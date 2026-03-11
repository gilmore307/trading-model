from __future__ import annotations

from dataclasses import dataclass

from src.config.settings import Settings
from src.execution.adapters import DryRunExecutionAdapter, ExecutionAdapter, ExecutionReceipt
from src.execution.controller import RouteController, RouteControlResult
from src.execution.exchange_snapshot import ExchangeSnapshotProvider
from src.reconcile.alignment import ExchangePositionSnapshot
from src.runners.regime_runner import BtcRegimeRunner, RegimeRunnerOutput
from src.runtime.mode import RuntimeMode
from src.runtime.mode_policy import policy_for_mode
from src.runtime.store import RuntimeStore
from src.state.live_position import LivePosition, LivePositionStatus
from src.strategies.executors import ExecutionPlan, executor_for


@dataclass(slots=True)
class ExecutionCycleResult:
    regime_output: RegimeRunnerOutput
    plan: ExecutionPlan
    receipt: ExecutionReceipt | None
    local_position: LivePosition | None
    verification_position: LivePosition | None
    reconcile_result: RouteControlResult | None


class ExecutionPipeline:
    """Skeleton execution pipeline.

    Phase 1 scope:
    - run regime runner
    - derive a plan
    - send state transitions through RouteController
    - verify/reconcile against a provided exchange snapshot

    This intentionally stops short of real order placement.
    """

    def __init__(self, regime_runner: BtcRegimeRunner | None = None, controller: RouteController | None = None, snapshot_provider: ExchangeSnapshotProvider | None = None, adapter: ExecutionAdapter | None = None, settings: Settings | None = None, runtime_store: RuntimeStore | None = None):
        self.settings = settings or Settings.load()
        self.regime_runner = regime_runner or BtcRegimeRunner(self.settings)
        self.controller = controller or RouteController()
        self.snapshot_provider = snapshot_provider or ExchangeSnapshotProvider(self.settings)
        self.adapter = adapter or DryRunExecutionAdapter()
        self.runtime_store = runtime_store or RuntimeStore()

    def build_plan(self, output: RegimeRunnerOutput) -> ExecutionPlan:
        return executor_for(output).build_plan(output)

    def run_cycle(self, exchange_snapshot: ExchangePositionSnapshot | None = None) -> ExecutionCycleResult:
        mode = self.runtime_store.get().mode
        mode_policy = policy_for_mode(mode)
        regime_output = self.regime_runner.run_once()
        if not mode_policy.allow_normal_routing:
            plan = ExecutionPlan(regime=regime_output.final_decision['primary'], account=None, action='hold', reason=f'mode_blocked:{mode.value}')
        else:
            plan = self.build_plan(regime_output)
        if plan.account is not None and not self.controller.routes.is_enabled(plan.account, regime_output.symbol):
            plan = ExecutionPlan(regime=plan.regime, account=plan.account, action='hold', reason=self.controller.routes.get(plan.account, regime_output.symbol).frozen_reason or 'route_frozen')
        if exchange_snapshot is None and plan.account is not None:
            exchange_snapshot = self.snapshot_provider.fetch_position(plan.account, regime_output.symbol)
        if mode_policy.force_dry_run:
            self.adapter = DryRunExecutionAdapter()
        receipt = None
        local_position = None
        verification_position = None
        reconcile_result = None

        if plan.account is not None and plan.action == 'enter' and plan.side is not None and plan.size is not None:
            receipt = self.adapter.submit_entry(account=plan.account, symbol=regime_output.symbol, side=plan.side, size=plan.size, reason=plan.reason or 'entry')
            local_position = self.controller.submit_entry(plan.account, regime_output.symbol, plan.regime, plan.side, plan.size, entry_order_id=receipt.order_id)
            verification_position = self.controller.verify_position(plan.account, regime_output.symbol, exchange_snapshot)
            reconcile_result = self.controller.reconcile_account_symbol(plan.account, regime_output.symbol, exchange_snapshot)
        elif plan.account is not None and plan.action == 'exit':
            receipt = self.adapter.submit_exit(account=plan.account, symbol=regime_output.symbol, reason=plan.reason or 'exit')
            local_position = self.controller.submit_exit(plan.account, regime_output.symbol, exit_order_id=receipt.order_id)
            verification_position = self.controller.verify_position(plan.account, regime_output.symbol, exchange_snapshot)
            reconcile_result = self.controller.reconcile_account_symbol(plan.account, regime_output.symbol, exchange_snapshot)
        elif plan.account is not None and plan.action == 'arm':
            current = self.controller.store.get(plan.account, regime_output.symbol)
            if current is not None:
                reconcile_result = self.controller.reconcile_account_symbol(plan.account, regime_output.symbol, exchange_snapshot)
                local_position = current
                verification_position = current
        elif plan.account is not None:
            current = self.controller.store.get(plan.account, regime_output.symbol)
            if current is not None:
                reconcile_result = self.controller.reconcile_account_symbol(plan.account, regime_output.symbol, exchange_snapshot)
                local_position = current
                verification_position = current

        return ExecutionCycleResult(
            regime_output=regime_output,
            plan=plan,
            receipt=receipt,
            local_position=local_position,
            verification_position=verification_position,
            reconcile_result=reconcile_result,
        )
