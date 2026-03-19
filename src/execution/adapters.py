from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from src.config.settings import Settings
from src.execution.identifiers import build_okx_cl_ord_id, generate_execution_id
from src.exchange.okx_client import OkxClient


@dataclass(slots=True)
class ExecutionReceipt:
    accepted: bool
    mode: str
    account: str
    symbol: str
    action: str
    side: str | None
    size: float | None
    order_id: str | None
    reason: str
    observed_at: datetime
    raw: dict | None = None
    execution_id: str | None = None
    client_order_id: str | None = None
    trade_ids: list[str] | None = None


class ExecutionAdapter:
    def submit_entry(self, *, account: str, symbol: str, side: str, size: float, reason: str) -> ExecutionReceipt:
        raise NotImplementedError

    def submit_exit(self, *, account: str, symbol: str, reason: str, requested_size: float | None = None) -> ExecutionReceipt:
        raise NotImplementedError


class DryRunExecutionAdapter(ExecutionAdapter):
    def submit_entry(self, *, account: str, symbol: str, side: str, size: float, reason: str) -> ExecutionReceipt:
        execution_id = generate_execution_id(account=account, symbol=symbol, action='entry')
        client_order_id = build_okx_cl_ord_id(execution_id=execution_id, account=account, symbol=symbol, action='entry')
        return ExecutionReceipt(
            accepted=True,
            mode='dry_run',
            account=account,
            symbol=symbol,
            action='entry',
            side=side,
            size=size,
            order_id='dry-run-entry',
            reason=reason,
            observed_at=datetime.now(UTC),
            raw={'dry_run': True, 'execution_id': execution_id, 'client_order_id': client_order_id, 'trade_ids': []},
            execution_id=execution_id,
            client_order_id=client_order_id,
            trade_ids=[],
        )

    def submit_exit(self, *, account: str, symbol: str, reason: str, requested_size: float | None = None) -> ExecutionReceipt:
        execution_id = generate_execution_id(account=account, symbol=symbol, action='exit')
        client_order_id = build_okx_cl_ord_id(execution_id=execution_id, account=account, symbol=symbol, action='exit')
        return ExecutionReceipt(
            accepted=True,
            mode='dry_run',
            account=account,
            symbol=symbol,
            action='exit',
            side=None,
            size=None,
            order_id='dry-run-exit',
            reason=reason,
            observed_at=datetime.now(UTC),
            raw={'dry_run': True, 'execution_id': execution_id, 'client_order_id': client_order_id, 'trade_ids': []},
            execution_id=execution_id,
            client_order_id=client_order_id,
            trade_ids=[],
        )


class OkxExecutionAdapter(ExecutionAdapter):
    def __init__(self, settings: Settings):
        self.settings = settings

    def _client(self, account: str) -> OkxClient:
        strategy_name = self.settings.strategy_for_account_alias(account) or account
        return OkxClient(self.settings, self.settings.account_for_strategy(strategy_name))

    def submit_entry(self, *, account: str, symbol: str, side: str, size: float, reason: str) -> ExecutionReceipt:
        strategy_name = self.settings.strategy_for_account_alias(account) or account
        client = self._client(account)
        notional_usdt = float(self.settings.default_order_size_usdt) * float(size)
        execution_id = generate_execution_id(account=account, symbol=symbol, action='entry')
        client_order_id = build_okx_cl_ord_id(execution_id=execution_id, account=account, symbol=symbol, action='entry')
        result = client.create_entry_order(
            self.settings.execution_symbol(strategy_name, symbol),
            side,
            notional_usdt,
            client_order_id=client_order_id,
            execution_id=execution_id,
        )
        return ExecutionReceipt(
            accepted=bool(result.get('order_id')),
            mode='okx_demo' if self.settings.okx_demo else 'okx_live',
            account=account,
            symbol=symbol,
            action='entry',
            side=side,
            size=float(result.get('amount') or 0.0),
            order_id=result.get('order_id'),
            reason=reason,
            observed_at=datetime.now(UTC),
            raw=result,
            execution_id=result.get('execution_id') or execution_id,
            client_order_id=result.get('client_order_id') or client_order_id,
            trade_ids=result.get('trade_ids'),
        )

    def submit_exit(self, *, account: str, symbol: str, reason: str, requested_size: float | None = None) -> ExecutionReceipt:
        strategy_name = self.settings.strategy_for_account_alias(account) or account
        client = self._client(account)
        execution_id = generate_execution_id(account=account, symbol=symbol, action='exit')
        client_order_id = build_okx_cl_ord_id(execution_id=execution_id, account=account, symbol=symbol, action='exit')
        current = client.current_live_position(self.settings.execution_symbol(strategy_name, symbol))
        target_contracts = float(requested_size) if requested_size is not None else None
        if current is None:
            return ExecutionReceipt(
                accepted=False,
                mode='okx_demo' if self.settings.okx_demo else 'okx_live',
                account=account,
                symbol=symbol,
                action='exit',
                side=None,
                size=None,
                order_id=None,
                reason='no_live_exchange_position_for_exit',
                observed_at=datetime.now(UTC),
                raw={'execution_id': execution_id, 'client_order_id': client_order_id, 'trade_ids': []},
                execution_id=execution_id,
                client_order_id=client_order_id,
                trade_ids=[],
            )
        result = client.create_exit_order(
            self.settings.execution_symbol(strategy_name, symbol),
            current.get('side'),
            target_contracts if target_contracts is not None else float(current.get('contracts') or 0.0),
            client_order_id=client_order_id,
            execution_id=execution_id,
        )
        return ExecutionReceipt(
            accepted=bool(result.get('order_id')),
            mode='okx_demo' if self.settings.okx_demo else 'okx_live',
            account=account,
            symbol=symbol,
            action='exit',
            side=None,
            size=float(result.get('amount') or 0.0) if result.get('amount') is not None else None,
            order_id=result.get('order_id'),
            reason=reason,
            observed_at=datetime.now(UTC),
            raw=result,
            execution_id=result.get('execution_id') or execution_id,
            client_order_id=result.get('client_order_id') or client_order_id,
            trade_ids=result.get('trade_ids'),
        )
