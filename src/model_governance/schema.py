"""Aggregate schema helpers for model governance tables.

Dataset/evaluation evidence and promotion lifecycle DDL live in separate
subpackages. This module only preserves the aggregate operational entrypoint.
"""
from __future__ import annotations

from typing import Any

from model_governance.common.sql import DEFAULT_SCHEMA, qualified, quote_identifier
from model_governance.evaluation.schema import EVALUATION_TABLE_NAMES, create_evaluation_schema_sql
from model_governance.promotion.schema import PROMOTION_TABLE_NAMES, create_promotion_schema_sql

TABLE_NAMES = EVALUATION_TABLE_NAMES + PROMOTION_TABLE_NAMES


def create_governance_schema_sql(schema: str = DEFAULT_SCHEMA) -> list[str]:
    """Return ordered DDL statements for the full model governance schema."""
    return [
        f"CREATE SCHEMA IF NOT EXISTS {quote_identifier(schema)}",
        *create_evaluation_schema_sql(schema),
        *create_promotion_schema_sql(schema),
    ]


def ensure_model_governance_schema(cursor: Any, *, schema: str = DEFAULT_SCHEMA) -> None:
    """Create generic governance/evaluation/promotion tables if absent."""
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
