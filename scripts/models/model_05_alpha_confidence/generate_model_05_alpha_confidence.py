#!/usr/bin/env python3
"""Generate deterministic AlphaConfidenceModel rows from local JSON/JSONL or database rows."""
from __future__ import annotations

import argparse
import bisect
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from zoneinfo import ZoneInfo

from model_runtime.config import database_url_file

from model_governance.model_output_support import write_model_output_with_support
from model_governance.local_layer_scripts import FIXTURE_INPUT_ROWS, read_rows, write_rows
from models.model_05_alpha_confidence import MODEL_ID, MODEL_SURFACE, MODEL_VERSION, generate_rows

DEFAULT_DB_URL_FILE = database_url_file()
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
COLUMN_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_]+$")
ET = ZoneInfo("America/New_York")
JSON_COLUMNS = {"alpha_confidence_vector", "base_alpha_vector", "alpha_confidence_diagnostics"}
PRIMARY_KEY = ("alpha_confidence_vector_ref",)
EXPLAINABILITY_COLUMNS = {"alpha_confidence_vector", "base_alpha_vector"}
DIAGNOSTICS_COLUMNS = {"alpha_confidence_diagnostics"}
RETIRED_COLUMNS = ("event_context_vector_ref",)


def _database_url(explicit: str | None) -> str:
    if explicit:
        return explicit
    for env_name in ("TRADING_MODEL_DATABASE_URL", "OPENCLAW_DATABASE_URL"):
        value = os.environ.get(env_name, "").strip()
        if value:
            return value
    if DEFAULT_DB_URL_FILE.exists():
        return DEFAULT_DB_URL_FILE.read_text(encoding="utf-8").strip()
    raise SystemExit(f"database URL not supplied and {DEFAULT_DB_URL_FILE} does not exist")


def _load_psycopg():
    try:
        import psycopg  # type: ignore
        from psycopg.rows import dict_row  # type: ignore
    except ModuleNotFoundError as error:  # pragma: no cover
        raise SystemExit("psycopg is required for SQL generation; install psycopg[binary].") from error
    return psycopg, dict_row


def _quote_identifier(identifier: str) -> str:
    if not IDENTIFIER_RE.match(identifier):
        raise ValueError(f"unsafe SQL identifier: {identifier!r}")
    return '"' + identifier.replace('"', '""') + '"'


def _quote_column_identifier(identifier: str) -> str:
    if not COLUMN_IDENTIFIER_RE.match(identifier):
        raise ValueError(f"unsafe SQL column identifier: {identifier!r}")
    return '"' + identifier.replace('"', '""') + '"'


def _qualified(schema: str, table: str) -> str:
    return f"{_quote_identifier(schema)}.{_quote_identifier(table)}"


def _column_type(column: str) -> str:
    if column in JSON_COLUMNS:
        return "JSONB"
    if column.startswith("5_"):
        return "DOUBLE PRECISION"
    return "TEXT"


def _parse_time(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ET)
    return parsed.astimezone(ET)


def _iso(value: Any) -> str:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = _parse_time(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ET)
    return parsed.astimezone(ET).isoformat()


def _fetch_rows(
    cursor: Any,
    *,
    schema: str,
    table: str,
    source_start: str | None,
    source_end: str | None,
    order_by: str,
    target_symbol: str | None = None,
    target_candidate_ids: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    if target_candidate_ids is not None and not target_candidate_ids:
        return []
    where: list[str] = []
    params: list[Any] = []
    if source_start:
        where.append("available_time::timestamptz >= %s::timestamptz")
        params.append(source_start)
    if source_end:
        where.append("available_time::timestamptz < %s::timestamptz")
        params.append(source_end)
    if target_symbol:
        where.append("UPPER(symbol) = %s")
        params.append(target_symbol.upper())
    if target_candidate_ids is not None:
        where.append("target_candidate_id = ANY(%s)")
        params.append(list(target_candidate_ids))
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    cursor.execute(f"SELECT * FROM {_qualified(schema, table)}{where_sql} ORDER BY {order_by}", params)
    return [dict(row) for row in cursor.fetchall()]


def _payload_from_prefixed_columns(row: Mapping[str, Any], prefix: str) -> dict[str, Any]:
    return {str(key): value for key, value in row.items() if str(key).startswith(prefix) and value is not None}


def _coerce_json_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str) and value.strip():
        try:
            loaded = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return dict(loaded) if isinstance(loaded, Mapping) else {}
    return {}


def _target_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    nested = _coerce_json_mapping(row.get("target_context_state"))
    score_payload = nested.get("score_payload")
    if isinstance(score_payload, Mapping):
        payload.update({str(key): value for key, value in score_payload.items() if value is not None})
    payload.update(_payload_from_prefixed_columns(row, "3_"))
    return payload


def _event_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    payload = _coerce_json_mapping(row.get("event_failure_risk_vector"))
    payload.update(_payload_from_prefixed_columns(row, "4_"))
    return payload


def _market_payload(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _payload_from_prefixed_columns(row or {}, "1_")
    if "1_state_quality_score" not in payload:
        payload["1_state_quality_score"] = _average_present(payload.get("1_data_quality_score"), payload.get("1_coverage_score"), default=0.75)
    return payload


def _sector_payload(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _payload_from_prefixed_columns(row or {}, "2_")
    if "2_sector_context_support_quality_score" not in payload:
        payload["2_sector_context_support_quality_score"] = _first_present(
            payload.get("2_market_context_support_score"),
            payload.get("2_selection_readiness_score"),
            default=0.55,
        )
    return payload


def _quality_payload(*, market: Mapping[str, Any], sector: Mapping[str, Any], target: Mapping[str, Any], event: Mapping[str, Any]) -> dict[str, Any]:
    data_quality = min(
        _safe_score(market.get("1_state_quality_score"), 0.75),
        _safe_score(sector.get("2_state_quality_score"), 0.75),
        _safe_score(target.get("3_state_quality_score"), 0.75),
        _safe_score(event.get("4_event_evidence_quality_score_1W"), 0.75),
    )
    sample_support = min(1.0, _safe_score(target.get("3_evidence_count"), 0.0) / 50.0) if target.get("3_evidence_count") is not None else 0.55
    return {
        "sample_support_score": round(sample_support, 6),
        "walk_forward_reliability_score": round(data_quality, 6),
        "model_ensemble_agreement_score": 0.70,
        "model_disagreement_score": round(max(0.0, 1.0 - data_quality), 6),
        "out_of_distribution_score": 0.20,
        "data_quality_score": round(data_quality, 6),
    }


def _safe_score(value: Any, default: float) -> float:
    try:
        if value is None or value == "":
            return default
        score = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, score))


def _first_present(*values: Any, default: float) -> float:
    for value in values:
        if value is not None and value != "":
            return _safe_score(value, default)
    return default


def _average_present(*values: Any, default: float) -> float:
    scores = [_safe_score(value, default) for value in values if value is not None and value != ""]
    return round(sum(scores) / len(scores), 6) if scores else default


def _latest_before(rows: Sequence[Mapping[str, Any]], available_time: datetime) -> Mapping[str, Any] | None:
    latest: Mapping[str, Any] | None = None
    latest_time: datetime | None = None
    for row in rows:
        row_time = _parse_time(row.get("available_time"))
        if row_time <= available_time and (latest_time is None or row_time > latest_time):
            latest = row
            latest_time = row_time
    return latest


def _available_time_index(rows: Sequence[Mapping[str, Any]]) -> tuple[list[datetime], list[Mapping[str, Any]]]:
    indexed = [
        (_parse_time(row.get("available_time")), position, row)
        for position, row in enumerate(rows)
        if row.get("available_time")
    ]
    indexed.sort(key=lambda item: (item[0], item[1]))
    return [item[0] for item in indexed], [item[2] for item in indexed]


def _latest_from_index(times: Sequence[datetime], rows: Sequence[Mapping[str, Any]], available_time: datetime) -> Mapping[str, Any] | None:
    index = bisect.bisect_right(times, available_time) - 1
    if index < 0:
        return None
    return rows[index]


def _decision_rows(
    *,
    event_failure_rows: Sequence[Mapping[str, Any]],
    model_03_rows: Sequence[Mapping[str, Any]],
    source_03_rows: Sequence[Mapping[str, Any]],
    model_02_rows: Sequence[Mapping[str, Any]],
    model_01_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    event_by_candidate_time: dict[tuple[str, str], Mapping[str, Any]] = {}
    for row in event_failure_rows:
        if row.get("target_candidate_id") and row.get("available_time"):
            event_by_candidate_time[(str(row["target_candidate_id"]), _iso(row["available_time"]))] = row
    source_by_candidate_time: dict[tuple[str, str], Mapping[str, Any]] = {}
    for row in source_03_rows:
        if row.get("target_candidate_id") and row.get("available_time"):
            source_by_candidate_time[(str(row["target_candidate_id"]), _iso(row["available_time"]))] = row
    sector_rows_by_symbol: dict[str, list[Mapping[str, Any]]] = {}
    for row in model_02_rows:
        symbol = str(row.get("sector_or_industry_symbol") or "").upper()
        if symbol:
            sector_rows_by_symbol.setdefault(symbol, []).append(row)
    market_times, market_rows = _available_time_index(model_01_rows)
    sector_index_by_symbol = {
        symbol: _available_time_index(rows)
        for symbol, rows in sector_rows_by_symbol.items()
    }

    rows: list[dict[str, Any]] = []
    for target_model in model_03_rows:
        candidate = str(target_model.get("target_candidate_id") or "")
        if not candidate or not target_model.get("available_time"):
            continue
        available = _parse_time(target_model["available_time"])
        available_iso = _iso(available)
        event_model = event_by_candidate_time.get((candidate, available_iso), {})
        source_row = source_by_candidate_time.get((candidate, available_iso))
        symbol = str((source_row or {}).get("symbol") or "").upper()
        sector_times, sector_rows = sector_index_by_symbol.get(symbol, ([], []))
        market = _market_payload(_latest_from_index(market_times, market_rows, available))
        sector = _sector_payload(_latest_from_index(sector_times, sector_rows, available))
        target = _target_payload(target_model)
        event = _event_payload(event_model)
        rows.append(
            {
                "available_time": available_iso,
                "tradeable_time": _iso(event_model.get("tradeable_time") or available_iso),
                "target_candidate_id": candidate,
                "market_context_state_ref": event_model.get("market_context_state_ref") or target_model.get("market_context_state_ref"),
                "sector_context_state_ref": event_model.get("sector_context_state_ref") or target_model.get("sector_context_state_ref"),
                "target_context_state_ref": event_model.get("target_context_state_ref") or target_model.get("target_context_state_ref"),
                "event_failure_risk_vector_ref": event_model.get("event_failure_risk_vector_ref"),
                "training_sample_scope": "dense_minute_target_state",
                "market_context_state": market,
                "sector_context_state": sector,
                "target_context_state": target,
                "event_failure_risk_vector": event,
                "quality_calibration_state": _quality_payload(market=market, sector=sector, target=target, event=event),
            }
        )
    return rows


def _ensure_table(cursor: Any, *, target_schema: str, target_table: str, columns: Sequence[str]) -> None:
    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {_quote_identifier(target_schema)}")
    column_defs = ",\n          ".join(f"{_quote_column_identifier(column)} {_column_type(column)}" for column in columns)
    pk_sql = ", ".join(_quote_column_identifier(column) for column in PRIMARY_KEY)
    cursor.execute(f"CREATE TABLE IF NOT EXISTS {_qualified(target_schema, target_table)} ({column_defs}, PRIMARY KEY ({pk_sql}))")
    for column in columns:
        cursor.execute(f"ALTER TABLE {_qualified(target_schema, target_table)} ADD COLUMN IF NOT EXISTS {_quote_column_identifier(column)} {_column_type(column)}")


def _write_sql(cursor: Any, rows: Sequence[Mapping[str, Any]], *, target_schema: str, target_table: str) -> None:
    write_model_output_with_support(
        cursor,
        rows,
        target_schema=target_schema,
        target_table=target_table,
        primary_key=PRIMARY_KEY,
        explainability_columns=EXPLAINABILITY_COLUMNS,
        diagnostics_columns=DIAGNOSTICS_COLUMNS,
    )
    for table in (target_table, f"{target_table}_explainability", f"{target_table}_diagnostics"):
        for column in RETIRED_COLUMNS:
            cursor.execute(f"ALTER TABLE {_qualified(target_schema, table)} DROP COLUMN IF EXISTS {_quote_column_identifier(column)}")


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True, default=str) + "\n" for row in rows), encoding="utf-8")


def generate_from_database(
    *,
    database_url: str,
    source_start: str | None,
    source_end: str | None,
    target_schema: str,
    target_table: str,
    model_version: str,
    output_jsonl: Path | None,
    target_symbol: str | None = None,
    after_cost_alpha_model: Mapping[str, Any] | None = None,
) -> int:
    psycopg, dict_row = _load_psycopg()
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cursor:
            source_03_rows = _fetch_rows(cursor, schema="trading_data", table="source_03_target_state", source_start=source_start, source_end=source_end, target_symbol=target_symbol, order_by="available_time::timestamptz ASC, target_candidate_id ASC")
            target_candidate_ids = sorted({str(row["target_candidate_id"]) for row in source_03_rows if row.get("target_candidate_id")})
            event_failure_rows = _fetch_rows(cursor, schema="trading_model", table="model_04_event_failure_risk", source_start=source_start, source_end=source_end, target_candidate_ids=target_candidate_ids if target_symbol else None, order_by="available_time::timestamptz ASC, target_candidate_id ASC")
            model_03_rows = _fetch_rows(cursor, schema="trading_model", table="model_03_target_state_vector", source_start=source_start, source_end=source_end, target_candidate_ids=target_candidate_ids if target_symbol else None, order_by="available_time::timestamptz ASC, target_candidate_id ASC")
            model_02_rows = _fetch_rows(cursor, schema="trading_model", table="model_02_sector_context", source_start=source_start, source_end=source_end, order_by="available_time::timestamptz ASC, sector_or_industry_symbol ASC")
            model_01_rows = _fetch_rows(cursor, schema="trading_model", table="model_01_market_regime", source_start=source_start, source_end=source_end, order_by="available_time::timestamptz ASC")
            decisions = _decision_rows(event_failure_rows=event_failure_rows, model_03_rows=model_03_rows, source_03_rows=source_03_rows, model_02_rows=model_02_rows, model_01_rows=model_01_rows)
            model_rows = generate_rows(decisions, model_version=model_version, after_cost_alpha_model=after_cost_alpha_model)
            _write_sql(cursor, model_rows, target_schema=target_schema, target_table=target_table)
    if output_jsonl:
        _write_jsonl(output_jsonl, model_rows)
    return len(model_rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-jsonl", type=Path, help="Local JSONL/JSON input rows. Defaults to a tiny fixture row.")
    parser.add_argument("--output-jsonl", type=Path, help="Optional output path; .jsonl writes newline-delimited JSON, otherwise JSON array.")
    parser.add_argument("--model-version", default=MODEL_VERSION)
    parser.add_argument("--after-cost-alpha-model-json", type=Path, help="Optional trained Layer 5 after-cost alpha model artifact.")
    parser.add_argument("--from-database", action="store_true")
    parser.add_argument("--database-url")
    parser.add_argument("--source-start")
    parser.add_argument("--source-end")
    parser.add_argument("--target-symbol", help="Optional selected target symbol filter via source_03_target_state.")
    parser.add_argument("--target-schema", default="trading_model")
    parser.add_argument("--target-table", default="model_05_alpha_confidence")
    args = parser.parse_args(argv)
    after_cost_alpha_model = _read_json_mapping(args.after_cost_alpha_model_json)
    if args.from_database:
        count = generate_from_database(database_url=_database_url(args.database_url), source_start=args.source_start, source_end=args.source_end, target_schema=args.target_schema, target_table=args.target_table, model_version=args.model_version, output_jsonl=args.output_jsonl, target_symbol=args.target_symbol, after_cost_alpha_model=after_cost_alpha_model)
        print(f"generated {count} rows into {args.target_schema}.{args.target_table}")
        return 0
    input_rows = read_rows(args.input_jsonl) if args.input_jsonl else FIXTURE_INPUT_ROWS[MODEL_SURFACE]
    rows = generate_rows(input_rows, model_version=args.model_version, after_cost_alpha_model=after_cost_alpha_model)
    write_rows(rows, args.output_jsonl)
    return 0


def _read_json_mapping(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise SystemExit("--after-cost-alpha-model-json must contain a JSON object")
    return dict(payload)


if __name__ == "__main__":
    raise SystemExit(main())
