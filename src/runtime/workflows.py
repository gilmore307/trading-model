from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import UTC, datetime
from pathlib import Path
import json

from src.config.settings import Settings
from src.exchange.okx_client import OkxClient
from src.review.framework import build_weekly_window
from src.review.export import export_report_artifacts
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
    def run_review(self) -> WorkflowStepResult:
        return WorkflowStepResult(name='run_review', ok=True, detail='stub')

    def run_test_workflow(self) -> WorkflowStepResult:
        return WorkflowStepResult(name='run_test_workflow', ok=True, detail='stub')

    def flatten_all_positions(self) -> WorkflowStepResult:
        return WorkflowStepResult(name='flatten_all_positions', ok=True, detail='stub')

    def verify_flat(self) -> WorkflowStepResult:
        return WorkflowStepResult(name='verify_flat', ok=True, detail='stub')

    def convert_non_usdt_assets(self) -> WorkflowStepResult:
        return WorkflowStepResult(name='convert_non_usdt_assets', ok=True, detail='stub')

    def verify_startup_capital(self) -> WorkflowStepResult:
        return WorkflowStepResult(name='verify_startup_capital', ok=True, detail='stub')

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

    def _unique_accounts(self) -> list[tuple[str, str]]:
        seen: set[str] = set()
        accounts: list[tuple[str, str]] = []
        for strategy in self.settings.strategies:
            account = self.settings.account_for_strategy(strategy)
            if account.alias in seen:
                continue
            seen.add(account.alias)
            accounts.append((strategy, account.alias))
        return accounts

    def run_review(self) -> WorkflowStepResult:
        try:
            now = datetime.now(UTC)
            window = build_weekly_window(now)
            exported = export_report_artifacts(
                window,
                history_path=str(OUT_DIR / 'execution-cycles.jsonl'),
                out_dir=None,
                generated_at=now,
            )
            return WorkflowStepResult(
                name='run_review',
                ok=True,
                detail=f"json={exported.get('json_path')} markdown={exported.get('markdown_path')}",
            )
        except Exception as exc:
            return WorkflowStepResult(name='run_review', ok=False, detail=str(exc))

    def run_test_workflow(self) -> WorkflowStepResult:
        try:
            self.settings.ensure_demo_only()
            symbol = self.settings.test_symbols[0]
            account_alias = self.settings.test_account_alias
            account = self.settings.strategy_accounts[account_alias]
            client = OkxClient(self.settings, account)
            total_actions: list[str] = []
            for cycle in range(self.settings.test_cycles):
                side = 'long'
                if self.settings.test_reverse_signal and cycle % 2 == 1:
                    side = 'short'
                entry = client.create_entry_order(symbol, side, float(self.settings.test_entry_usdt))
                total_actions.append(f'cycle={cycle + 1}:entry:{side}:{entry.get("order_id") or "submitted"}')
                current_open_amount = float(entry.get('live_contracts') or entry.get('amount') or 0.0)
                for add_idx in range(self.settings.test_add_count):
                    add = client.create_entry_order(symbol, side, float(self.settings.test_add_usdt), current_open_amount=current_open_amount)
                    current_open_amount = float(add.get('live_contracts') or (current_open_amount + float(add.get('amount') or 0.0)))
                    total_actions.append(f'cycle={cycle + 1}:add={add_idx + 1}:{side}:{add.get("order_id") or "submitted"}')
                live = client.current_live_position(symbol)
                if live and float(live.get('contracts') or 0.0) > 0.0 and live.get('side'):
                    exit_result = client.create_exit_order(symbol, str(live.get('side')), float(live.get('contracts') or 0.0))
                    total_actions.append(f'cycle={cycle + 1}:exit:{exit_result.get("order_id") or "submitted"}')
                else:
                    total_actions.append(f'cycle={cycle + 1}:exit_skipped:no_live_position')
            return WorkflowStepResult(name='run_test_workflow', ok=True, detail='; '.join(total_actions) if total_actions else 'no_test_actions')
        except Exception as exc:
            return WorkflowStepResult(name='run_test_workflow', ok=False, detail=str(exc))

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

    def convert_non_usdt_assets(self) -> WorkflowStepResult:
        actions = []
        errors = []
        converted_any = False
        for strategy, account in self._unique_accounts():
            client = OkxClient(self.settings, self.settings.account_for_strategy(strategy))
            try:
                assets = client.non_usdt_assets()
            except Exception as exc:
                errors.append(f'{account}:balance:{exc}')
                continue
            if not assets:
                actions.append(f'{account}:already_usdt')
                continue
            for row in assets:
                asset = str(row.get('asset') or '').upper()
                amount = float(row.get('amount') or 0.0)
                if amount <= 0:
                    continue
                try:
                    result = client.convert_asset_to_usdt(asset, amount)
                    converted_any = converted_any or not bool(result.get('skipped'))
                    status = result.get('reason') if result.get('skipped') else (result.get('order_id') or 'submitted')
                    actions.append(f'{account}:{asset}:{status}')
                except Exception as exc:
                    errors.append(f'{account}:{asset}:{exc}')
        detail_rows = actions if actions else ['no_convertible_assets']
        if converted_any and not actions:
            detail_rows = ['converted']
        return WorkflowStepResult(
            name='convert_non_usdt_assets',
            ok=not errors,
            detail='; '.join(detail_rows) + ('' if not errors else ' | errors=' + '; '.join(errors)),
        )

    def verify_startup_capital(self) -> WorkflowStepResult:
        threshold = float(self.settings.buffer_capital_usdt or 0.0)
        failures = []
        ready = []
        for strategy, account in self._unique_accounts():
            client = OkxClient(self.settings, self.settings.account_for_strategy(strategy))
            try:
                summary = client.account_balance_summary()
            except Exception as exc:
                failures.append(f'{account}:balance:{exc}')
                continue
            usdt_available = float(summary.get('usdt_available') or 0.0)
            non_usdt = [row.get('asset') for row in (summary.get('assets') or []) if str(row.get('asset') or '').upper() != 'USDT' and float(row.get('available') or row.get('equity') or 0.0) > 0.0]
            if usdt_available < threshold:
                failures.append(f'{account}:usdt_available={usdt_available}<buffer={threshold}')
                continue
            if non_usdt:
                failures.append(f'{account}:residual_non_usdt={"/".join(sorted(str(x) for x in non_usdt))}')
                continue
            ready.append(f'{account}:usdt_available={usdt_available}')
        return WorkflowStepResult(
            name='verify_startup_capital',
            ok=not failures,
            detail='; '.join(ready if ready else ['not_ready']) + ('' if not failures else ' | failures=' + '; '.join(failures)),
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
        if mode not in {RuntimeMode.REVIEW, RuntimeMode.TEST, RuntimeMode.CALIBRATE, RuntimeMode.RESET}:
            raise ValueError(f'workflow mode not supported: {mode}')

        started_mode = self.runtime_store.get().mode
        destructive = mode == RuntimeMode.RESET
        self.runtime_store.set_mode(mode, reason='workflow_start')

        if mode == RuntimeMode.REVIEW:
            steps = [
                self.hooks.run_review(),
            ]
        elif mode == RuntimeMode.TEST:
            steps = [
                self.hooks.run_test_workflow(),
            ]
        else:
            steps = [
                self.hooks.flatten_all_positions(),
                self.hooks.verify_flat(),
                self.hooks.convert_non_usdt_assets(),
                self.hooks.verify_startup_capital(),
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
