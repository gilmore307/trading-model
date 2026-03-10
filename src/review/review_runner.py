from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path

from src.review.windows import rolling_windows
from src.storage.state import StateStore

ROOT = Path('/root/.openclaw/workspace/projects/okx-trading')
LOGS = ROOT / 'logs'
REPORTS = ROOT / 'reports'
CHANGES = REPORTS / 'changes'
REPORTS.mkdir(parents=True, exist_ok=True)


def is_test_position_key(value: str | None) -> bool:
    return bool(value and value.startswith('test:'))


def is_test_strategy(value: str | None) -> bool:
    return bool(value and value.startswith('test_'))


def is_test_history_row(row: dict) -> bool:
    return is_test_position_key(row.get('position_key')) or is_test_strategy(row.get('strategy'))


def filter_prod_state(state: dict | None) -> dict | None:
    if state is None:
        return None
    positions = {
        key: value
        for key, value in (state.get('positions') or {}).items()
        if not is_test_position_key(key)
    }
    buckets = {
        key: value
        for key, value in (state.get('buckets') or {}).items()
        if not is_test_position_key(key)
    }
    last_signals = {
        key: value
        for key, value in (state.get('last_signals') or {}).items()
        if not is_test_position_key(key)
    }
    history = [row for row in (state.get('history') or []) if not is_test_history_row(row)]
    open_positions = sum(
        1
        for value in positions.values()
        for item in (value if isinstance(value, list) else [value])
        if item.get('status') == 'open'
    )
    return {
        **state,
        'positions': positions,
        'buckets': buckets,
        'last_signals': last_signals,
        'history': history,
        'open_positions': open_positions,
    }


def load_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def count_jsonl_rows(path: Path, start_ts_ms: int | None = None, end_ts_ms: int | None = None) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            ts = int(row.get('ts') or row.get('bar_id') or 0)
            if start_ts_ms is not None and ts < start_ts_ms:
                continue
            if end_ts_ms is not None and ts >= end_ts_ms:
                continue
            count += 1
    return count


FEE_EXPECTED_EVENT_TYPES = {'entry', 'exit'}
FEE_TO_PROFIT_REDUCE_FREQUENCY_THRESHOLD = 0.2


def build_fee_analysis(summary: dict, state: dict | None) -> dict:
    fees = summary.get('fees', {})
    realized_pnl_total = float(summary.get('realized_pnl_usdt_total') or 0.0)
    if realized_pnl_total == 0.0:
        bucket_rows = [] if state is None else list((state.get('buckets') or {}).values())
        for bucket in bucket_rows:
            realized_pnl_total += float(bucket.get('realized_pnl_usdt') or 0.0)

    fee_usdt_total = float(fees.get('fee_usdt_total') or 0.0)
    expected_fee_events = int(fees.get('expected_fee_events') or 0)
    avg_fee_per_execution = None if expected_fee_events <= 0 else fee_usdt_total / expected_fee_events

    fee_to_profit_ratio = None
    recommendation = 'insufficient_profit_basis'
    if realized_pnl_total > 0:
        fee_to_profit_ratio = fee_usdt_total / realized_pnl_total
        recommendation = 'reduce_frequency' if fee_to_profit_ratio >= FEE_TO_PROFIT_REDUCE_FREQUENCY_THRESHOLD else 'no_change'

    return {
        'module': 'fee_frequency_control',
        'fee_usdt_total': fee_usdt_total,
        'expected_fee_events': expected_fee_events,
        'events_with_fee': int(fees.get('events_with_fee') or 0),
        'events_missing_fee': int(fees.get('events_missing_fee') or 0),
        'fee_coverage_ratio': fees.get('fee_coverage_ratio'),
        'avg_fee_per_execution': avg_fee_per_execution,
        'realized_pnl_usdt_total': realized_pnl_total,
        'fee_to_realized_pnl_ratio': fee_to_profit_ratio,
        'frequency_adjustment_recommendation': recommendation,
        'reduce_frequency_threshold': FEE_TO_PROFIT_REDUCE_FREQUENCY_THRESHOLD,
    }


def summarize_history(state: dict | None, start_ts_ms: int | None = None, end_ts_ms: int | None = None) -> dict:
    history = [] if state is None else (state.get('history') or [])
    summary = {
        'total_events': 0,
        'fees': {
            'expected_fee_events': 0,
            'events_with_fee': 0,
            'events_missing_fee': 0,
            'fee_usdt_total': 0.0,
            'fee_coverage_ratio': None,
            'missing_fee_event_ids': [],
        },
        'anomalies': {
            'bucket_lock_count': 0,
            'reconcile_mismatch_count': 0,
            'reconcile_exit_count': 0,
            'entry_incomplete_count': 0,
        },
        'realized_pnl_usdt_total': 0.0,
        'by_strategy_symbol': {},
    }

    for row in history:
        ts = int(row.get('ts') or row.get('bar_id') or 0)
        if start_ts_ms is not None and ts < start_ts_ms:
            continue
        if end_ts_ms is not None and ts >= end_ts_ms:
            continue
        summary['total_events'] += 1
        event_type = row.get('type') or 'unknown'
        strategy = row.get('strategy') or 'unknown'
        symbol = row.get('symbol') or 'unknown'
        key = f'{strategy}:{symbol}'
        bucket = summary['by_strategy_symbol'].setdefault(key, {
            'strategy': strategy,
            'symbol': symbol,
            'events': 0,
            'entries': 0,
            'exits': 0,
            'bucket_locks': 0,
            'reconcile_mismatches': 0,
            'reconcile_exits': 0,
            'fee_events': 0,
            'fee_usdt_total': 0.0,
        })
        bucket['events'] += 1
        if event_type == 'entry':
            bucket['entries'] += 1
        if event_type == 'exit':
            bucket['exits'] += 1
            try:
                summary['realized_pnl_usdt_total'] += float(row.get('realized_pnl_usdt') or 0.0)
            except Exception:
                pass
        if event_type == 'bucket_lock':
            summary['anomalies']['bucket_lock_count'] += 1
            bucket['bucket_locks'] += 1
        if event_type == 'reconcile_mismatch':
            summary['anomalies']['reconcile_mismatch_count'] += 1
            bucket['reconcile_mismatches'] += 1
        if event_type == 'exit' and str(row.get('mode')) == 'reconcile':
            summary['anomalies']['reconcile_exit_count'] += 1
            bucket['reconcile_exits'] += 1
        if 'entry_incomplete' in str(row.get('reason') or ''):
            summary['anomalies']['entry_incomplete_count'] += 1

        if event_type in FEE_EXPECTED_EVENT_TYPES:
            summary['fees']['expected_fee_events'] += 1
            fee = row.get('fee_usdt')
            if fee is None and event_type == 'exit':
                fee = row.get('exit_fee_usdt')
            if fee is None:
                summary['fees']['events_missing_fee'] += 1
                event_id = row.get('event_id')
                if event_id:
                    summary['fees']['missing_fee_event_ids'].append(event_id)
            else:
                try:
                    fee_value = float(fee)
                    summary['fees']['events_with_fee'] += 1
                    summary['fees']['fee_usdt_total'] += fee_value
                    bucket['fee_events'] += 1
                    bucket['fee_usdt_total'] += fee_value
                except Exception:
                    summary['fees']['events_missing_fee'] += 1
                    event_id = row.get('event_id')
                    if event_id:
                        summary['fees']['missing_fee_event_ids'].append(event_id)

    denom = summary['fees']['expected_fee_events']
    if denom > 0:
        summary['fees']['fee_coverage_ratio'] = summary['fees']['events_with_fee'] / denom

    summary['by_strategy_symbol'] = sorted(
        summary['by_strategy_symbol'].values(),
        key=lambda row: (row['strategy'], row['symbol'])
    )
    return summary


def main() -> None:
    windows = rolling_windows(datetime.now(UTC))
    health = load_json(LOGS / 'service' / 'health.json')
    snapshot = load_json(LOGS / 'service' / 'snapshot.json')
    state = filter_prod_state(StateStore(LOGS / 'state.json').load())
    events_path = LOGS / 'market-data' / 'events' / 'trades.jsonl'

    now_utc = datetime.now(UTC)
    live_cycle_start_utc = windows['weekly'].end_utc
    live_cycle_start_bj = windows['weekly'].end_bj

    report = {
        'generated_at': now_utc.isoformat(),
        'windows': {
            name: {
                'start_bj': window.start_bj.isoformat(),
                'end_bj': window.end_bj.isoformat(),
                'start_utc': window.start_utc.isoformat(),
                'end_utc': window.end_utc.isoformat(),
            }
            for name, window in windows.items()
        },
        'live_cycle': {
            'start_bj': live_cycle_start_bj.isoformat(),
            'end_bj': now_utc.astimezone(windows['weekly'].end_bj.tzinfo).isoformat(),
            'start_utc': live_cycle_start_utc.isoformat(),
            'end_utc': now_utc.isoformat(),
        },
        'health': health,
        'snapshot': snapshot,
        'workflow': load_json(CHANGES / 'latest-review-workflow.json'),
        'usdt_calibrate_plan': load_json(CHANGES / 'prepare-usdt-calibrate-plan.json'),
        'latest_calibrate_bucket_reset': load_json(CHANGES / 'latest-calibrate-bucket-reset.json'),
        'latest_parameter_change': load_json(CHANGES / 'latest-parameter-change.json'),
        'state_summary': {
            'open_positions': None if state is None else state.get('open_positions', 0),
            'bucket_count': 0 if state is None else len(state.get('buckets', {})),
        },
        'event_counts': {},
        'calibration_inputs': {},
    }

    for name, window in windows.items():
        start_ts_ms = int(window.start_utc.timestamp() * 1000)
        end_ts_ms = int(window.end_utc.timestamp() * 1000)
        report['event_counts'][name] = count_jsonl_rows(
            events_path,
            start_ts_ms,
            end_ts_ms,
        )
        window_summary = summarize_history(state, start_ts_ms, end_ts_ms)
        report['calibration_inputs'][name] = window_summary
        report.setdefault('fee_analysis', {})[name] = build_fee_analysis(window_summary, state)

    live_cycle_start_ts_ms = int(live_cycle_start_utc.timestamp() * 1000)
    live_cycle_end_ts_ms = int(now_utc.timestamp() * 1000)
    report['event_counts']['live_cycle'] = count_jsonl_rows(
        events_path,
        live_cycle_start_ts_ms,
        live_cycle_end_ts_ms,
    )
    live_cycle_summary = summarize_history(
        state,
        live_cycle_start_ts_ms,
        live_cycle_end_ts_ms,
    )
    report['calibration_inputs']['live_cycle'] = live_cycle_summary
    report.setdefault('fee_analysis', {})['live_cycle'] = build_fee_analysis(live_cycle_summary, state)

    out = REPORTS / 'review-latest.json'
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
