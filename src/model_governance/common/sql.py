"""Shared SQL helpers for model governance packages."""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from model_runtime.config import database_url_file

DEFAULT_SCHEMA = "trading_model"
DEFAULT_DB_URL_FILE = database_url_file()
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def quote_identifier(identifier: str) -> str:
    """Return a safely quoted SQL identifier."""
    if not _IDENTIFIER_RE.match(identifier):
        raise ValueError(f"unsafe SQL identifier: {identifier!r}")
    return '"' + identifier.replace('"', '""') + '"'


def qualified(schema: str, table: str) -> str:
    return f"{quote_identifier(schema)}.{quote_identifier(table)}"


def database_url(explicit: str | None = None) -> str:
    """Resolve the PostgreSQL URL using the repository-standard secret lookup."""
    if explicit:
        return explicit
    for env_name in ("TRADING_MODEL_DATABASE_URL", "OPENCLAW_DATABASE_URL"):
        value = os.environ.get(env_name, "").strip()
        if value:
            return value
    if DEFAULT_DB_URL_FILE.exists():
        return DEFAULT_DB_URL_FILE.read_text(encoding="utf-8").strip()
    raise SystemExit(f"database URL not supplied and {DEFAULT_DB_URL_FILE} does not exist")


def run_psql(database_url_value: str, sql: str) -> None:
    """Run SQL through psql inside one transaction."""
    subprocess.run(
        ["psql", database_url_value, "-v", "ON_ERROR_STOP=1", "-q"],
        input=f"BEGIN;\n{sql}\nCOMMIT;\n",
        text=True,
        check=True,
    )


def json_literal(value: Any) -> str:
    return sql_literal(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str))


def sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int | float) and not isinstance(value, bool):
        return repr(value)
    return "'" + str(value).replace("'", "''") + "'"
