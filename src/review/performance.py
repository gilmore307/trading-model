from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from src.config.accounts import V2_ACCOUNTS
from src.review.compare import FLAT_COMPARE_ALIAS


@dataclass(slots=True)
class AccountPerformance:
    account: str
    pnl_usdt: float | None = None
    equity_usdt: float | None = None
    trade_count: int | None = None
    fee_usdt: float | None = None
    exposure_time_pct: float | None = None
    source: str = 'pending'


DEFAULT_COMPARE_ACCOUNTS = [account.alias for account in V2_ACCOUNTS] + [FLAT_COMPARE_ALIAS, 'router_composite']


def build_performance_snapshot(metrics_by_account: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    metrics_by_account = metrics_by_account or {}
    accounts: list[dict[str, Any]] = []
    highlights: list[str] = []

    for alias in DEFAULT_COMPARE_ACCOUNTS:
        raw = metrics_by_account.get(alias, {})
        row = AccountPerformance(
            account=alias,
            pnl_usdt=None if raw.get('pnl_usdt') is None else float(raw.get('pnl_usdt')),
            equity_usdt=None if raw.get('equity_usdt') is None else float(raw.get('equity_usdt')),
            trade_count=None if raw.get('trade_count') is None else int(raw.get('trade_count')),
            fee_usdt=None if raw.get('fee_usdt') is None else float(raw.get('fee_usdt')),
            exposure_time_pct=None if raw.get('exposure_time_pct') is None else float(raw.get('exposure_time_pct')),
            source=str(raw.get('source') or 'pending'),
        )
        accounts.append(asdict(row))
        if row.pnl_usdt is not None:
            highlights.append(f'pnl_available:{alias}')
        if row.fee_usdt is not None:
            highlights.append(f'fee_available:{alias}')

    return {
        'accounts': accounts,
        'highlights': sorted(set(highlights)),
        'status': 'ready' if metrics_by_account else 'pending_data',
    }
