from __future__ import annotations

from typing import Any

from src.review.performance import DEFAULT_COMPARE_ACCOUNTS


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_account_metrics_from_cycle(*, receipt: Any = None, reconcile_result: Any = None) -> dict[str, dict[str, float]]:
    """Build canonical per-account metrics from one execution cycle.

    Current scope is intentionally conservative:
    - fee_usdt from execution receipt raw payloads
    - a future extension point for pnl/equity once cycle artifacts persist them
    """

    metrics: dict[str, dict[str, float]] = {}

    raw = getattr(receipt, 'raw', None)
    account = getattr(receipt, 'account', None)
    if isinstance(raw, dict):
        alias = raw.get('account_alias') or account
        if alias in DEFAULT_COMPARE_ACCOUNTS:
            fee_usdt = _safe_float(raw.get('fee_usdt'))
            if fee_usdt is not None:
                metrics.setdefault(alias, {})['fee_usdt'] = fee_usdt

    return metrics
