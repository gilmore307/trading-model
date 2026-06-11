"""SQL helpers for focused model-output primary tables and support artifacts."""
from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
COLUMN_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_]+$")
RETIRED_HORIZON_SUFFIXES = ("5min", "15min", "60min", "390min", "5m", "15m", "60m", "390m")
DEFAULT_WRITE_BATCH_SIZE = 1000


def quote_identifier(identifier: str) -> str:
    if not IDENTIFIER_RE.match(identifier):
        raise ValueError(f"unsafe SQL identifier: {identifier!r}")
    return '"' + identifier.replace('"', '""') + '"'


def quote_column_identifier(identifier: str) -> str:
    if not COLUMN_IDENTIFIER_RE.match(identifier):
        raise ValueError(f"unsafe SQL column identifier: {identifier!r}")
    return '"' + identifier.replace('"', '""') + '"'


def qualified(schema: str, table: str) -> str:
    return f"{quote_identifier(schema)}.{quote_identifier(table)}"


def write_model_output_with_support(
    cursor: Any,
    rows: Sequence[Mapping[str, Any]],
    *,
    target_schema: str,
    target_table: str,
    primary_key: Sequence[str],
    explainability_columns: set[str],
    diagnostics_columns: set[str],
) -> None:
    """Write model output with JSON-heavy columns moved out of the primary table."""

    if not rows:
        return
    normalized_rows = [dict(row) for row in rows]
    auto_moved = _non_scalar_columns(normalized_rows) - set(primary_key)
    diagnostics_columns = set(diagnostics_columns) | {column for column in auto_moved if "diagnostic" in column or "reason_codes" in column}
    explainability_columns = (set(explainability_columns) | auto_moved) - diagnostics_columns
    moved_columns = explainability_columns | diagnostics_columns

    primary_rows = [{key: value for key, value in row.items() if key not in moved_columns} for row in normalized_rows]
    support_identity = _support_identity_columns(normalized_rows, primary_key)
    explainability_rows = [
        _support_row(row, support_identity, explainability_columns, payload_column="explanation_payload_json", support_table=f"{target_table}_explainability", primary_table=target_table)
        for row in normalized_rows
        if _has_non_empty(row, explainability_columns)
    ]
    diagnostics_rows = [
        _support_row(row, support_identity, diagnostics_columns, payload_column="diagnostic_payload_json", support_table=f"{target_table}_diagnostics", primary_table=target_table)
        for row in normalized_rows
        if _has_non_empty(row, diagnostics_columns)
    ]

    _write_rows(
        cursor,
        primary_rows,
        schema=target_schema,
        table=target_table,
        primary_key=primary_key,
        drop_columns=moved_columns,
        drop_absent_retired_horizon_columns=True,
    )
    if explainability_rows:
        _write_rows(
            cursor,
            explainability_rows,
            schema=target_schema,
            table=f"{target_table}_explainability",
            primary_key=primary_key,
            drop_columns=set(),
        )
    if diagnostics_rows:
        _write_rows(
            cursor,
            diagnostics_rows,
            schema=target_schema,
            table=f"{target_table}_diagnostics",
            primary_key=primary_key,
            drop_columns=set(),
        )


def _non_scalar_columns(rows: Sequence[Mapping[str, Any]]) -> set[str]:
    columns: set[str] = set()
    for row in rows:
        for key, value in row.items():
            if isinstance(value, Mapping) or (isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))):
                columns.add(str(key))
    return columns


def _support_identity_columns(rows: Sequence[Mapping[str, Any]], primary_key: Sequence[str]) -> list[str]:
    ordered: list[str] = []
    candidates = ("available_time", "tradeable_time", "target_candidate_id", "model_id", "model_layer", "model_version", *primary_key)
    all_columns = {key for row in rows for key in row}
    non_null_columns = {key for row in rows for key, value in row.items() if value not in (None, "")}
    for column in candidates:
        if column in all_columns and column not in ordered:
            ordered.append(column)
    for column in sorted(all_columns):
        if column.endswith("_ref") and column in non_null_columns and column not in ordered:
            ordered.append(column)
    return ordered


def _support_row(
    row: Mapping[str, Any],
    identity_columns: Sequence[str],
    payload_columns: set[str],
    *,
    payload_column: str,
    support_table: str,
    primary_table: str,
) -> dict[str, Any]:
    output = {column: row.get(column) for column in identity_columns if column in row}
    for column in sorted(payload_columns):
        if column in row:
            output[column] = row.get(column)
    output[payload_column] = {
        "artifact": support_table,
        "primary_table": primary_table,
        "moved_columns": sorted(column for column in payload_columns if column in row),
    }
    return output


def _has_non_empty(row: Mapping[str, Any], columns: set[str]) -> bool:
    return any(_is_non_empty(row.get(column)) for column in columns if column in row)


def _is_non_empty(value: Any) -> bool:
    if value is None or value == "":
        return False
    if isinstance(value, Mapping):
        return bool(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return bool(value)
    return True


def _write_rows(
    cursor: Any,
    rows: Sequence[Mapping[str, Any]],
    *,
    schema: str,
    table: str,
    primary_key: Sequence[str],
    drop_columns: set[str],
    drop_absent_retired_horizon_columns: bool = False,
) -> None:
    if not rows:
        return
    columns = list(rows[0].keys())
    column_types = _column_types(rows, columns)
    q_table = qualified(schema, table)
    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {quote_identifier(schema)}")
    definitions = ", ".join(f"{quote_column_identifier(column)} {column_types[column]}" for column in columns)
    pk_sql = ", ".join(quote_column_identifier(column) for column in primary_key)
    cursor.execute(f"CREATE TABLE IF NOT EXISTS {q_table} ({definitions}, PRIMARY KEY ({pk_sql}))")
    for column in columns:
        cursor.execute(f"ALTER TABLE {q_table} ADD COLUMN IF NOT EXISTS {quote_column_identifier(column)} {column_types[column]}")
    _ensure_primary_key(cursor, schema=schema, table=table, primary_key=primary_key)
    columns_to_drop = set(drop_columns)
    if drop_absent_retired_horizon_columns:
        columns_to_drop.update(
            absent_retired_horizon_columns(
                cursor,
                schema=schema,
                table=table,
                current_columns=set(columns),
            )
        )
    for column in columns_to_drop:
        cursor.execute(f"ALTER TABLE {q_table} DROP COLUMN IF EXISTS {quote_column_identifier(column)}")

    placeholders = ["%s::jsonb" if column_types[column] == "JSONB" else "%s" for column in columns]
    updates = ", ".join(
        f"{quote_column_identifier(column)} = EXCLUDED.{quote_column_identifier(column)}"
        for column in columns
        if column not in primary_key
    )
    insert_sql = f"""
        INSERT INTO {q_table} ({", ".join(quote_column_identifier(column) for column in columns)})
        VALUES ({", ".join(placeholders)})
        ON CONFLICT ({pk_sql}) DO UPDATE SET {updates}
    """
    batch: list[list[Any]] = []
    for row in rows:
        batch.append([
            json.dumps(row.get(column), sort_keys=True, default=str) if column_types[column] == "JSONB" else _jsonable(row.get(column))
            for column in columns
        ])
        if len(batch) >= DEFAULT_WRITE_BATCH_SIZE:
            cursor.executemany(insert_sql, batch)
            batch = []
    if batch:
        cursor.executemany(insert_sql, batch)


def _ensure_primary_key(cursor: Any, *, schema: str, table: str, primary_key: Sequence[str]) -> None:
    cursor.execute(
        """
        SELECT 1
        FROM pg_index
        WHERE indrelid = %s::regclass AND indisprimary
        """,
        (f"{schema}.{table}",),
    )
    if cursor.fetchone():
        return
    q_table = qualified(schema, table)
    pk_sql = ", ".join(quote_column_identifier(column) for column in primary_key)
    cursor.execute(f"ALTER TABLE {q_table} ADD PRIMARY KEY ({pk_sql})")


def drop_absent_retired_horizon_columns(
    cursor: Any,
    *,
    schema: str,
    table: str,
    current_columns: set[str] | None = None,
) -> None:
    q_table = qualified(schema, table)
    for column in absent_retired_horizon_columns(
        cursor,
        schema=schema,
        table=table,
        current_columns=current_columns or set(),
    ):
        cursor.execute(f"ALTER TABLE {q_table} DROP COLUMN IF EXISTS {quote_column_identifier(column)}")


def absent_retired_horizon_columns(cursor: Any, *, schema: str, table: str, current_columns: set[str]) -> set[str]:
    cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        """,
        (schema, table),
    )
    return {
        str(_row_value(row, "column_name"))
        for row in cursor.fetchall()
        if str(_row_value(row, "column_name")) not in current_columns
        and _is_retired_horizon_column(str(_row_value(row, "column_name")))
    }


def _row_value(row: Any, key: str) -> Any:
    if isinstance(row, Mapping):
        return row.get(key)
    return row[0]


def _is_retired_horizon_column(column: str) -> bool:
    return bool(re.match(r"^\d+_", column)) and any(column.endswith(f"_{suffix}") for suffix in RETIRED_HORIZON_SUFFIXES)


def _column_type(rows: Sequence[Mapping[str, Any]], column: str) -> str:
    values = [row.get(column) for row in rows if row.get(column) is not None]
    first = values[0] if values else None
    if isinstance(first, Mapping) or (isinstance(first, Sequence) and not isinstance(first, (str, bytes, bytearray))):
        return "JSONB"
    if column in {"available_time", "tradeable_time"}:
        return "TIMESTAMPTZ"
    if isinstance(first, bool):
        return "BOOLEAN"
    if isinstance(first, int) and not isinstance(first, bool):
        return "INTEGER"
    if isinstance(first, float):
        return "DOUBLE PRECISION"
    if len(column) > 2 and column[0].isdigit() and column[1] == "_" and first is None:
        return "DOUBLE PRECISION"
    return "TEXT"


def _column_types(rows: Sequence[Mapping[str, Any]], columns: Sequence[str]) -> dict[str, str]:
    return {column: _column_type(rows, column) for column in columns}


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value
