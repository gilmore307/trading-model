from __future__ import annotations

from typing import Any

from src.review.ingestion import _merge_metric_fields, _safe_float
from src.review.performance import DEFAULT_COMPARE_ACCOUNTS


def build_account_metrics_from_cycle(*, receipt: Any = None, reconcile_result: Any = None, balance_summary: dict[str, Any] | None = None) -> dict[str, dict[str, float]]:
    """Build canonical per-account metrics from one execution cycle.

    Current scope:
    - fee/funding/performance hints from execution receipt raw payloads
    - equity / pnl snapshots from optional balance summaries

    The result preserves compatibility mirrors (`pnl_usdt`, `equity_usdt`,
    `fee_usdt`) while centering richer canonical review fields.
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
            sanitized_balance_summary = {k: v for k, v in balance_summary.items() if k != 'pnl_usdt'}
            _merge_metric_fields(target, sanitized_balance_summary, overwrite=True)
            equity_usdt = _safe_float(balance_summary.get('equity_end_usdt', balance_summary.get('equity_usdt')))
            unrealized_pnl_usdt = _safe_float(
                balance_summary.get('unrealized_pnl_usdt', balance_summary.get('pnl_usdt'))
            )
            if equity_usdt is not None:
                target.setdefault('equity_end_usdt', equity_usdt)
                target.setdefault('equity_usdt', equity_usdt)
            if unrealized_pnl_usdt is not None:
                target['unrealized_pnl_usdt'] = unrealized_pnl_usdt
                if target.get('realized_pnl_usdt') is not None:
                    target['pnl_usdt'] = float(target.get('realized_pnl_usdt') or 0.0) + unrealized_pnl_usdt
                elif target.get('pnl_usdt') is None:
                    target['pnl_usdt'] = unrealized_pnl_usdt

    if isinstance(balance_summary, dict):
        for alias, target in metrics.items():
            if target.get('equity_change_usdt') is None:
                start = _safe_float(target.get('equity_start_usdt'))
                end = _safe_float(target.get('equity_end_usdt', target.get('equity_usdt')))
                if start is not None and end is not None:
                    target['equity_change_usdt'] = end - start

    return metrics
