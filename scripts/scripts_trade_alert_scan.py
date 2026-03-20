from __future__ import annotations

import json
from pathlib import Path
from typing import Any

RUNTIME_DIR = Path('/root/.openclaw/workspace/projects/crypto-trading/logs/runtime')
DAEMON_LOG = RUNTIME_DIR / 'trade-daemon.jsonl'
LATEST_ARTIFACT = RUNTIME_DIR / 'latest-execution-cycle.json'
STATE_PATH = RUNTIME_DIR / 'openclaw-trade-alert-state.json'


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def main() -> None:
    state = read_json(STATE_PATH)
    last_daemon_size = int(state.get('last_daemon_size') or 0)
    last_trade_fingerprint = state.get('last_trade_fingerprint')
    last_warn_fingerprint = state.get('last_warn_fingerprint')

    events: list[dict[str, Any]] = []

    if DAEMON_LOG.exists():
        content = DAEMON_LOG.read_text(encoding='utf-8')
        if len(content) > last_daemon_size:
            delta = content[last_daemon_size:]
            last_daemon_size = len(content)
            for line in delta.splitlines():
                line = line.strip()
                if not line:
                    continue
                event = json.loads(line)
                if event.get('event') == 'cycle_error':
                    events.append({'kind': 'cycle_error', 'payload': event})

    artifact = read_json(LATEST_ARTIFACT)
    summary = artifact.get('summary') if isinstance(artifact, dict) else {}
    if isinstance(summary, dict) and summary:
        action = summary.get('plan_action')
        receipt_accepted = summary.get('receipt_accepted')
        recorded_at = artifact.get('recorded_at')
        trade_fp = f"{recorded_at}|{action}|{summary.get('plan_account')}|{summary.get('symbol')}|{summary.get('receipt_mode')}|{receipt_accepted}"
        if action in {'enter', 'exit'} and receipt_accepted and trade_fp != last_trade_fingerprint:
            events.append({'kind': 'trade_execution', 'payload': artifact})
            last_trade_fingerprint = trade_fp

        warn_fp = f"{recorded_at}|{summary.get('block_reason')}|{summary.get('policy_reason')}"
        if (summary.get('block_reason') or summary.get('policy_reason')) and warn_fp != last_warn_fingerprint:
            events.append({'kind': 'runtime_warning', 'payload': artifact})
            last_warn_fingerprint = warn_fp

    write_json(STATE_PATH, {
        'last_daemon_size': last_daemon_size,
        'last_trade_fingerprint': last_trade_fingerprint,
        'last_warn_fingerprint': last_warn_fingerprint,
    })
    print(json.dumps({'events': events}, ensure_ascii=False))


if __name__ == '__main__':
    main()
