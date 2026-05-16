#!/usr/bin/env python3
"""Build AlphaConfidenceModel labels and evaluation summary from local or database rows."""
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import Any

from model_governance.local_layer_scripts import (
    FIXTURE_INPUT_ROWS,
    evaluate_layer,
    fixture_outcome_rows,
    generate_layer,
    read_rows,
    write_payload,
)
from models.model_04_alpha_confidence import MODEL_ID, MODEL_SURFACE

DEFAULT_DB_URL_FILE = Path("/root/secrets/openclaw/database-url")
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


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
    except ModuleNotFoundError as error:  # pragma: no cover
        raise SystemExit("psycopg is required for SQL evaluation; install psycopg[binary].") from error
    return psycopg, dict_row


def _quote(identifier: str) -> str:
    if not IDENTIFIER_RE.match(identifier):
        raise ValueError(f"unsafe SQL identifier: {identifier!r}")
    return '"' + identifier.replace('"', '""') + '"'


def _qualified(schema: str, table: str) -> str:
    return f"{_quote(schema)}.{_quote(table)}"


def _fetch_model_rows(cursor: Any, *, schema: str, table: str, source_start: str | None, source_end: str | None) -> list[dict[str, Any]]:
    where: list[str] = []
    params: list[Any] = []
    if source_start:
        where.append("available_time::timestamptz >= %s::timestamptz")
        params.append(source_start)
    if source_end:
        where.append("available_time::timestamptz < %s::timestamptz")
        params.append(source_end)
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    cursor.execute(f"SELECT * FROM {_qualified(schema, table)}{where_sql} ORDER BY available_time::timestamptz ASC, alpha_confidence_vector_ref ASC", params)
    return [dict(row) for row in cursor.fetchall()]


def _evaluate(model_rows: list[dict[str, Any]], *, evidence_source: str, output_json: Path | None) -> None:
    outcome_rows = fixture_outcome_rows(MODEL_SURFACE, model_rows)
    payload = evaluate_layer(
        module_name="models.model_04_alpha_confidence",
        label_builder_name="build_alpha_confidence_labels",
        model_rows=model_rows,
        outcome_rows=outcome_rows,
        layer_number=5,
        model_surface=MODEL_SURFACE,
        model_id=MODEL_ID,
        evidence_source=evidence_source,
    )
    write_payload(payload, output_json)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-jsonl", type=Path, help="Local JSONL/JSON model rows. Defaults to generated fixture model rows.")
    parser.add_argument("--input-jsonl", type=Path, help="Optional input rows used to generate model rows when --model-jsonl is absent.")
    parser.add_argument("--outcome-jsonl", type=Path, help="Local JSONL/JSON realized outcome rows. Defaults to fixture outcomes built from model refs.")
    parser.add_argument("--output-json", "--output", dest="output_json", type=Path, help="Optional output path for summary and labels.")
    parser.add_argument("--evidence-source", default="fixture_or_local_jsonl")
    parser.add_argument("--from-database", action="store_true")
    parser.add_argument("--database-url")
    parser.add_argument("--model-schema", default="trading_model")
    parser.add_argument("--model-table", default="model_04_alpha_confidence")
    parser.add_argument("--source-start")
    parser.add_argument("--source-end")
    args = parser.parse_args(argv)
    if args.from_database:
        psycopg, dict_row = _load_psycopg()
        with psycopg.connect(_database_url(args.database_url), row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                model_rows = _fetch_model_rows(cursor, schema=args.model_schema, table=args.model_table, source_start=args.source_start, source_end=args.source_end)
        _evaluate(model_rows, evidence_source=args.evidence_source or "database_rows_fixture_outcomes", output_json=args.output_json)
        return 0
    if args.model_jsonl:
        model_rows = read_rows(args.model_jsonl)
    else:
        input_rows = read_rows(args.input_jsonl) if args.input_jsonl else FIXTURE_INPUT_ROWS[MODEL_SURFACE]
        model_rows = generate_layer("models.model_04_alpha_confidence", input_rows)
    outcome_rows = read_rows(args.outcome_jsonl) if args.outcome_jsonl else fixture_outcome_rows(MODEL_SURFACE, model_rows)
    payload = evaluate_layer(
        module_name="models.model_04_alpha_confidence",
        label_builder_name="build_alpha_confidence_labels",
        model_rows=model_rows,
        outcome_rows=outcome_rows,
        layer_number=5,
        model_surface=MODEL_SURFACE,
        model_id=MODEL_ID,
        evidence_source=args.evidence_source,
    )
    write_payload(payload, args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
