#!/usr/bin/env python3
"""Build TargetStateVectorModel promotion evidence from local JSON/JSONL or database rows."""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

from models.model_03_target_state_vector import evaluation, generator

DEFAULT_DB_URL_FILE = Path("/root/secrets/openclaw/database-url")
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _read_rows(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".jsonl", ".ndjson"}:
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    payload = json.loads(text)
    if isinstance(payload, dict):
        payload = payload.get("rows") or payload.get("feature_rows") or payload.get("model_rows") or []
    return [dict(row) for row in payload]


def _database_url(explicit: str | None) -> str:
    if explicit:
        return explicit
    value = os.environ.get("OPENCLAW_DATABASE_URL", "").strip()
    if value:
        return value
    if DEFAULT_DB_URL_FILE.exists():
        return DEFAULT_DB_URL_FILE.read_text(encoding="utf-8").strip()
    raise SystemExit(f"database URL not supplied and {DEFAULT_DB_URL_FILE} does not exist")


def _load_psycopg():
    try:
        import psycopg  # type: ignore
        from psycopg.rows import dict_row  # type: ignore
    except ModuleNotFoundError as error:  # pragma: no cover - environment guard
        raise SystemExit("psycopg is required for SQL evaluation; install psycopg[binary].") from error
    return psycopg, dict_row


def _quote_identifier(identifier: str) -> str:
    if not IDENTIFIER_RE.match(identifier):
        raise ValueError(f"unsafe SQL identifier: {identifier!r}")
    return '"' + identifier.replace('"', '""') + '"'


def _qualified(schema: str, table: str) -> str:
    return f"{_quote_identifier(schema)}.{_quote_identifier(table)}"


def _fetch_rows(cursor: Any, *, schema: str, table: str, source_start: str | None, source_end: str | None) -> list[dict[str, Any]]:
    where: list[str] = []
    params: list[Any] = []
    if source_start:
        where.append("available_time >= %s")
        params.append(source_start)
    if source_end:
        where.append("available_time < %s")
        params.append(source_end)
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    cursor.execute(f"SELECT * FROM {_qualified(schema, table)}{where_sql} ORDER BY available_time ASC, target_candidate_id ASC", params)
    return [dict(row) for row in cursor.fetchall()]


def _build_payload(feature_rows: list[dict[str, Any]], model_rows: list[dict[str, Any]], *, evidence_source: str) -> dict[str, Any]:
    artifacts = evaluation.build_evaluation_artifacts(
        feature_rows=feature_rows,
        model_rows=model_rows,
        evidence_source=evidence_source,
        purpose="real_database_evaluation" if evidence_source == "real_database_evaluation" else "evaluation_dry_run",
        request_status="evaluated",
        write_policy=evaluation.DEFAULT_DATABASE_READ_WRITE_POLICY if evidence_source == "real_database_evaluation" else evaluation.DEFAULT_DRY_RUN_WRITE_POLICY,
    )
    return {"tables": artifacts.as_table_rows(), "threshold_summary": evaluation.summarize_threshold_results(artifacts.eval_metrics)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-rows", type=Path)
    parser.add_argument("--model-rows", type=Path, help="Optional model rows; generated from feature rows when omitted in file mode")
    parser.add_argument("--output", "--output-json", dest="output", type=Path, help="Optional JSON output path")
    parser.add_argument("--from-database", action="store_true", help="Read feature/model rows from PostgreSQL")
    parser.add_argument("--database-url", help="PostgreSQL URL. Defaults to OPENCLAW_DATABASE_URL or local OpenClaw DB secret file.")
    parser.add_argument("--feature-schema", default="trading_data")
    parser.add_argument("--feature-table", default="feature_03_target_state_vector")
    parser.add_argument("--model-schema", default="trading_model")
    parser.add_argument("--model-table", default="model_03_target_state_vector")
    parser.add_argument("--source-start")
    parser.add_argument("--source-end")
    args = parser.parse_args(argv)
    if args.from_database:
        psycopg, dict_row = _load_psycopg()
        with psycopg.connect(_database_url(args.database_url), row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                feature_rows = _fetch_rows(cursor, schema=args.feature_schema, table=args.feature_table, source_start=args.source_start, source_end=args.source_end)
                model_rows = _fetch_rows(cursor, schema=args.model_schema, table=args.model_table, source_start=args.source_start, source_end=args.source_end)
        payload = _build_payload(feature_rows, model_rows, evidence_source="real_database_evaluation")
    else:
        if not args.feature_rows:
            parser.error("--feature-rows is required unless --from-database is supplied")
        feature_rows = _read_rows(args.feature_rows)
        model_rows = _read_rows(args.model_rows) if args.model_rows else generator.generate_rows(feature_rows)
        payload = _build_payload(feature_rows, model_rows, evidence_source="fixture_or_local_jsonl")
    text = json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
