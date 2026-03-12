from __future__ import annotations

from typing import Any

from src.review.compare import FLAT_COMPARE_ALIAS
from src.review.performance import DEFAULT_COMPARE_ACCOUNTS


CANONICAL_NUMERIC_FIELDS = (
    'realized_pnl_usdt',
    'unrealized_pnl_usdt',
    'pnl_usdt',
    'equity_usdt',
    'equity_start_usdt',
    'equity_end_usdt',
    'equity_change_usdt',
    'fee_usdt',
    'funding_usdt',
    'funding_total_usdt',
    'trade_count',
    'exposure_time_pct',
    'max_drawdown_pct',
)


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _merge_metric_fields(target: dict[str, float], raw: dict[str, Any], *, overwrite: bool = True) -> None:
    for key in CANONICAL_NUMERIC_FIELDS:
        value = _safe_float(raw.get(key))
        if value is None:
            continue
        if overwrite or key not in target:
            target[key] = value

    if 'pnl_usdt' not in target:
        total = _safe_float(raw.get('total_pnl_usdt'))
        if total is not None:
            target['pnl_usdt'] = total
    if 'pnl_usdt' not in target:
        realized = _safe_float(raw.get('realized_pnl_usdt'))
        unrealized = _safe_float(raw.get('unrealized_pnl_usdt'))
        if realized is not None or unrealized is not None:
            target['pnl_usdt'] = float(realized or 0.0) + float(unrealized or 0.0)

    if 'equity_usdt' not in target:
        equity_end = _safe_float(raw.get('equity_end_usdt'))
        if equity_end is not None:
            target['equity_usdt'] = equity_end
    if 'equity_end_usdt' not in target:
        equity = _safe_float(raw.get('equity_usdt'))
        if equity is not None:
            target['equity_end_usdt'] = equity

    if 'equity_change_usdt' not in target:
        start = _safe_float(raw.get('equity_start_usdt'))
        end = _safe_float(raw.get('equity_end_usdt'))
        if start is None:
            start = _safe_float(raw.get('equity_start'))
        if end is None:
            end = _safe_float(raw.get('equity_usdt'))
        if start is not None and end is not None:
            target['equity_change_usdt'] = end - start


def canonicalize_history_row(row: dict[str, Any]) -> dict[str, dict[str, float]]:
    """Extract canonical performance hints from one execution artifact row.

    Current priority:
    1. receipt.raw / receipt-level performance hints
    2. summary.account_metrics canonical payload
    3. compare_snapshot embedded performance rows

    The extractor is intentionally permissive so runtime artifacts can evolve
    without forcing repeated review-pipeline rewrites.
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
        target = metrics.setdefault(account, {})
        _merge_metric_fields(target, receipt_raw, overwrite=False)

    summary = row.get('summary') or {}
    summary_metrics = summary.get('account_metrics') if isinstance(summary, dict) else None
    if isinstance(summary_metrics, dict):
        for alias, raw in summary_metrics.items():
            if alias not in DEFAULT_COMPARE_ACCOUNTS or not isinstance(raw, dict):
                continue
            target = metrics.setdefault(alias, {})
            _merge_metric_fields(target, raw, overwrite=True)

    compare_snapshot = row.get('compare_snapshot') or {}
    for account_row in compare_snapshot.get('accounts', []) if isinstance(compare_snapshot, dict) else []:
        if not isinstance(account_row, dict):
            continue
        alias = account_row.get('account')
        if alias not in DEFAULT_COMPARE_ACCOUNTS:
            continue
        target = metrics.setdefault(alias, {})
        _merge_metric_fields(target, account_row, overwrite=True)

    # Keep flat compare addressable even when no explicit row exists.
    metrics.setdefault(FLAT_COMPARE_ALIAS, {})
    return metrics
