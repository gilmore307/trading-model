from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.config.settings import Settings
from src.execution.adapters import DryRunExecutionAdapter, OkxExecutionAdapter
from src.execution.pipeline import ExecutionPipeline
from src.runners.discord_notifier import DiscordNotifier
from src.runners.execution_cycle import persist_execution_artifact
from src.runtime.mode import RuntimeMode
from src.runtime.store import RuntimeStore

OUT_DIR = Path('/root/.openclaw/workspace/projects/crypto-trading/logs/runtime')
OUT_DIR.mkdir(parents=True, exist_ok=True)
DAEMON_LOG = OUT_DIR / 'trade-daemon.jsonl'
PID_PATH = OUT_DIR / 'trade-daemon.pid'


def _json_default(value: Any):
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    return str(value)


def _log_event(event: dict[str, Any]) -> None:
    with DAEMON_LOG.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(event, default=_json_default, ensure_ascii=False) + '\n')


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Run continuous trade daemon for crypto-trading demo execution.')
    parser.add_argument('--interval-seconds', type=float, default=60.0, help='Seconds between execution cycles.')
    parser.add_argument('--max-cycles', type=int, default=0, help='Optional max cycles for bounded runs. 0 means run forever.')
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    settings = Settings.load()
    settings.ensure_demo_only()

    runtime_store = RuntimeStore()
    runtime_store.set_mode(RuntimeMode.TRADE, reason='daemon_start_trade_mode')

    notifier = DiscordNotifier(settings)
    adapter = DryRunExecutionAdapter() if settings.dry_run else OkxExecutionAdapter(settings)
    pipeline = ExecutionPipeline(settings=settings, runtime_store=runtime_store, adapter=adapter)

    PID_PATH.write_text(str(Path('/proc/self').resolve().name), encoding='utf-8')
    _log_event({
        'event': 'daemon_started',
        'observed_at': datetime.now(UTC),
        'interval_seconds': args.interval_seconds,
        'dry_run': settings.dry_run,
        'mode': runtime_store.get().mode.value,
    })

    cycles = 0
    while True:
        cycle_started_at = datetime.now(UTC)
        try:
            result = pipeline.run_cycle(exchange_snapshot=None)
            artifact = persist_execution_artifact(result)
            summary = artifact.get('summary', {}) if isinstance(artifact, dict) else {}
            cycle_event = {
                'event': 'cycle_ok',
                'observed_at': cycle_started_at,
                'runtime_mode': summary.get('runtime_mode'),
                'symbol': summary.get('symbol'),
                'regime': summary.get('regime'),
                'plan_action': summary.get('plan_action'),
                'plan_account': summary.get('plan_account'),
                'receipt_mode': summary.get('receipt_mode'),
                'receipt_accepted': summary.get('receipt_accepted'),
                'block_reason': summary.get('block_reason'),
                'policy_reason': summary.get('policy_reason'),
                'diagnostics': summary.get('diagnostics'),
            }
            _log_event(cycle_event)

            notifier.notify_trade(summary, artifact)
            notifier.notify_warning(summary)
        except Exception as exc:
            error_event = {
                'event': 'cycle_error',
                'observed_at': cycle_started_at,
                'error': repr(exc),
            }
            _log_event(error_event)
            notifier.notify_error(error_event)

        cycles += 1
        if args.max_cycles > 0 and cycles >= args.max_cycles:
            break
        time.sleep(max(1.0, args.interval_seconds))

    _log_event({
        'event': 'daemon_stopped',
        'observed_at': datetime.now(UTC),
        'cycles': cycles,
    })


if __name__ == '__main__':
    main()
