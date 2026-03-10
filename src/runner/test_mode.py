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
    p.add_argument('--sleep-seconds', type=float, default=2.0)
    p.add_argument('--arm-demo-submit', action='store_true')
    p.add_argument('--write-state', action='store_true')
    return p.parse_args()


def main() -> None:
    args = parse_args()
    settings = Settings.load()
    settings.ensure_demo_only()

    client = OkxClientRegistry(settings).for_strategy(args.strategy)
    executor = DemoExecutor(armed=args.arm_demo_submit and not settings.dry_run, client=client)
    store = StateStore(LOGS / 'state.json')
    snapshot = store.load()

    key = f'{args.strategy}:{args.symbol}'
    exec_symbol = settings.execution_symbol(args.strategy, args.symbol)
    bucket = ensure_bucket(snapshot, key, args.strategy, exec_symbol, settings.bucket_initial_capital_usdt)
    positions = snapshot.get('positions', {}).get(key, []) or []
    open_positions = [p for p in positions if p.get('status') == 'open']

    if open_positions:
        raise RuntimeError(f'test_mode requires a flat local bucket first: {key} has {len(open_positions)} open positions')
    live_before = client.current_live_position(exec_symbol)
    if live_before is not None:
        raise RuntimeError(f'test_mode requires a flat exchange symbol first: {live_before}')

    now_bar_id = int(datetime.now(UTC).timestamp() * 1000)
    run = {
        'generated_at': datetime.now(UTC).isoformat(),
        'type': 'test_mode',
        'strategy': args.strategy,
        'symbol': args.symbol,
        'execution_symbol': exec_symbol,
        'side': args.side,
        'armed_demo_submit': bool(args.arm_demo_submit and not settings.dry_run),
        'steps': [],
    }

    first = executor.submit_entry_signal(
        position_key=key,
        symbol=exec_symbol,
        strategy=args.strategy,
        side=args.side,
        reason='test_mode_entry',
        bar_id=now_bar_id,
        order_size_usdt=args.entry_usdt,
        margin_required_usdt=args.entry_usdt,
        leverage=1,
        bucket=bucket,
        existing_positions=positions,
        current_open_amount=0.0,
    )
    snapshot = apply_state_patch(snapshot, first.state_patch)
    run['steps'].append({
        'step': 'entry_1',
        'detail': first.detail,
        'venue_response': first.venue_response,
    })

    time.sleep(args.sleep_seconds)
    positions = snapshot.get('positions', {}).get(key, []) or []
    open_positions = [p for p in positions if p.get('status') == 'open']
    current_open_amount = sum(float(p.get('amount') or 0.0) for p in open_positions if p.get('side') == args.side)

    second = executor.submit_entry_signal(
        position_key=key,
        symbol=exec_symbol,
        strategy=args.strategy,
        side=args.side,
        reason='test_mode_add',
        bar_id=now_bar_id + 1,
        order_size_usdt=args.add_usdt,
        margin_required_usdt=args.add_usdt,
        leverage=1,
        bucket=snapshot.get('buckets', {}).get(key, bucket),
        existing_positions=positions,
        current_open_amount=current_open_amount,
    )
    snapshot = apply_state_patch(snapshot, second.state_patch)
    run['steps'].append({
        'step': 'entry_2_add',
        'detail': second.detail,
        'venue_response': second.venue_response,
    })

    time.sleep(args.sleep_seconds)
    positions = snapshot.get('positions', {}).get(key, []) or []
    exit_all = executor.submit_exit_signal(
        position_key=key,
        symbol=exec_symbol,
        strategy=args.strategy,
        positions=positions,
        reason='test_mode_exit_all',
        bar_id=now_bar_id + 2,
        bucket=snapshot.get('buckets', {}).get(key, bucket),
        exit_side=None,
    )
    snapshot = apply_state_patch(snapshot, exit_all.state_patch)
    run['steps'].append({
        'step': 'exit_all',
        'detail': exit_all.detail,
        'venue_response': exit_all.venue_response,
    })

    per_account_positions = {client.account_alias: client.exchange.fetch_positions([exec_symbol])}
    run['alignment'] = position_alignment_report(snapshot, per_account_positions)
    run['final_bucket'] = snapshot.get('buckets', {}).get(key)
    run['final_positions'] = snapshot.get('positions', {}).get(key, [])

    out = REPORTS / 'latest-test-mode.json'
    out.write_text(json.dumps(run, indent=2, default=str))

    if args.write_state:
        store.save(snapshot)

    print(json.dumps(run, indent=2, default=str))


if __name__ == '__main__':
    main()
