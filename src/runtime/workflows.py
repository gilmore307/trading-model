from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import UTC, datetime
from pathlib import Path
import json

from src.config.settings import Settings
from src.exchange.okx_client import OkxClient
from src.runtime.bucket_state import BucketStateStore
from src.runtime.mode import RuntimeMode
from src.runtime.store import RuntimeStore
from src.runtime.workflow import next_mode_after


OUT_DIR = Path('/root/.openclaw/workspace/projects/crypto-trading/logs/runtime')
OUT_DIR.mkdir(parents=True, exist_ok=True)
WORKFLOW_LOG = OUT_DIR / 'workflow-events.jsonl'


@dataclass(slots=True)
class WorkflowStepResult:
    name: str
    ok: bool
    detail: str | None = None


@dataclass(slots=True)
class WorkflowRunResult:
    workflow: str
    started_mode: str
    ended_mode: str
    destructive: bool
    steps: list[WorkflowStepResult]
    observed_at: datetime


class WorkflowHooks:
    def flatten_all_positions(self) -> WorkflowStepResult:
        return WorkflowStepResult(name='flatten_all_positions', ok=True, detail='stub')

    def verify_flat(self) -> WorkflowStepResult:
        return WorkflowStepResult(name='verify_flat', ok=True, detail='stub')

    def reset_bucket_state(self, destructive: bool) -> WorkflowStepResult:
        return WorkflowStepResult(name='reset_bucket_state', ok=True, detail=f'destructive={destructive}')


class OkxWorkflowHooks(WorkflowHooks):
    def __init__(self, settings: Settings, bucket_store: BucketStateStore | None = None):
        self.settings = settings
        self.bucket_store = bucket_store or BucketStateStore()

    def _account_symbol_pairs(self) -> list[tuple[str, str, str]]:
        pairs: list[tuple[str, str, str]] = []
        for strategy in self.settings.strategies:
            account = self.settings.account_for_strategy(strategy).alias
            for symbol in self.settings.symbols:
                pairs.append((strategy, account, symbol))
        return pairs

    def flatten_all_positions(self) -> WorkflowStepResult:
        actions = []
        errors = []
        for strategy, account, symbol in self._account_symbol_pairs():
            client = OkxClient(self.settings, self.settings.account_for_strategy(strategy))
            live = client.current_live_position(self.settings.execution_symbol(strategy, symbol))
            if not live:
                continue
            side = live.get('side')
            amount = float(live.get('contracts') or 0.0)
            if not side or amount <= 0:
                continue
            try:
                result = client.create_exit_order(self.settings.execution_symbol(strategy, symbol), side, amount)
                actions.append(f'{account}:{symbol}:{result.get("order_id") or "submitted"}')
            except Exception as exc:
                errors.append(f'{account}:{symbol}:{exc}')
        return WorkflowStepResult(
            name='flatten_all_positions',
            ok=not errors,
            detail='; '.join(actions if actions else ['no_live_positions']) + ('' if not errors else ' | errors=' + '; '.join(errors)),
        )

    def verify_flat(self) -> WorkflowStepResult:
        non_flat = []
        for strategy, account, symbol in self._account_symbol_pairs():
            client = OkxClient(self.settings, self.settings.account_for_strategy(strategy))
            live = client.current_live_position(self.settings.execution_symbol(strategy, symbol))
            if live and float(live.get('contracts') or 0.0) > 0.0:
                non_flat.append(f'{account}:{symbol}:{live.get("side")}:{live.get("contracts")}')
        return WorkflowStepResult(
            name='verify_flat',
            ok=not non_flat,
            detail='all_flat' if not non_flat else 'non_flat=' + '; '.join(non_flat),
        )

    def reset_bucket_state(self, destructive: bool) -> WorkflowStepResult:
        reset = []
        for strategy, account, symbol in self._account_symbol_pairs():
            state = self.bucket_store.reset_bucket(account, symbol, self.settings.bucket_initial_capital_usdt)
            reset.append(f'{state.account}:{state.symbol}:{state.capital_usdt}')
        return WorkflowStepResult(
            name='reset_bucket_state',
            ok=True,
            detail=('destructive=' + str(destructive) + ' | ' + '; '.join(reset)) if reset else f'destructive={destructive}',
        )


class RuntimeWorkflowRunner:
    def __init__(self, runtime_store: RuntimeStore | None = None, hooks: WorkflowHooks | None = None):
        self.runtime_store = runtime_store or RuntimeStore()
        self.hooks = hooks or WorkflowHooks()

    def _log(self, result: WorkflowRunResult) -> None:
        with WORKFLOW_LOG.open('a', encoding='utf-8') as f:
            f.write(json.dumps(asdict(result), default=str, ensure_ascii=False) + '\n')

    def run(self, mode: RuntimeMode) -> WorkflowRunResult:
        if mode not in {RuntimeMode.CALIBRATE, RuntimeMode.RESET}:
            raise ValueError(f'workflow mode not supported: {mode}')

        started_mode = self.runtime_store.get().mode
        destructive = mode == RuntimeMode.RESET
        self.runtime_store.set_mode(mode, reason='workflow_start')

        steps = [
            self.hooks.flatten_all_positions(),
            self.hooks.verify_flat(),
            self.hooks.reset_bucket_state(destructive=destructive),
        ]

        transition = next_mode_after(mode)
        ended = mode
        if transition is not None and all(step.ok for step in steps):
            ended = transition.to_mode
            self.runtime_store.set_mode(ended, reason=transition.reason)

        result = WorkflowRunResult(
            workflow=mode.value,
            started_mode=started_mode.value,
            ended_mode=ended.value,
            destructive=destructive,
            steps=steps,
            observed_at=datetime.now(UTC),
        )
        self._log(result)
        return result
