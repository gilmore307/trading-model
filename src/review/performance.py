from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from src.config.accounts import V2_ACCOUNTS
from src.review.compare import FLAT_COMPARE_ALIAS


@dataclass(slots=True)
class AccountPerformance:
    account: str
    pnl_usdt: float | None = None
    realized_pnl_usdt: float | None = None
    unrealized_pnl_usdt: float | None = None
    unrealized_pnl_start_usdt: float | None = None
    unrealized_pnl_change_usdt: float | None = None
    equity_usdt: float | None = None
    equity_start_usdt: float | None = None
    equity_end_usdt: float | None = None
    equity_change_usdt: float | None = None
    trade_count: int | None = None
    fee_usdt: float | None = None
    funding_usdt: float | None = None
    funding_total_usdt: float | None = None
    exposure_time_pct: float | None = None
    max_drawdown_pct: float | None = None
    source: str = 'pending'


def _canonical_pnl(raw: dict[str, Any]) -> float | None:
    pnl = raw.get('pnl_usdt')
    if pnl is not None:
        return float(pnl)
    realized = raw.get('realized_pnl_usdt')
    unrealized = raw.get('unrealized_pnl_usdt')
    if realized is not None or unrealized is not None:
        return float(realized or 0.0) + float(unrealized or 0.0)
    return None


def _canonical_equity_end(raw: dict[str, Any]) -> float | None:
    equity_end = raw.get('equity_end_usdt')
    if equity_end is not None:
        return float(equity_end)
    equity = raw.get('equity_usdt')
    if equity is not None:
        return float(equity)
    return None


DEFAULT_COMPARE_ACCOUNTS = [account.alias for account in V2_ACCOUNTS] + [FLAT_COMPARE_ALIAS, 'router_composite']


def build_performance_snapshot(metrics_by_account: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    metrics_by_account = metrics_by_account or {}
    accounts: list[dict[str, Any]] = []
    highlights: list[str] = []

    for alias in DEFAULT_COMPARE_ACCOUNTS:
        raw = metrics_by_account.get(alias, {})
        canonical_pnl = _canonical_pnl(raw)
        canonical_equity_end = _canonical_equity_end(raw)
        row = AccountPerformance(
            account=alias,
            pnl_usdt=canonical_pnl,
            realized_pnl_usdt=None if raw.get('realized_pnl_usdt') is None else float(raw.get('realized_pnl_usdt')),
            unrealized_pnl_usdt=None if raw.get('unrealized_pnl_usdt') is None else float(raw.get('unrealized_pnl_usdt')),
            unrealized_pnl_start_usdt=None if raw.get('unrealized_pnl_start_usdt') is None else float(raw.get('unrealized_pnl_start_usdt')),
            unrealized_pnl_change_usdt=None if raw.get('unrealized_pnl_change_usdt') is None else float(raw.get('unrealized_pnl_change_usdt')),
            equity_usdt=canonical_equity_end,
            equity_start_usdt=None if raw.get('equity_start_usdt') is None else float(raw.get('equity_start_usdt')),
            equity_end_usdt=canonical_equity_end,
            equity_change_usdt=None if raw.get('equity_change_usdt') is None else float(raw.get('equity_change_usdt')),
            trade_count=None if raw.get('trade_count') is None else int(raw.get('trade_count')),
            fee_usdt=None if raw.get('fee_usdt') is None else float(raw.get('fee_usdt')),
            funding_usdt=None if raw.get('funding_usdt') is None else float(raw.get('funding_usdt')),
            funding_total_usdt=None if raw.get('funding_total_usdt') is None else float(raw.get('funding_total_usdt')),
            exposure_time_pct=None if raw.get('exposure_time_pct') is None else float(raw.get('exposure_time_pct')),
            max_drawdown_pct=None if raw.get('max_drawdown_pct') is None else float(raw.get('max_drawdown_pct')),
            source=str(raw.get('source') or 'pending'),
        )
        accounts.append(asdict(row))
        if row.pnl_usdt is not None:
            highlights.append(f'pnl_available:{alias}')
        if row.equity_end_usdt is not None:
            highlights.append(f'equity_available:{alias}')
        if row.fee_usdt is not None:
            highlights.append(f'fee_available:{alias}')
        if row.funding_usdt is not None:
            highlights.append(f'funding_available:{alias}')

    return {
        'accounts': accounts,
        'highlights': sorted(set(highlights)),
        'status': 'ready' if metrics_by_account else 'pending_data',
    }
