from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from src.config.settings import Settings
from src.exchange.okx_client import OkxClientRegistry
from src.execution.executor import DemoExecutor
from src.runner.live_trader import ensure_bucket, apply_state_patch, position_alignment_report
from src.storage.state import StateStore

ROOT = Path('/root/.openclaw/workspace/projects/okx-trading')
LOGS = ROOT / 'logs'
REPORTS = ROOT / 'reports' / 'changes'
REPORTS.mkdir(parents=True, exist_ok=True)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument('--strategy', required=True, choices=['breakout', 'pullback', 'meanrev'])
    p.add_argument('--symbol', required=True)
    p.add_argument('--side', required=True, choices=['long', 'short'])
    p.add_argument('--entry-usdt', type=float, default=100.0)
    p.add_argument('--add-usdt', type=float, default=100.0)
    p.add_argument('--add-count', type=int, default=2)
    p.add_argument('--cycles', type=int, default=1)
    p.add_argument('--sleep-seconds', type=float, default=2.0)
    p.add_argument('--arm-demo-submit', action='store_true')
    p.add_argument('--write-state', action='store_true')
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


def main() -> None:
    args = parse_args()
    settings = Settings.load()
    settings.ensure_demo_only()

    client = OkxClientRegistry(settings).for_strategy(args.strategy)
    executor = DemoExecutor(armed=args.arm_demo_submit and not settings.dry_run, client=client)
    store = StateStore(LOGS / 'state.json')
    snapshot = store.load()

    exec_symbol = settings.execution_symbol(args.strategy, args.symbol)
    test_key = f'test:{args.strategy}:{args.symbol}'
    bucket = ensure_bucket(snapshot, test_key, f'test_{args.strategy}', exec_symbol, settings.buffer_capital_usdt)
    bucket.update({
        'initial_capital_usdt': settings.buffer_capital_usdt,
        'available_usdt': settings.buffer_capital_usdt,
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

    now_bar_id = int(datetime.now(UTC).timestamp() * 1000)
    run = {
        'generated_at': datetime.now(UTC).isoformat(),
        'type': 'test_mode',
        'strategy': args.strategy,
        'symbol': args.symbol,
        'execution_symbol': exec_symbol,
        'test_bucket_key': test_key,
        'side': args.side,
        'entry_usdt': args.entry_usdt,
        'add_usdt': args.add_usdt,
        'add_count': args.add_count,
        'cycles': args.cycles,
        'armed_demo_submit': bool(args.arm_demo_submit and not settings.dry_run),
        'backing_capital': 'buffer_capital_usdt',
        'buffer_capital_usdt': settings.buffer_capital_usdt,
        'note': 'Buffer capital isolates local accounting only. Do not run concurrently with formal trading on the same account/symbol.',
        'steps': [],
    }

    current_bar_id = now_bar_id
    for cycle in range(1, args.cycles + 1):
        positions = snapshot.get('positions', {}).get(test_key, []) or []
        bucket = snapshot.get('buckets', {}).get(test_key, bucket)
        first = executor.submit_entry_signal(
            position_key=test_key,
            symbol=exec_symbol,
            strategy=f'test_{args.strategy}',
            side=args.side,
            reason=f'test_mode_cycle_{cycle}_entry',
            bar_id=current_bar_id,
            order_size_usdt=args.entry_usdt,
            margin_required_usdt=args.entry_usdt,
            leverage=1,
            bucket=bucket,
            existing_positions=positions,
            current_open_amount=0.0,
        )
        snapshot = apply_state_patch(snapshot, first.state_patch)
        append_step(run, f'cycle_{cycle}:entry_1', first.detail, first.venue_response)
        time.sleep(args.sleep_seconds)
        current_bar_id += 1

        for add_index in range(1, args.add_count + 1):
            positions = snapshot.get('positions', {}).get(test_key, []) or []
            open_positions = [p for p in positions if p.get('status') == 'open']
            current_open_amount = sum(float(p.get('amount') or 0.0) for p in open_positions if p.get('side') == args.side)
            add = executor.submit_entry_signal(
                position_key=test_key,
                symbol=exec_symbol,
                strategy=f'test_{args.strategy}',
                side=args.side,
                reason=f'test_mode_cycle_{cycle}_add_{add_index}',
                bar_id=current_bar_id,
                order_size_usdt=args.add_usdt,
                margin_required_usdt=args.add_usdt,
                leverage=1,
                bucket=snapshot.get('buckets', {}).get(test_key, bucket),
                existing_positions=positions,
                current_open_amount=current_open_amount,
            )
            snapshot = apply_state_patch(snapshot, add.state_patch)
            append_step(run, f'cycle_{cycle}:add_{add_index}', add.detail, add.venue_response, {'current_open_amount_before': current_open_amount})
            time.sleep(args.sleep_seconds)
            current_bar_id += 1

        positions = snapshot.get('positions', {}).get(test_key, []) or []
        exit_all = executor.submit_exit_signal(
            position_key=test_key,
            symbol=exec_symbol,
            strategy=f'test_{args.strategy}',
            positions=positions,
            reason=f'test_mode_cycle_{cycle}_exit_all',
            bar_id=current_bar_id,
            bucket=snapshot.get('buckets', {}).get(test_key, bucket),
            exit_side=None,
        )
        snapshot = apply_state_patch(snapshot, exit_all.state_patch)
        append_step(run, f'cycle_{cycle}:exit_all', exit_all.detail, exit_all.venue_response)
        time.sleep(args.sleep_seconds)
        current_bar_id += 1

    per_account_positions = {client.account_alias: client.exchange.fetch_positions([exec_symbol])}
    run['alignment'] = position_alignment_report(snapshot, per_account_positions)
    run['final_bucket'] = snapshot.get('buckets', {}).get(test_key)
    run['final_positions'] = snapshot.get('positions', {}).get(test_key, [])

    out = REPORTS / 'latest-test-mode.json'
    out.write_text(json.dumps(run, indent=2, default=str))

    if args.write_state:
        store.save(snapshot)

    print(json.dumps(run, indent=2, default=str))


if __name__ == '__main__':
    main()
