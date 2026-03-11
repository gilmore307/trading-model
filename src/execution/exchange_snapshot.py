from __future__ import annotations

from dataclasses import dataclass

from src.config.settings import Settings
from src.exchange.okx_client import OkxClient, live_position_snapshot
from src.reconcile.alignment import ExchangePositionSnapshot


@dataclass(slots=True)
class ExchangeSnapshotProvider:
    settings: Settings

    def fetch_position(self, account: str, symbol: str) -> ExchangePositionSnapshot | None:
        strategy_name = self.settings.strategy_for_account_alias(account) or account
        okx = OkxClient(self.settings, self.settings.account_for_strategy(strategy_name))
        execution_symbol = self.settings.execution_symbol(strategy_name, symbol)
        snap = live_position_snapshot(okx.exchange, execution_symbol)
        if snap is None:
            return None
        return ExchangePositionSnapshot(
            account=account,
            symbol=symbol,
            side=snap.get('side'),
            size=float(snap.get('contracts') or 0.0),
        )
