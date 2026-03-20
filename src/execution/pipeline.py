from __future__ import annotations

from dataclasses import asdict, dataclass, field

from src.config.settings import Settings
from src.execution.adapters import DryRunExecutionAdapter, ExecutionAdapter, ExecutionReceipt, OkxExecutionAdapter
from src.execution.controller import RouteController, RouteControlResult
from src.execution.exchange_snapshot import ExchangeSnapshotProvider
from src.reconcile.alignment import ExchangePositionSnapshot
from src.routing.composite import RouterCompositeSimulator
from src.runners.regime_runner import BtcRegimeRunner, RegimeRunnerOutput
from src.runtime.mode_policy import policy_for_mode
from src.runtime.store import RuntimeStore
from src.state.live_position import LivePosition
from src.strategies.executors import ExecutionPlan, executor_for


@dataclass(slots=True)
class ExecutionDecisionTrace:
    mode: str
    mode_allows_routing: bool
    decision_trade_enabled: bool
    route_trade_enabled: bool
    pipeline_trade_enabled: bool
    pipeline_entered: bool = False
    submission_allowed: bool = False
    submission_attempted: bool = False
    allow_reason: str | None = None
    block_reason: str | None = None
    diagnostics: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ExecutionCycleResult:
    regime_output: RegimeRunnerOutput
    plan: ExecutionPlan
    receipt: ExecutionReceipt | None
    local_position: LivePosition | None
    verification_position: LivePosition | None
    reconcile_result: RouteControlResult | None
    decision_trace: ExecutionDecisionTrace
    runtime_state: dict
    route_state: dict | None
    live_positions: list[dict]
    router_composite: dict


class ExecutionPipeline:
    """Skeleton execution pipeline.

    Phase 1 scope:
    - run regime runner
    - derive a plan
    - send state transitions through RouteController
    - verify/reconcile against a provided exchange snapshot

    This intentionally stops short of real order placement.
    """

    def __init__(self, regime_runner: BtcRegimeRunner | None = None, controller: RouteController | None = None, snapshot_provider: ExchangeSnapshotProvider | None = None, adapter: ExecutionAdapter | None = None, settings: Settings | None = None, runtime_store: RuntimeStore | None = None, composite_simulator: RouterCompositeSimulator | None = None):
        self.settings = settings or Settings.load()
        self.regime_runner = regime_runner or BtcRegimeRunner(self.settings)
        self.controller = controller or RouteController(verification_cycle_timeout=self.settings.verification_cycle_timeout)
        self.snapshot_provider = snapshot_provider or ExchangeSnapshotProvider(self.settings)
        self.adapter = adapter or DryRunExecutionAdapter()
        self.runtime_store = runtime_store or RuntimeStore()
        self.composite_simulator = composite_simulator or RouterCompositeSimulator(self.controller.store)

    def build_plan(self, output: RegimeRunnerOutput) -> ExecutionPlan:
        return executor_for(output).build_plan(output)

    def _initial_trace(self, mode, mode_policy, regime_output: RegimeRunnerOutput) -> ExecutionDecisionTrace:
        summary = regime_output.decision_summary or {}
        return ExecutionDecisionTrace(
            mode=mode.value,
            mode_allows_routing=mode_policy.allow_normal_routing,
            decision_trade_enabled=bool(summary.get('trade_enabled', regime_output.final_decision.get('tradable', False))),
            route_trade_enabled=bool(regime_output.route_decision.get('trade_enabled', False)),
            pipeline_trade_enabled=False,
            pipeline_entered=False,
            submission_allowed=False,
            submission_attempted=False,
            allow_reason=summary.get('allow_reason'),
            block_reason=summary.get('block_reason'),
            diagnostics=list(summary.get('diagnostics', [])),
        )

    def _idle_regime_output(self) -> RegimeRunnerOutput:
        return RegimeRunnerOutput(
            observed_at=self.runtime_store.get().updated_at,
            symbol='BTC-USDT-SWAP',
            background_4h={'primary': 'idle', 'confidence': 0.0, 'reasons': ['strategy_execution_disabled'], 'secondary': [], 'tradable': False},
            primary_15m={'primary': 'idle', 'confidence': 0.0, 'reasons': ['strategy_execution_disabled'], 'secondary': [], 'tradable': False},
            override_1m=None,
            background_features={},
            primary_features={},
            override_features={},
            final_decision={'primary': 'idle', 'confidence': 0.0, 'reasons': ['strategy_execution_disabled'], 'secondary': [], 'tradable': False},
            route_decision={'regime': 'idle', 'account': None, 'strategy_family': None, 'trade_enabled': False, 'allow_reason': None, 'block_reason': 'strategy_execution_disabled'},
            decision_summary={'regime': 'idle', 'confidence': 0.0, 'tradable': False, 'account': None, 'strategy_family': None, 'trade_enabled': False, 'allow_reason': None, 'block_reason': 'strategy_execution_disabled', 'reasons': ['strategy_execution_disabled'], 'secondary': [], 'diagnostics': ['strategy_execution_disabled']},
        )

    def _entry_preflight(self, account: str, symbol: str, size: float | None) -> tuple[bool, str | None]:
        if not isinstance(self.adapter, OkxExecutionAdapter):
            return True, None
        try:
            strategy_name = self.settings.strategy_for_account_alias(account) or account
            client = self.adapter._client(account)
            summary = client.account_balance_summary()
        except Exception as exc:
            return False, f'preflight_balance_check_failed:{exc}'

        usdt_available = float(summary.get('usdt_available') or 0.0)
        notional_needed = float(self.settings.default_order_size_usdt) * float(size or 0.0)
        threshold = notional_needed + float(self.settings.buffer_capital_usdt or 0.0)
        if usdt_available < threshold:
            execution_symbol = self.settings.execution_symbol(strategy_name, symbol)
            return False, f'preflight_insufficient_usdt_margin:{account}:{execution_symbol}:available={usdt_available}:required={threshold}'
        return True, None

    def run_cycle(self, exchange_snapshot: ExchangePositionSnapshot | None = None) -> ExecutionCycleResult:
        mode = self.runtime_store.get().mode
        mode_policy = policy_for_mode(mode)
        regime_output = self.regime_runner.run_once() if mode_policy.allow_strategy_execution else self._idle_regime_output()
        trace = self._initial_trace(mode, mode_policy, regime_output)

        if not mode_policy.allow_strategy_execution:
            trace.block_reason = f'mode_no_strategy:{mode.value}'
            trace.allow_reason = None
            if 'strategy_execution_disabled' not in trace.diagnostics:
                trace.diagnostics.append('strategy_execution_disabled')
            plan = ExecutionPlan(regime='idle', account=None, action='hold', reason=trace.block_reason)
        elif not mode_policy.allow_normal_routing:
            trace.block_reason = f'mode_blocked:{mode.value}'
            trace.allow_reason = None
            trace.diagnostics.append('mode_blocked')
            plan = ExecutionPlan(regime=regime_output.final_decision['primary'], account=None, action='hold', reason=trace.block_reason)
        elif not trace.decision_trade_enabled:
            if trace.block_reason is None:
                trace.block_reason = 'decision_trade_disabled'
            trace.allow_reason = None
            trace.diagnostics.append('decision_gate_blocked')
            plan = ExecutionPlan(regime=regime_output.final_decision['primary'], account=None, action='hold', reason=trace.block_reason)
        else:
            plan = self.build_plan(regime_output)

        if plan.account is not None and not self.controller.routes.is_enabled(plan.account, regime_output.symbol):
            frozen_reason = self.controller.routes.get(plan.account, regime_output.symbol).frozen_reason or 'route_frozen'
            trace.block_reason = frozen_reason
            trace.allow_reason = None
            trace.diagnostics.append('route_frozen')
            plan = ExecutionPlan(regime=plan.regime, account=plan.account, action='hold', reason=frozen_reason)

        current_position = None
        pending_verification_priority = False
        if plan.account is not None:
            current_position = self.controller.store.get(plan.account, regime_output.symbol)
            if current_position is not None and current_position.status.value in {'entry_submitted', 'entry_verifying', 'exit_submitted', 'exit_verifying'}:
                pending_verification_priority = True
                trace.allow_reason = 'pending_verification_priority'
                if 'pending_verification_priority' not in trace.diagnostics:
                    trace.diagnostics.append('pending_verification_priority')
                plan = ExecutionPlan(
                    regime=plan.regime,
                    account=plan.account,
                    action='hold',
                    reason=f'pending_verification:{current_position.status.value}',
                )

        if plan.account is not None and plan.action == 'enter':
            preflight_ok, preflight_reason = self._entry_preflight(plan.account, regime_output.symbol, plan.size)
            if not preflight_ok:
                trace.block_reason = preflight_reason
                trace.allow_reason = None
                trace.diagnostics.append('preflight_blocked')
                plan = ExecutionPlan(regime=plan.regime, account=plan.account, action='hold', reason=preflight_reason)

        trace.pipeline_entered = plan.account is not None
        trace.submission_allowed = plan.account is not None and plan.action in {'enter', 'exit'}
        trace.submission_attempted = False
        trace.pipeline_trade_enabled = trace.submission_allowed

        if exchange_snapshot is None and plan.account is not None:
            exchange_snapshot = self.snapshot_provider.fetch_position(plan.account, regime_output.symbol)
        if mode_policy.force_dry_run:
            self.adapter = DryRunExecutionAdapter()
        receipt = None
        local_position = None
        verification_position = None
        reconcile_result = None

        def refresh_snapshot() -> ExchangePositionSnapshot | None:
            if plan.account is None:
                return exchange_snapshot
            return self.snapshot_provider.fetch_position(plan.account, regime_output.symbol)

        if plan.account is not None and not pending_verification_priority and plan.action == 'enter' and plan.side is not None and plan.size is not None:
            trace.submission_attempted = True
            receipt = self.adapter.submit_entry(account=plan.account, symbol=regime_output.symbol, side=plan.side, size=plan.size, reason=plan.reason or 'entry')
            local_position = self.controller.submit_entry(
                plan.account,
                regime_output.symbol,
                plan.regime,
                plan.side,
                float(receipt.size if receipt.size is not None else plan.size),
                entry_order_id=receipt.order_id,
                entry_execution_id=receipt.execution_id,
                entry_client_order_id=receipt.client_order_id,
                entry_trade_ids=receipt.trade_ids,
            )
            verification_hint = None if receipt.raw is None or not isinstance(receipt.raw, dict) else {
                'verified_entry': bool(receipt.raw.get('verified_entry')),
                'verification_attempts': receipt.raw.get('verification_attempts') or [],
            }
            if verification_hint is not None:
                meta = dict(local_position.meta or {})
                meta['last_verification_hint'] = verification_hint
                local_position.meta = meta
                local_position = self.controller.store.upsert(local_position)
            exchange_snapshot = refresh_snapshot()
            local_position = self.controller.refresh_local_position_from_exchange(plan.account, regime_output.symbol, exchange_snapshot) or local_position
            verification_position = self.controller.verify_position(plan.account, regime_output.symbol, exchange_snapshot)
            reconcile_result = self.controller.reconcile_account_symbol(plan.account, regime_output.symbol, exchange_snapshot)
        elif plan.account is not None and not pending_verification_priority and plan.action == 'exit':
            trace.submission_attempted = True
            requested_exit_size = None if current_position is None else float(current_position.ledger_open_size or current_position.size or 0.0)
            receipt = self.adapter.submit_exit(account=plan.account, symbol=regime_output.symbol, reason=plan.reason or 'exit', requested_size=requested_exit_size)
            local_position = self.controller.submit_exit(
                plan.account,
                regime_output.symbol,
                exit_order_id=receipt.order_id,
                exit_execution_id=receipt.execution_id,
                exit_client_order_id=receipt.client_order_id,
                exit_trade_ids=receipt.trade_ids,
                requested_size=requested_exit_size,
            )
            if local_position is not None and isinstance(receipt.raw, dict):
                meta = dict(local_position.meta or {})
                meta['last_exit_fee_usdt'] = receipt.raw.get('fee_usdt')
                meta['last_exit_realized_pnl_usdt'] = receipt.raw.get('realized_pnl_usdt')
                local_position.meta = meta
                local_position = self.controller.store.upsert(local_position)
            exchange_snapshot = refresh_snapshot()
            local_position = self.controller.refresh_local_position_from_exchange(plan.account, regime_output.symbol, exchange_snapshot) or local_position
            verification_position = self.controller.verify_position(plan.account, regime_output.symbol, exchange_snapshot)
            reconcile_result = self.controller.reconcile_account_symbol(plan.account, regime_output.symbol, exchange_snapshot)
        elif plan.account is not None and plan.action == 'arm':
            current = self.controller.store.get(plan.account, regime_output.symbol)
            if current is not None:
                exchange_snapshot = refresh_snapshot()
                current = self.controller.refresh_local_position_from_exchange(plan.account, regime_output.symbol, exchange_snapshot) or current
                if current.status.value in {'entry_submitted', 'entry_verifying', 'exit_submitted', 'exit_verifying'}:
                    current = self.controller.verify_position(plan.account, regime_output.symbol, exchange_snapshot) or current
                reconcile_result = self.controller.reconcile_account_symbol(plan.account, regime_output.symbol, exchange_snapshot)
                local_position = current
                verification_position = current
        elif plan.account is not None:
            current = current_position or self.controller.store.get(plan.account, regime_output.symbol)
            if current is not None:
                current_snapshot = exchange_snapshot if exchange_snapshot is not None else refresh_snapshot()
                if current.status.value == 'exit_verifying' and current_snapshot is not None and float(current_snapshot.size or 0.0) > 0.0 and plan.reason != f'pending_verification:{current.status.value}':
                    self.controller.mark_forced_exit_recovery(plan.account, regime_output.symbol, detail='forced_exit_recovery_submitted')
                    trace.submission_attempted = True
                    requested_exit_size = float(current.ledger_open_size or current.size or 0.0)
                    receipt = self.adapter.submit_exit(account=plan.account, symbol=regime_output.symbol, reason='forced_exit_recovery', requested_size=requested_exit_size)
                    current = self.controller.submit_exit(
                        plan.account,
                        regime_output.symbol,
                        exit_order_id=receipt.order_id,
                        exit_execution_id=receipt.execution_id,
                        exit_client_order_id=receipt.client_order_id,
                        exit_trade_ids=receipt.trade_ids,
                        requested_size=requested_exit_size,
                    ) or current
                    if current is not None and isinstance(receipt.raw, dict):
                        meta = dict(current.meta or {})
                        meta['last_exit_fee_usdt'] = receipt.raw.get('fee_usdt')
                        meta['last_exit_realized_pnl_usdt'] = receipt.raw.get('realized_pnl_usdt')
                        current.meta = meta
                        current = self.controller.store.upsert(current)
                    exchange_snapshot = refresh_snapshot()
                    local_position = self.controller.refresh_local_position_from_exchange(plan.account, regime_output.symbol, exchange_snapshot) or current
                    verification_position = self.controller.verify_position(plan.account, regime_output.symbol, exchange_snapshot)
                    self.controller.enable_route_if_flat(plan.account, regime_output.symbol)
                    reconcile_result = self.controller.reconcile_account_symbol(plan.account, regime_output.symbol, exchange_snapshot)
                else:
                    exchange_snapshot = current_snapshot
                    current = self.controller.refresh_local_position_from_exchange(plan.account, regime_output.symbol, exchange_snapshot) or current
                    if current.status.value in {'entry_submitted', 'entry_verifying', 'exit_submitted', 'exit_verifying'}:
                        current = self.controller.verify_position(plan.account, regime_output.symbol, exchange_snapshot) or current
                    reconcile_result = self.controller.reconcile_account_symbol(plan.account, regime_output.symbol, exchange_snapshot)
                    local_position = current
                    verification_position = current

        if reconcile_result is not None and not reconcile_result.policy.trade_enabled:
            trace.block_reason = reconcile_result.policy.reason
            trace.allow_reason = None
            if reconcile_result.policy.action not in trace.diagnostics:
                trace.diagnostics.append(reconcile_result.policy.action)

        route_state = None
        if plan.account is not None:
            route_state = asdict(self.controller.routes.get(plan.account, regime_output.symbol))

        return ExecutionCycleResult(
            regime_output=regime_output,
            plan=plan,
            receipt=receipt,
            local_position=local_position,
            verification_position=verification_position,
            reconcile_result=reconcile_result,
            decision_trace=trace,
            runtime_state=asdict(self.runtime_store.get()),
            route_state=route_state,
            live_positions=[asdict(position) for position in self.controller.store.list_positions()],
            router_composite=self.composite_simulator.snapshot(regime_output),
        )
