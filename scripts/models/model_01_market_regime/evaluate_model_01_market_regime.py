#!/usr/bin/env python3
"""Build MarketRegimeModel evaluation artifacts.

By default this remains an isolated fixture/local-JSONL dry run. With
``--from-database`` it performs a read-only PostgreSQL fetch of feature and model
rows, then builds promotion evidence without writing to the database. Promotion
manager-control-plane persistence remains owned by `trading-manager`.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tomllib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping
from zoneinfo import ZoneInfo

from models.model_01_market_regime.evaluation import (
    DEFAULT_DATABASE_READ_WRITE_POLICY,
    DEFAULT_DRY_RUN_WRITE_POLICY,
    DEFAULT_FEATURE_SCHEMA,
    DEFAULT_FEATURE_TABLE,
    DEFAULT_MODEL_SCHEMA,
    DEFAULT_MODEL_TABLE,
    DEFAULT_PROMOTION_THRESHOLDS,
    build_evaluation_artifacts,
    summarize_artifacts,
)

ET = ZoneInfo("America/New_York")
DEFAULT_DB_URL_FILE = Path("/root/secrets/openclaw/database-url")
DEFAULT_THRESHOLDS_TOML = Path(__file__).resolve().parents[3] / "src" / "models" / "model_01_market_regime" / "config" / "promotion_thresholds.toml"
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise ValueError(f"{path}:{line_number} must contain a JSON object")
        rows.append(parsed)
    return rows


def _fixture_rows() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    start = datetime(2026, 1, 2, 16, 0, tzinfo=ET)
    feature_rows: list[dict[str, object]] = []
    model_rows: list[dict[str, object]] = []
    for index in range(12):
        available_time = (start + timedelta(days=index)).isoformat()
        one_day_return = ((index % 5) - 2) / 100.0
        five_day_return = (index - 6) / 200.0
        feature_rows.append(
            {
                "snapshot_time": available_time,
                "spy_return_1d": one_day_return,
                "spy_return_5d": five_day_return,
            }
        )
        trend = (index - 5.5) / 6.0
        stress = (5.5 - index) / 8.0
        model_rows.append(
            {
                "available_time": available_time,
                "1_market_direction_score": trend / 1.5,
                "1_market_direction_strength_score": abs(trend / 1.5),
                "1_market_trend_quality_score": trend,
                "1_market_stability_score": (trend - stress) / 2,
                "1_market_risk_stress_score": stress,
                "1_market_transition_risk_score": abs(trend) / 10,
                "1_breadth_participation_score": trend / 2,
                "1_correlation_crowding_score": stress / 2,
                "1_dispersion_opportunity_score": (trend / 2 - abs(stress / 2)) / 2,
                "1_market_liquidity_pressure_score": stress / 2,
                "1_market_liquidity_support_score": (trend - stress) / 2,
                "1_coverage_score": 1.0,
                "1_data_quality_score": 1.0,
            }
        )
    return feature_rows, model_rows


def _database_url(explicit: str | None) -> str:
    if explicit:
        return explicit
    value = os.environ.get("OPENCLAW_DATABASE_URL", "").strip()
    if value:
        return value
    if DEFAULT_DB_URL_FILE.exists():
        return DEFAULT_DB_URL_FILE.read_text(encoding="utf-8").strip()
    raise SystemExit(f"database URL not supplied and {DEFAULT_DB_URL_FILE} does not exist")


def _ident(identifier: str) -> str:
    if not IDENTIFIER_RE.match(identifier):
        raise ValueError(f"unsafe SQL identifier: {identifier!r}")
    return '"' + identifier.replace('"', '""') + '"'


def _qualified(schema: str, table: str) -> str:
    return f"{_ident(schema)}.{_ident(table)}"


def _run_psql(database_url: str, sql: str) -> str:
    result = subprocess.run(
        ["psql", database_url, "-v", "ON_ERROR_STOP=1", "-q", "-At"],
        input=sql,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        if result.stdout:
            print(result.stdout, file=sys.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode)
    return result.stdout


def _fetch_json_rows(database_url: str, *, schema: str, table: str, order_column: str) -> list[dict[str, Any]]:
    output = _run_psql(
        database_url,
        f"""
        SELECT row_to_json(t)::text
        FROM (
          SELECT * FROM {_qualified(schema, table)}
          ORDER BY {_ident(order_column)} ASC
        ) AS t;
        """,
    )
    return [json.loads(line) for line in output.splitlines() if line.strip().startswith("{")]


def _flatten_feature_payload_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for row in rows:
        output = dict(row)
        payload = output.pop("feature_payload_json", None)
        if isinstance(payload, str):
            payload = json.loads(payload)
        if isinstance(payload, Mapping):
            output.update(payload)
        flattened.append(output)
    return flattened


def _load_thresholds(path: Path | None) -> dict[str, float]:
    if path is None:
        path = DEFAULT_THRESHOLDS_TOML
    if not path.exists():
        return dict(DEFAULT_PROMOTION_THRESHOLDS)
    parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    thresholds = dict(DEFAULT_PROMOTION_THRESHOLDS)
    for key, value in parsed.items():
        if key not in thresholds:
            raise ValueError(f"unknown promotion threshold: {key}")
        thresholds[key] = float(value)
    return thresholds


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-jsonl", type=Path, help="Optional local JSONL feature rows. Must include snapshot_time and label source columns.")
    parser.add_argument("--model-jsonl", type=Path, help="Optional local JSONL model rows. Must include available_time and factor columns.")
    parser.add_argument("--from-database", action="store_true", help="Read feature/model rows from PostgreSQL instead of fixture/local JSONL input.")
    parser.add_argument("--database-url", help="PostgreSQL URL. Defaults to OPENCLAW_DATABASE_URL or the local OpenClaw DB secret file.")
    parser.add_argument("--feature-schema", default=DEFAULT_FEATURE_SCHEMA)
    parser.add_argument("--feature-table", default=DEFAULT_FEATURE_TABLE)
    parser.add_argument("--model-schema", default=DEFAULT_MODEL_SCHEMA)
    parser.add_argument("--model-table", default=DEFAULT_MODEL_TABLE)
    parser.add_argument("--output-json", type=Path, help="Optional local output path for generated artifacts or summary.")
    parser.add_argument("--print-artifacts", action="store_true", help="Print full generated artifacts instead of summary only.")
    parser.add_argument("--model-config-hash", help="Optional config hash to stamp into snapshot/eval run rows.")
    parser.add_argument("--promotion-thresholds-toml", type=Path, default=DEFAULT_THRESHOLDS_TOML, help="Promotion threshold TOML used in summary evidence.")
    args = parser.parse_args(argv)

    if args.from_database and (args.feature_jsonl or args.model_jsonl):
        raise SystemExit("--from-database cannot be combined with --feature-jsonl/--model-jsonl")
    if bool(args.feature_jsonl) != bool(args.model_jsonl):
        raise SystemExit("--feature-jsonl and --model-jsonl must be supplied together")

    if args.from_database:
        database_url = _database_url(args.database_url)
        feature_storage_rows = _fetch_json_rows(database_url, schema=args.feature_schema, table=args.feature_table, order_column="snapshot_time")
        feature_rows = _flatten_feature_payload_rows(feature_storage_rows)
        model_rows = _fetch_json_rows(database_url, schema=args.model_schema, table=args.model_table, order_column="available_time")
        purpose = "promotion_evaluation"
        request_status = "completed"
        run_name = "market_regime_database_read_eval"
        run_status = "completed"
        write_policy = DEFAULT_DATABASE_READ_WRITE_POLICY
        evidence_source = f"postgresql:{args.feature_schema}.{args.feature_table}+{args.model_schema}.{args.model_table}"
    elif args.feature_jsonl and args.model_jsonl:
        feature_rows = _read_jsonl(args.feature_jsonl)
        model_rows = _read_jsonl(args.model_jsonl)
        purpose = "local_jsonl_evaluation"
        request_status = "local_only"
        run_name = "market_regime_local_jsonl_eval"
        run_status = "local_only"
        write_policy = DEFAULT_DRY_RUN_WRITE_POLICY
        evidence_source = "local_jsonl"
    else:
        feature_rows, model_rows = _fixture_rows()
        purpose = "evaluation_dry_run"
        request_status = "dry_run_only"
        run_name = "market_regime_dry_run_eval"
        run_status = "dry_run_only"
        write_policy = DEFAULT_DRY_RUN_WRITE_POLICY
        evidence_source = "fixture"

    artifacts = build_evaluation_artifacts(
        feature_rows=feature_rows,
        model_rows=model_rows,
        model_config_hash=args.model_config_hash,
        purpose=purpose,
        request_status=request_status,
        run_name=run_name,
        run_status=run_status,
        write_policy=write_policy,
        evidence_source=evidence_source,
        feature_schema=args.feature_schema,
        feature_table=args.feature_table,
    )
    thresholds = _load_thresholds(args.promotion_thresholds_toml)
    payload = artifacts.as_table_rows() if args.print_artifacts else summarize_artifacts(artifacts, thresholds=thresholds)
    text = json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(text, encoding="utf-8")
        print(f"wrote evaluation artifacts to {args.output_json}")
    else:
        print(text, end="")
    if args.from_database:
        print("READ ONLY: database rows were read, but no evaluation or promotion rows were written.")
    else:
        print("DRY RUN ONLY: no database connection was opened and no rows were written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
