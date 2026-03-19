from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import UTC, datetime
from pathlib import Path
import json
import time

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
TEST_REPORT_JSON = OUT_DIR / 'latest-test-summary.json'
TEST_REPORT_MD = OUT_DIR / 'latest-test-summary.md'
CONVERSION_SETTLE_SECONDS = 5.0
CONVERSION_VERIFY_RETRIES = 3
DUST_ASSET_THRESHOLD = 0.001
RUNTIME_HISTORY_FILES = [
    OUT_DIR / 'execution-cycles.jsonl',
    OUT_DIR / 'execution-anomalies.jsonl',
    OUT_DIR / 'regime-local-history.jsonl',
    OUT_DIR / 'strategy-activity-history.jsonl',
    OUT_DIR / 'latest-execution-cycle.json',
    TEST_REPORT_JSON,
    TEST_REPORT_MD,
]
REPORT_DIR = Path('/root/.openclaw/workspace/projects/crypto-trading/reports/trade-review')


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

    def clear_analysis_history(self) -> WorkflowStepResult:
        return WorkflowStepResult(name='clear_analysis_history', ok=True, detail='stub')

    def flatten_all_positions(self) -> WorkflowStepResult:
        return WorkflowStepResult(name='flatten_all_positions', ok=True, detail='stub')

    def verify_flat(self) -> WorkflowStepResult:
        return WorkflowStepResult(name='verify_flat', ok=True, detail='stub')

    def flatten_all_margin_positions(self) -> WorkflowStepResult:
        return WorkflowStepResult(name='flatten_all_margin_positions', ok=True, detail='stub')

    def verify_margin_flat(self) -> WorkflowStepResult:
        return WorkflowStepResult(name='verify_margin_flat', ok=True, detail='stub')

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
            cycle_rows: list[dict[str, object]] = []
            entry_count = 0
            add_count = 0
            exit_count = 0
            for cycle in range(self.settings.test_cycles):
                side = 'long'
                if self.settings.test_reverse_signal and cycle % 2 == 1:
                    side = 'short'
                cycle_row: dict[str, object] = {'cycle': cycle + 1, 'side': side, 'entry': None, 'adds': [], 'exit': None}
                entry = client.create_entry_order(symbol, side, float(self.settings.test_entry_usdt))
                entry_count += 1
                cycle_row['entry'] = {'order_id': entry.get('order_id'), 'verified_entry': entry.get('verified_entry'), 'live_contracts': entry.get('live_contracts')}
                total_actions.append(f'cycle={cycle + 1}:entry:{side}:{entry.get("order_id") or "submitted"}')
                current_open_amount = float(entry.get('live_contracts') or entry.get('amount') or 0.0)
                for add_idx in range(self.settings.test_add_count):
                    add = client.create_entry_order(symbol, side, float(self.settings.test_add_usdt), current_open_amount=current_open_amount)
                    add_count += 1
                    current_open_amount = float(add.get('live_contracts') or (current_open_amount + float(add.get('amount') or 0.0)))
                    adds = list(cycle_row.get('adds') or [])
                    adds.append({'order_id': add.get('order_id'), 'verified_entry': add.get('verified_entry'), 'live_contracts': add.get('live_contracts')})
                    cycle_row['adds'] = adds
                    total_actions.append(f'cycle={cycle + 1}:add={add_idx + 1}:{side}:{add.get("order_id") or "submitted"}')
                live = client.current_live_position(symbol)
                if live and float(live.get('contracts') or 0.0) > 0.0 and live.get('side'):
                    exit_result = client.create_exit_order(symbol, str(live.get('side')), float(live.get('contracts') or 0.0))
                    exit_count += 1
                    cycle_row['exit'] = {'order_id': exit_result.get('order_id'), 'verified_flat': exit_result.get('verified_flat'), 'remaining_contracts': exit_result.get('remaining_contracts')}
                    total_actions.append(f'cycle={cycle + 1}:exit:{exit_result.get("order_id") or "submitted"}')
                else:
                    cycle_row['exit'] = {'skipped': True, 'reason': 'no_live_position'}
                    total_actions.append(f'cycle={cycle + 1}:exit_skipped:no_live_position')
                cycle_rows.append(cycle_row)
            summary = {
                'generated_at': datetime.now(UTC).isoformat(),
                'mode': 'test',
                'okx_demo': self.settings.okx_demo,
                'account_alias': account_alias,
                'symbol': symbol,
                'test_cycles': self.settings.test_cycles,
                'test_add_count': self.settings.test_add_count,
                'entry_count': entry_count,
                'add_count': add_count,
                'exit_count': exit_count,
                'cycles': cycle_rows,
            }
            TEST_REPORT_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
            markdown_lines = [
                '# Test Mode Summary',
                '',
                f'- Generated at: {summary["generated_at"]}',
                f'- Account: {account_alias}',
                f'- Symbol: {symbol}',
                f'- Cycles: {self.settings.test_cycles}',
                f'- Entries: {entry_count}',
                f'- Adds: {add_count}',
                f'- Exits: {exit_count}',
                '',
                '## Cycle Details',
            ]
            for row in cycle_rows:
                markdown_lines.append(f"- cycle {row['cycle']} side={row['side']} entry={((row.get('entry') or {}).get('order_id') if isinstance(row.get('entry'), dict) else None)} exit={((row.get('exit') or {}).get('order_id') if isinstance(row.get('exit'), dict) else ('skipped' if isinstance(row.get('exit'), dict) and row.get('exit', {}).get('skipped') else None))}")
            TEST_REPORT_MD.write_text('\n'.join(markdown_lines).strip() + '\n', encoding='utf-8')
            return WorkflowStepResult(name='run_test_workflow', ok=True, detail=f"summary_json={TEST_REPORT_JSON} summary_md={TEST_REPORT_MD} | " + ('; '.join(total_actions) if total_actions else 'no_test_actions'))
        except Exception as exc:
            return WorkflowStepResult(name='run_test_workflow', ok=False, detail=str(exc))

    def clear_analysis_history(self) -> WorkflowStepResult:
        removed = []
        missing = []
        errors = []
        for path in RUNTIME_HISTORY_FILES:
            try:
                if path.exists():
                    path.unlink()
                    removed.append(str(path.name))
                else:
                    missing.append(str(path.name))
            except Exception as exc:
                errors.append(f'{path.name}:{exc}')
        try:
            if REPORT_DIR.exists():
                for child in REPORT_DIR.iterdir():
                    if child.is_file():
                        child.unlink()
                        removed.append(f'reports/{child.name}')
            else:
                missing.append('reports/trade-review')
        except Exception as exc:
            errors.append(f'reports/trade-review:{exc}')
        detail_parts = []
        if removed:
            detail_parts.append('removed=' + '; '.join(removed))
        if missing:
            detail_parts.append('missing=' + '; '.join(missing))
        return WorkflowStepResult(
            name='clear_analysis_history',
            ok=not errors,
            detail=' | '.join(detail_parts) + ('' if not errors else ' | errors=' + '; '.join(errors)),
        )

    def flatten_all_positions(self) -> WorkflowStepResult:
        actions = []
        errors = []
        for strategy, account in self._unique_accounts():
            client = OkxClient(self.settings, self.settings.account_for_strategy(strategy))
            try:
                positions = client.all_live_positions()
            except Exception as exc:
                errors.append(f'{account}:positions:{exc}')
                continue
            if not positions:
                actions.append(f'{account}:no_live_positions')
                continue
            for live in positions:
                symbol = str(live.get('symbol') or '')
                side = live.get('side')
                amount = float(live.get('contracts') or 0.0)
                if not symbol or not side or amount <= 0:
                    continue
                try:
                    result = client.create_exit_order(symbol, str(side), amount)
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
        for strategy, account in self._unique_accounts():
            client = OkxClient(self.settings, self.settings.account_for_strategy(strategy))
            try:
                positions = client.all_live_positions()
            except Exception as exc:
                non_flat.append(f'{account}:positions_error:{exc}')
                continue
            for live in positions:
                if float(live.get('contracts') or 0.0) > 0.0:
                    non_flat.append(f'{account}:{live.get("symbol")}:{live.get("side")}:{live.get("contracts")}')
        return WorkflowStepResult(
            name='verify_flat',
            ok=not non_flat,
            detail='all_flat' if not non_flat else 'non_flat=' + '; '.join(non_flat),
        )

    def flatten_all_margin_positions(self) -> WorkflowStepResult:
        actions = []
        errors = []
        for strategy, account in self._unique_accounts():
            client = OkxClient(self.settings, self.settings.account_for_strategy(strategy))
            try:
                positions = client.all_live_margin_positions()
            except Exception as exc:
                errors.append(f'{account}:margin_positions:{exc}')
                continue
            if not positions:
                actions.append(f'{account}:no_margin_positions')
                continue
            for row in positions:
                try:
                    result = client.close_margin_position(row)
                    status = result.get('reason') if result.get('skipped') else (result.get('order_id') or 'submitted')
                    actions.append(f'{account}:{row.get("symbol")}:{status}')
                except Exception as exc:
                    errors.append(f'{account}:{row.get("symbol")}:{exc}')
        return WorkflowStepResult(
            name='flatten_all_margin_positions',
            ok=not errors,
            detail='; '.join(actions if actions else ['no_margin_positions']) + ('' if not errors else ' | errors=' + '; '.join(errors)),
        )

    def verify_margin_flat(self) -> WorkflowStepResult:
        remains = []
        for strategy, account in self._unique_accounts():
            client = OkxClient(self.settings, self.settings.account_for_strategy(strategy))
            try:
                positions = client.all_live_margin_positions()
            except Exception as exc:
                remains.append(f'{account}:margin_positions_error:{exc}')
                continue
            for row in positions:
                pos = float(row.get('pos') or 0.0)
                liab = float(row.get('liability') or 0.0)
                interest = float(row.get('interest') or 0.0)
                if pos > 0 or liab > 0 or interest > 0:
                    remains.append(f'{account}:{row.get("symbol")}:pos={pos}:liab={liab}:interest={interest}:posCcy={row.get("pos_ccy")}:mgnMode={row.get("margin_mode")}')
        return WorkflowStepResult(
            name='verify_margin_flat',
            ok=not remains,
            detail='all_margin_flat' if not remains else 'margin_remaining=' + '; '.join(remains),
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
                if amount <= DUST_ASSET_THRESHOLD:
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
        last_failures = []
        ready = []
        for attempt in range(CONVERSION_VERIFY_RETRIES):
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
                margin_exposures = client.margin_exposure_summary()
                non_usdt = [
                    f"{row.get('asset')}(avail={row.get('available')},eq={row.get('equity')},liab={row.get('liability')},cross={row.get('cross_liability')},iso={row.get('isolated_liability')},lev={row.get('notional_leverage')})"
                    for row in (summary.get('assets') or [])
                    if str(row.get('asset') or '').upper() != 'USDT' and max(float(row.get('available') or 0.0), float(row.get('equity') or 0.0)) > DUST_ASSET_THRESHOLD
                ]
                if usdt_available < threshold:
                    failures.append(f'{account}:usdt_available={usdt_available}<buffer={threshold}')
                    continue
                if margin_exposures:
                    failures.append('margin_exposure=' + ';'.join(
                        f"{account}:{row.get('asset')}:liab={row.get('liability')}:cross={row.get('cross_liability')}:iso={row.get('isolated_liability')}:lev={row.get('notional_leverage')}:mgn={row.get('margin_ratio')}"
                        for row in margin_exposures
                    ))
                    continue
                if non_usdt:
                    failures.append(f'{account}:residual_non_usdt=' + '|'.join(sorted(str(x) for x in non_usdt)))
                    continue
                ready.append(f'{account}:usdt_available={usdt_available}')
            if not failures:
                return WorkflowStepResult(
                    name='verify_startup_capital',
                    ok=True,
                    detail='; '.join(ready if ready else ['ready']),
                )
            last_failures = failures
            if attempt < CONVERSION_VERIFY_RETRIES - 1:
                time.sleep(CONVERSION_SETTLE_SECONDS)
        return WorkflowStepResult(
            name='verify_startup_capital',
            ok=False,
            detail='; '.join(ready if ready else ['not_ready']) + ' | failures=' + '; '.join(last_failures),
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
                self.hooks.flatten_all_margin_positions(),
                self.hooks.verify_margin_flat(),
                self.hooks.convert_non_usdt_assets(),
                self.hooks.verify_startup_capital(),
                self.hooks.reset_bucket_state(destructive=destructive),
            ]
            if destructive:
                steps.append(self.hooks.clear_analysis_history())

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
