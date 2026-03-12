from __future__ import annotations

from typing import Any

from src.review.ingestion import _merge_metric_fields, _safe_float
from src.review.performance import DEFAULT_COMPARE_ACCOUNTS


def build_account_metrics_from_cycle(*, receipt: Any = None, reconcile_result: Any = None, balance_summary: dict[str, Any] | None = None) -> dict[str, dict[str, float]]:
    """Build canonical per-account metrics from one execution cycle.

    Current scope:
    - fee/funding/performance hints from execution receipt raw payloads
    - equity / pnl snapshots from optional balance summaries

    The result keeps backward-compatible fields (`pnl_usdt`, `equity_usdt`,
    `fee_usdt`) while also exposing richer canonical review fields.
    """

    metrics: dict[str, dict[str, float]] = {}

    raw = getattr(receipt, 'raw', None)
    account = getattr(receipt, 'account', None)
    if isinstance(raw, dict):
        alias = raw.get('account_alias') or account
        if alias in DEFAULT_COMPARE_ACCOUNTS:
            target = metrics.setdefault(alias, {})
            _merge_metric_fields(target, raw, overwrite=False)

    if isinstance(balance_summary, dict):
        alias = balance_summary.get('account_alias') or account
        if alias in DEFAULT_COMPARE_ACCOUNTS:
            target = metrics.setdefault(alias, {})
            _merge_metric_fields(target, balance_summary, overwrite=True)
            equity_usdt = _safe_float(balance_summary.get('equity_usdt'))
            pnl_usdt = _safe_float(balance_summary.get('pnl_usdt'))
            if equity_usdt is not None:
                target.setdefault('equity_end_usdt', equity_usdt)
                target.setdefault('equity_usdt', equity_usdt)
            if pnl_usdt is not None:
                target.setdefault('unrealized_pnl_usdt', pnl_usdt)
                target.setdefault('pnl_usdt', pnl_usdt)

    return metrics
