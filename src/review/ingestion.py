from __future__ import annotations

from typing import Any

from src.review.compare import FLAT_COMPARE_ALIAS
from src.review.performance import DEFAULT_COMPARE_ACCOUNTS


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def canonicalize_history_row(row: dict[str, Any]) -> dict[str, dict[str, float]]:
    """Extract canonical performance hints from one execution artifact row.

    Priority today:
    1. fee_usdt from receipt.raw (already present in OKX execution receipts)
    2. optional pnl/equity snapshots if later artifacts include them

    This keeps review aggregation forward-compatible without forcing a specific
    runtime persistence format right now.
    """

    metrics: dict[str, dict[str, float]] = {}

    receipt = row.get('receipt') or {}
    receipt_raw = receipt.get('raw') if isinstance(receipt, dict) else {}
    if not isinstance(receipt_raw, dict):
        receipt_raw = {}

    receipt_account = receipt.get('account') if isinstance(receipt, dict) else None
    raw_account = receipt_raw.get('account_alias') if isinstance(receipt_raw, dict) else None
    account = raw_account or receipt_account
    if account in DEFAULT_COMPARE_ACCOUNTS:
        fee_usdt = _safe_float(receipt_raw.get('fee_usdt'))
        if fee_usdt is not None:
            metrics.setdefault(account, {})['fee_usdt'] = fee_usdt

    summary = row.get('summary') or {}
    summary_metrics = summary.get('account_metrics') if isinstance(summary, dict) else None
    if isinstance(summary_metrics, dict):
        for alias, raw in summary_metrics.items():
            if alias not in DEFAULT_COMPARE_ACCOUNTS or not isinstance(raw, dict):
                continue
            target = metrics.setdefault(alias, {})
            for key in ('pnl_usdt', 'equity_usdt', 'fee_usdt'):
                value = _safe_float(raw.get(key))
                if value is not None:
                    target[key] = value

    compare_snapshot = row.get('compare_snapshot') or {}
    for account_row in compare_snapshot.get('accounts', []) if isinstance(compare_snapshot, dict) else []:
        if not isinstance(account_row, dict):
            continue
        alias = account_row.get('account')
        if alias not in DEFAULT_COMPARE_ACCOUNTS:
            continue
        target = metrics.setdefault(alias, {})
        for key in ('pnl_usdt', 'equity_usdt', 'fee_usdt'):
            value = _safe_float(account_row.get(key))
            if value is not None:
                target[key] = value

    # Keep flat compare addressable even when no explicit row exists.
    metrics.setdefault(FLAT_COMPARE_ALIAS, {})
    return metrics
