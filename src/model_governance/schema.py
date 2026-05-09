"""Aggregate schema helpers for model governance evidence tables.

Dataset and evaluation evidence tables live in ``model_governance/evaluation``.
Promotion decision, activation, rollback, and manager-control-plane persistence
belong in ``trading-manager`` and are intentionally not defined here.
"""
from __future__ import annotations

from typing import Any

from model_governance.common.sql import DEFAULT_SCHEMA, qualified, quote_identifier
from model_governance.evaluation.schema import EVALUATION_TABLE_NAMES, create_evaluation_schema_sql

TABLE_NAMES = EVALUATION_TABLE_NAMES


def create_governance_schema_sql(schema: str = DEFAULT_SCHEMA) -> list[str]:
    """Return ordered DDL statements for model-side evidence schema."""
    return [
        f"CREATE SCHEMA IF NOT EXISTS {quote_identifier(schema)}",
        *create_evaluation_schema_sql(schema),
    ]


def ensure_model_governance_schema(cursor: Any, *, schema: str = DEFAULT_SCHEMA) -> None:
    """Create generic governance/evaluation evidence tables if absent."""
    for statement in create_governance_schema_sql(schema):
        cursor.execute(statement)


__all__ = [
    "DEFAULT_SCHEMA",
    "TABLE_NAMES",
    "create_governance_schema_sql",
    "ensure_model_governance_schema",
    "qualified",
    "quote_identifier",
]
