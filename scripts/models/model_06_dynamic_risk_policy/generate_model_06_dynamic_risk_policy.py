#!/usr/bin/env python3
"""Generate deterministic DynamicRiskPolicyModel rows from local JSON/JSONL or database rows."""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from model_runtime.config import database_url_file

from model_governance.model_output_support import write_model_output_with_support
from model_governance.local_layer_scripts import FIXTURE_INPUT_ROWS, generate_layer, read_rows, write_rows
from models.model_06_dynamic_risk_policy import MODEL_SURFACE, MODEL_VERSION, generate_rows

DEFAULT_DB_URL_FILE = database_url_file()
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
JSON_COLUMNS = {"dynamic_risk_policy_state", "dynamic_risk_policy_diagnostics", "6_risk_policy_reason_codes"}
PRIMARY_KEY = ("dynamic_risk_policy_state_ref",)
EXPLAINABILITY_COLUMNS = {"dynamic_risk_policy_state"}
DIAGNOSTICS_COLUMNS = {"dynamic_risk_policy_diagnostics", "6_risk_policy_reason_codes"}
TEXT_6_COLUMNS = {"6_resolved_risk_policy_horizon", "6_risk_policy_reason_codes"}


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


def _quote(identifier: str) -> str:
    if not IDENTIFIER_RE.match(identifier):
        raise ValueError(f"unsafe SQL identifier: {identifier!r}")
    return '"' + identifier.replace('"', '""') + '"'


def _qualified(schema: str, table: str) -> str:
    return f"{_quote(schema)}.{_quote(table)}"


def _column_type(column: str) -> str:
    if column in JSON_COLUMNS:
        return "JSONB"
    if column.startswith("6_"):
        return "TEXT" if column in TEXT_6_COLUMNS else "DOUBLE PRECISION"
    return "TEXT"


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


def _fetch_alpha_rows(cursor: Any, *, schema: str, table: str, source_start: str | None, source_end: str | None) -> list[dict[str, Any]]:
    where: list[str] = []
    params: list[Any] = []
    if source_start:
        where.append("available_time::timestamptz >= %s::timestamptz")
        params.append(source_start)
    if source_end:
        where.append("available_time::timestamptz < %s::timestamptz")
        params.append(source_end)
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    cursor.execute(f"SELECT * FROM {_qualified(schema, table)}{where_sql} ORDER BY available_time::timestamptz ASC, target_candidate_id ASC", params)
    return [dict(row) for row in cursor.fetchall()]


def _alpha_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    payload = _coerce_json_mapping(row.get("alpha_confidence_vector"))
    payload.update({str(key): value for key, value in row.items() if str(key).startswith("5_") and value is not None})
    return payload


def _decision_rows(alpha_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in alpha_rows:
        rows.append(
            {
                "available_time": row.get("available_time"),
                "tradeable_time": row.get("tradeable_time") or row.get("available_time"),
                "target_candidate_id": row.get("target_candidate_id"),
                "market_context_state_ref": row.get("market_context_state_ref"),
                "alpha_confidence_vector_ref": row.get("alpha_confidence_vector_ref"),
                "market_context_state": _coerce_json_mapping(row.get("market_context_state")) or {"1_market_risk_stress_score": 0.25, "1_market_liquidity_support_score": 0.70},
                "systemic_event_risk_state": _coerce_json_mapping(row.get("systemic_event_risk_state")),
                "alpha_confidence_vector": _alpha_payload(row),
                "portfolio_exposure_state": {"gross_exposure_capacity_score": 0.70, "correlation_concentration_score": 0.25},
                "account_capacity_state": {"cash_capacity_score": 0.70, "drawdown_pressure_score": 0.20},
            }
        )
    return rows


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True, default=str) + "\n" for row in rows), encoding="utf-8")


def generate_from_database(
    *,
    database_url: str,
    source_start: str | None,
    source_end: str | None,
    source_schema: str,
    source_table: str,
    target_schema: str,
    target_table: str,
    model_version: str,
    output_jsonl: Path | None,
) -> int:
    psycopg, dict_row = _load_psycopg()
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cursor:
            alpha_rows = _fetch_alpha_rows(cursor, schema=source_schema, table=source_table, source_start=source_start, source_end=source_end)
            model_rows = generate_rows(_decision_rows(alpha_rows), model_version=model_version)
            write_model_output_with_support(
                cursor,
                model_rows,
                target_schema=target_schema,
                target_table=target_table,
                primary_key=PRIMARY_KEY,
                explainability_columns=EXPLAINABILITY_COLUMNS,
                diagnostics_columns=DIAGNOSTICS_COLUMNS,
            )
    if output_jsonl:
        _write_jsonl(output_jsonl, model_rows)
    return len(model_rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-jsonl", type=Path, help="Local JSONL/JSON input rows. Defaults to a tiny fixture row.")
    parser.add_argument("--output-jsonl", type=Path, help="Optional output path; .jsonl writes newline-delimited JSON, otherwise JSON array.")
    parser.add_argument("--model-version", default=MODEL_VERSION)
    parser.add_argument("--from-database", action="store_true")
    parser.add_argument("--database-url")
    parser.add_argument("--source-start")
    parser.add_argument("--source-end")
    parser.add_argument("--source-schema", default="trading_model")
    parser.add_argument("--source-table", default="model_05_alpha_confidence")
    parser.add_argument("--target-schema", default="trading_model")
    parser.add_argument("--target-table", default="model_06_dynamic_risk_policy")
    args = parser.parse_args(argv)
    if args.from_database:
        count = generate_from_database(database_url=_database_url(args.database_url), source_start=args.source_start, source_end=args.source_end, source_schema=args.source_schema, source_table=args.source_table, target_schema=args.target_schema, target_table=args.target_table, model_version=args.model_version, output_jsonl=args.output_jsonl)
        print(f"generated {count} rows into {args.target_schema}.{args.target_table}")
        return 0
    input_rows = read_rows(args.input_jsonl) if args.input_jsonl else FIXTURE_INPUT_ROWS[MODEL_SURFACE]
    rows = generate_layer("models.model_06_dynamic_risk_policy", input_rows, model_version=args.model_version)
    write_rows(rows, args.output_jsonl)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
