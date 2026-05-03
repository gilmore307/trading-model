"""Compatibility exports for promotion persistence helpers.

New code should import from ``model_governance.promotion.persistence``.
"""

from model_governance.promotion.persistence import database_url, render_promotion_persistence_sql, run_psql

__all__ = ["database_url", "render_promotion_persistence_sql", "run_psql"]
