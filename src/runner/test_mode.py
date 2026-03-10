from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from src.config.settings import Settings
from src.exchange.okx_client import OkxClient, OkxClientRegistry
from src.execution.executor import DemoExecutor
from src.runner.live_trader import ensure_bucket, apply_state_patch, position_alignment_report
from src.runtime_guards import assert_single_okx_trading_daemon_context
from src.runtime_mode import set_mode
from src.storage.state import StateStore

ROOT = Path('/root/.openclaw/workspace/projects/okx-trading')
LOGS = ROOT / 'logs'
REPORTS = ROOT / 'reports' / 'changes'
REPORTS.mkdir(parents=True, exist_ok=True)
TEST_SUMMARY_PATH = REPORTS / 'latest-test-mode-summary.json'
TEST_DETAIL_PATH = REPORTS / 'latest-test-mode-detail.json'
NON_PROD_TEST_EXCLUDED = {'BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'SOL-USDT-SWAP'}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument('--strategy', default=None, choices=['breakout', 'pullback', 'meanrev'])
    p.add_argument('--symbols', default=None, help='Comma-separated test symbols; must exclude BTC/ETH/SOL')
    p.add_argument('--side', default='long', choices=['long', 'short'])
    p.add_argument('--entry-usdt', type=float, default=None)
    p.add_argument('--add-usdt', type=float, default=None)
    p.add_argument('--add-count', type=int, default=None)
    p.add_argument('--cycles', type=int, default=None)
    p.add_argument('--sleep-seconds', type=float, default=None)
    p.add_argument('--duration-minutes', type=int, default=None)
    p.add_argument('--arm-demo-submit', action='store_true')
    p.add_argument('--write-state', action='store_true')
    p.add_argument('--test-reverse-signal', action='store_true')
    return p.parse_args()


def append_step(run: dict, step: str, detail: str, venue_response: dict | None = None, extra: dict | None = None) -> None:
    row = {
        'step': step,
        'detail': detail,
        'venue_response': venue_response,
    }
    if extra:
        row.update(extra)
    run['steps'].append(row)


def opposite_side(side: str) -> str:
    return 'short' if side == 'long' else 'long'


def _require_test_symbols(symbols: list[str]) -> list[str]:
    cleaned = [item.strip() for item in symbols if item.strip()]
    if not cleaned:
        raise RuntimeError('test_mode requires at least one test symbol')
    bad = [symbol for symbol in cleaned if symbol in NON_PROD_TEST_EXCLUDED]
    if bad:
        raise RuntimeError(f'test_mode disallows production symbols: {bad}')
    return cleaned


def _run_single_symbol(
    *,
    snapshot: dict,
    store: StateStore,
    client,
    strategy: str,
    raw_symbol: str,
    side: str,
    entry_usdt: float,
    add_usdt: float,
    add_count: int,
    cycles: int,
    sleep_seconds: float,
    armed_demo_submit: bool,
    write_state: bool,
    test_reverse_signal: bool,
    settings: Settings,
) -> tuple[dict, dict]:
    executor = DemoExecutor(armed=armed_demo_submit and not settings.dry_run, client=client)
    exec_symbol = settings.execution_symbol(strategy, raw_symbol)
    test_key = f'test:{strategy}:{raw_symbol}'
    bucket_capital = settings.buffer_capital_usdt
    bucket = ensure_bucket(snapshot, test_key, f'test_{strategy}', exec_symbol, bucket_capital)
    bucket.update({
        'initial_capital_usdt': bucket_capital,
        'available_usdt': bucket_capital,
        'allocated_usdt': 0.0,
        'is_test_bucket': True,
        'backing_capital': 'buffer_capital_usdt',
    })
    snapshot = apply_state_patch(snapshot, {'buckets': {test_key: bucket}})

    positions = snapshot.get('positions', {}).get(test_key, []) or []
    open_positions = [p for p in positions if p.get('status') == 'open']
    if open_positions:
        raise RuntimeError(f'test_mode requires a flat local test bucket first: {test_key} has {len(open_positions)} open positions')

    live_before = client.current_live_position(exec_symbol)
    if live_before is not None:
        raise RuntimeError(
            'test_mode requires a flat exchange symbol first; buffer funding isolates accounting only, not exchange positions. '
            f'Current live position: {live_before}'
        )

    run = {
        'generated_at': datetime.now(UTC).isoformat(),
        'type': 'test_mode',
        'strategy': strategy,
        'symbol': raw_symbol,
        'execution_symbol': exec_symbol,
        'test_bucket_key': test_key,
        'side': side,
        'entry_usdt': entry_usdt,
        'add_usdt': add_usdt,
        'add_count': add_count,
        'cycles': cycles,
        'armed_demo_submit': bool(armed_demo_submit and not settings.dry_run),
        'backing_capital': 'buffer_capital_usdt',
        'buffer_capital_usdt': bucket_capital,
        'test_reverse_signal': test_reverse_signal,
        'note': 'Buffer capital isolates local accounting only. Do not run concurrently with formal trading on the same account/symbol.',
        'steps': [],
    }

    current_bar_id = int(datetime.now(UTC).timestamp() * 1000)
    for cycle in range(1, cycles + 1):
        positions = snapshot.get('positions', {}).get(test_key, []) or []
        bucket = snapshot.get('buckets', {}).get(test_key, bucket)
        first = executor.submit_entry_signal(
            position_key=test_key,
            symbol=exec_symbol,
            strategy=f'test_{strategy}',
            side=side,
            reason=f'test_mode_cycle_{cycle}_entry',
            bar_id=current_bar_id,
            order_size_usdt=entry_usdt,
            margin_required_usdt=entry_usdt,
            leverage=1,
            bucket=bucket,
            existing_positions=positions,
            current_open_amount=0.0,
        )
        snapshot = apply_state_patch(snapshot, first.state_patch)
        append_step(run, f'cycle_{cycle}:entry_1', first.detail, first.venue_response)
        if write_state:
            store.save(snapshot)
        time.sleep(sleep_seconds)
        current_bar_id += 1

        for add_index in range(1, add_count + 1):
            positions = snapshot.get('positions', {}).get(test_key, []) or []
            open_positions = [p for p in positions if p.get('status') == 'open']
            current_open_amount = sum(float(p.get('amount') or 0.0) for p in open_positions if p.get('side') == side)
            add = executor.submit_entry_signal(
                position_key=test_key,
                symbol=exec_symbol,
                strategy=f'test_{strategy}',
                side=side,
                reason=f'test_mode_cycle_{cycle}_add_{add_index}',
                bar_id=current_bar_id,
                order_size_usdt=add_usdt,
                margin_required_usdt=add_usdt,
                leverage=1,
                bucket=snapshot.get('buckets', {}).get(test_key, bucket),
                existing_positions=positions,
                current_open_amount=current_open_amount,
            )
            snapshot = apply_state_patch(snapshot, add.state_patch)
            append_step(run, f'cycle_{cycle}:add_{add_index}', add.detail, add.venue_response, {'current_open_amount_before': current_open_amount})
            if write_state:
                store.save(snapshot)
            time.sleep(sleep_seconds)
            current_bar_id += 1

        positions = snapshot.get('positions', {}).get(test_key, []) or []
        bucket = snapshot.get('buckets', {}).get(test_key, bucket)
        if test_reverse_signal:
            reverse_exit = executor.submit_exit_signal(
                position_key=test_key,
                symbol=exec_symbol,
                strategy=f'test_{strategy}',
                positions=positions,
                reason=f'test_mode_cycle_{cycle}_reverse_signal:{opposite_side(side)}|exit_all',
                bar_id=current_bar_id,
                bucket=bucket,
                exit_side=None,
            )
            snapshot = apply_state_patch(snapshot, reverse_exit.state_patch)
            append_step(run, f'cycle_{cycle}:reverse_signal_exit_all', reverse_exit.detail, reverse_exit.venue_response, {'reverse_signal': opposite_side(side)})
        else:
            exit_all = executor.submit_exit_signal(
                position_key=test_key,
                symbol=exec_symbol,
                strategy=f'test_{strategy}',
                positions=positions,
                reason=f'test_mode_cycle_{cycle}_exit_all',
                bar_id=current_bar_id,
                bucket=bucket,
                exit_side=None,
            )
            snapshot = apply_state_patch(snapshot, exit_all.state_patch)
            append_step(run, f'cycle_{cycle}:exit_all', exit_all.detail, exit_all.venue_response)
        if write_state:
            store.save(snapshot)
        time.sleep(sleep_seconds)
        current_bar_id += 1

    per_account_positions = {client.account_alias: client.exchange.fetch_positions([exec_symbol])}
    run['alignment'] = position_alignment_report(snapshot, per_account_positions)
    run['final_bucket'] = snapshot.get('buckets', {}).get(test_key)
    run['final_positions'] = snapshot.get('positions', {}).get(test_key, [])
    return snapshot, run


def _cleanup_test_state(snapshot: dict, strategy: str, symbols: list[str]) -> dict:
    updated = dict(snapshot)
    positions = dict(updated.get('positions', {}))
    buckets = dict(updated.get('buckets', {}))
    last_signals = dict(updated.get('last_signals', {}))
    for raw_symbol in symbols:
        test_key = f'test:{strategy}:{raw_symbol}'
        positions[test_key] = []
        bucket = dict(buckets.get(test_key, {}))
        if bucket:
            initial = float(bucket.get('initial_capital_usdt', bucket.get('available_usdt', 0.0)) or 0.0)
            bucket['available_usdt'] = initial
            bucket['allocated_usdt'] = 0.0
            bucket['locked'] = False
            bucket['lock_reason'] = None
            buckets[test_key] = bucket
        last_signals[test_key] = {'side': 'flat', 'reason': 'test_cleanup', 'bar_id': int(datetime.now(UTC).timestamp() * 1000)}
    updated['positions'] = positions
    updated['buckets'] = buckets
    updated['last_signals'] = last_signals
    updated['open_positions'] = 0
    return updated


def _current_daemon_pid() -> int | None:
    pidfile = LOGS / 'service' / 'daemon.pid'
    if not pidfile.exists():
        return None
    try:
        return int(pidfile.read_text().strip())
    except Exception:
        return None


def split_test_report(summary: dict) -> tuple[dict, dict]:
    detail = dict(summary)
    compact_runs = []
    for run in summary.get('runs', []):
        compact_run = dict(run)
        compact_run['step_count'] = len(run.get('steps', []))
        compact_run.pop('steps', None)
        compact_run['final_open_positions'] = [p for p in (run.get('final_positions') or []) if p.get('status') == 'open']
        compact_runs.append(compact_run)
    summary_view = dict(summary)
    summary_view['runs'] = compact_runs
    return summary_view, detail


def write_test_reports(summary: dict) -> None:
    summary_view, detail = split_test_report(summary)
    TEST_SUMMARY_PATH.write_text(json.dumps(summary_view, indent=2, default=str))
    TEST_DETAIL_PATH.write_text(json.dumps(detail, indent=2, default=str))
    (REPORTS / 'latest-test-mode.json').write_text(json.dumps(summary_view, indent=2, default=str))


def main() -> None:
    args = parse_args()
    assert_single_okx_trading_daemon_context(allow_current_run_daemon_pid=_current_daemon_pid())
    settings = Settings.load()
    settings.ensure_demo_only()

    strategy = args.strategy or settings.test_strategy
    symbols = _require_test_symbols(
        (args.symbols.split(',') if args.symbols else settings.test_symbols)
    )
    side = args.side
    entry_usdt = args.entry_usdt or settings.test_entry_usdt
    add_usdt = args.add_usdt or settings.test_add_usdt
    add_count = args.add_count if args.add_count is not None else settings.test_add_count
    cycles = args.cycles if args.cycles is not None else settings.test_cycles
    sleep_seconds = args.sleep_seconds if args.sleep_seconds is not None else settings.test_action_interval_seconds
    duration_minutes = args.duration_minutes if args.duration_minutes is not None else settings.test_duration_minutes
    armed_demo_submit = bool(args.arm_demo_submit and not settings.dry_run)
    write_state = bool(args.write_state)
    test_reverse_signal = bool(args.test_reverse_signal or settings.test_reverse_signal)

    registry = OkxClientRegistry(settings)
    test_account = settings.strategy_accounts[settings.test_account_alias]
    client = OkxClient(settings, test_account)
    store = StateStore(LOGS / 'state.json')
    snapshot = store.load()

    started_at = time.time()
    deadline = started_at + max(1, duration_minutes) * 60
    run_id = datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')
    summary = {
        'generated_at': datetime.now(UTC).isoformat(),
        'run_id': run_id,
        'type': 'test_mode_suite',
        'strategy': strategy,
        'test_account_alias': settings.test_account_alias,
        'test_account_label': test_account.label or test_account.alias,
        'symbols': symbols,
        'excluded_symbols': sorted(NON_PROD_TEST_EXCLUDED),
        'buffer_capital_usdt': settings.buffer_capital_usdt,
        'duration_minutes': duration_minutes,
        'entry_usdt': entry_usdt,
        'add_usdt': add_usdt,
        'add_count': add_count,
        'cycles_per_symbol': cycles,
        'sleep_seconds': sleep_seconds,
        'armed_demo_submit': armed_demo_submit,
        'write_state': write_state,
        'test_reverse_signal': test_reverse_signal,
        'runs': [],
        'pass': False,
        'checks': {},
        'error': None,
    }

    try:
        for raw_symbol in symbols:
            if time.time() >= deadline:
                break
            snapshot, run = _run_single_symbol(
                snapshot=snapshot,
                store=store,
                client=client,
                strategy=strategy,
                raw_symbol=raw_symbol,
                side=side,
                entry_usdt=entry_usdt,
                add_usdt=add_usdt,
                add_count=add_count,
                cycles=cycles,
                sleep_seconds=sleep_seconds,
                armed_demo_submit=armed_demo_submit,
                write_state=write_state,
                test_reverse_signal=test_reverse_signal,
                settings=settings,
            )
            summary['runs'].append(run)
            side = opposite_side(side)
            write_test_reports(summary)

        all_alignments = [bool(run.get('alignment', {}).get('ok')) for run in summary['runs']]
        all_final_open_positions_flat = all(
            not [p for p in (run.get('final_positions') or []) if p.get('status') == 'open']
            for run in summary['runs']
        )
        summary['pass'] = bool(summary['runs']) and all(all_alignments) and all_final_open_positions_flat
        summary['checks'] = {
            'all_alignments_ok': all(all_alignments) if all_alignments else False,
            'all_final_open_positions_flat': all_final_open_positions_flat,
            'run_count': len(summary['runs']),
            'elapsed_seconds': round(time.time() - started_at, 3),
            'deadline_seconds': max(1, duration_minutes) * 60,
            'completed_suite': True,
        }
        return_code = 0
    except Exception as exc:
        snapshot = _cleanup_test_state(snapshot, strategy, symbols)
        store.save(snapshot)
        summary['error'] = {'type': type(exc).__name__, 'message': str(exc)}
        summary['checks'] = {
            'run_count': len(summary['runs']),
            'elapsed_seconds': round(time.time() - started_at, 3),
            'deadline_seconds': max(1, duration_minutes) * 60,
            'completed_suite': False,
            'cleaned_local_test_state': True,
        }
        return_code = 1
    finally:
        write_test_reports(summary)
        print(json.dumps(summary, indent=2, default=str))
        set_mode('develop', reason='test_runner_finalize', actor='test_mode')

    raise SystemExit(return_code)


if __name__ == '__main__':
    main()
