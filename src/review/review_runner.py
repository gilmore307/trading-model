from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path

from src.review.windows import rolling_windows

ROOT = Path('/root/.openclaw/workspace/projects/okx-trading')
LOGS = ROOT / 'logs'
REPORTS = ROOT / 'reports'
CHANGES = REPORTS / 'changes'
REPORTS.mkdir(parents=True, exist_ok=True)


def load_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text())


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


def main() -> None:
    windows = rolling_windows(datetime.now(UTC))
    health = load_json(LOGS / 'service' / 'health.json')
    snapshot = load_json(LOGS / 'service' / 'snapshot.json')
    state = load_json(LOGS / 'state.json')
    events_path = LOGS / 'market-data' / 'events' / 'trades.jsonl'

    report = {
        'generated_at': datetime.now(UTC).isoformat(),
        'windows': {
            name: {
                'start_bj': window.start_bj.isoformat(),
                'end_bj': window.end_bj.isoformat(),
                'start_utc': window.start_utc.isoformat(),
                'end_utc': window.end_utc.isoformat(),
            }
            for name, window in windows.items()
        },
        'health': health,
        'snapshot': snapshot,
        'workflow': load_json(CHANGES / 'latest-review-workflow.json'),
        'usdt_reset_plan': load_json(CHANGES / 'prepare-usdt-reset-plan.json'),
        'latest_weekly_reset': load_json(CHANGES / 'latest-weekly-reset.json'),
        'latest_parameter_change': load_json(CHANGES / 'latest-parameter-change.json'),
        'state_summary': {
            'open_positions': None if state is None else state.get('open_positions', 0),
            'bucket_count': 0 if state is None else len(state.get('buckets', {})),
        },
        'event_counts': {},
    }

    for name, window in windows.items():
        report['event_counts'][name] = count_jsonl_rows(
            events_path,
            int(window.start_utc.timestamp() * 1000),
            int(window.end_utc.timestamp() * 1000),
        )

    out = REPORTS / 'review-latest.json'
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
