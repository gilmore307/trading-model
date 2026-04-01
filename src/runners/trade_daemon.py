from __future__ import annotations

import argparse
import fcntl
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
from src.runners.execution_cycle import persist_parallel_execution_artifact
from src.runtime.log_paths import RUNTIME_DIR, dated_jsonl_path
from src.runtime.mode import RuntimeMode
from src.runtime.store import RuntimeStore
from src.runtime.strategy_pointer import load_active_strategy_snapshot
from src.runtime.workflows import OkxWorkflowHooks, WorkflowHooks, WorkflowRunResult

OUT_DIR = RUNTIME_DIR
DAEMON_LOG = lambda: dated_jsonl_path('trade-daemon')
PID_PATH = OUT_DIR / 'trade-daemon.pid'
LOCK_PATH = OUT_DIR / 'trade-daemon.lock'
UPGRADE_REQUEST_PATH = OUT_DIR / 'latest-strategy-upgrade-request.json'


def _json_default(value: Any):
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    return str(value)


def _log_event(event: dict[str, Any]) -> None:
    with DAEMON_LOG().open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(event, default=_json_default, ensure_ascii=False) + '\n')


def _store_upgrade_request(event: dict[str, Any]) -> None:
    UPGRADE_REQUEST_PATH.write_text(json.dumps(event, default=_json_default, ensure_ascii=False, indent=2), encoding='utf-8')


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Run continuous trade daemon for crypto-trading demo execution.')
    parser.add_argument('--interval-seconds', type=float, default=60.0, help='Seconds between execution cycles.')
    parser.add_argument('--max-cycles', type=int, default=0, help='Optional max cycles for bounded runs. 0 means run forever.')
    return parser


def acquire_single_instance_lock():
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    handle = LOCK_PATH.open('a+', encoding='utf-8')
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        handle.seek(0)
        holder = handle.read().strip()
        raise RuntimeError(f'trade_daemon_lock_held:{holder or "unknown"}') from exc
    handle.seek(0)
    handle.truncate()
    handle.write(str(Path('/proc/self').resolve().name))
    handle.flush()
    return handle


def ensure_trade_start_ready(*, settings: Settings, runtime_store: RuntimeStore, hooks: WorkflowHooks | None = None) -> WorkflowRunResult | None:
    if runtime_store.get().mode != RuntimeMode.TRADE:
        return None
    hooks = hooks or OkxWorkflowHooks(settings)
    startup = hooks.verify_startup_capital()
    if startup.ok:
        return None
    _log_event({
        'event': 'trade_start_not_ready',
        'observed_at': datetime.now(UTC),
        'detail': startup.detail,
        'action': 'continue_trade_daemon_without_mode_switch',
    })
    return WorkflowRunResult(
        workflow='startup_readiness_check',
        started_mode=RuntimeMode.TRADE.value,
        ended_mode=RuntimeMode.TRADE.value,
        destructive=False,
        steps=[startup],
        observed_at=datetime.now(UTC),
    )


def main() -> None:
    args = build_arg_parser().parse_args()
    daemon_lock = acquire_single_instance_lock()
    settings = Settings.load()
    settings.ensure_demo_only()

    runtime_store = RuntimeStore()
    runtime_store.set_mode(RuntimeMode.TRADE, reason='daemon_start_trade_mode')

    startup_workflow = ensure_trade_start_ready(settings=settings, runtime_store=runtime_store)

    notifier = DiscordNotifier(settings)
    adapter = DryRunExecutionAdapter() if settings.dry_run else OkxExecutionAdapter(settings)
    pipeline = ExecutionPipeline(settings=settings, runtime_store=runtime_store, adapter=adapter)
    previous_strategy_version = None

    PID_PATH.write_text(str(Path('/proc/self').resolve().name), encoding='utf-8')
    _log_event({
        'event': 'daemon_started',
        'observed_at': datetime.now(UTC),
        'interval_seconds': args.interval_seconds,
        'dry_run': settings.dry_run,
        'mode': runtime_store.get().mode.value,
        'startup_workflow': None if startup_workflow is None else {
            'workflow': startup_workflow.workflow,
            'started_mode': startup_workflow.started_mode,
            'ended_mode': startup_workflow.ended_mode,
            'steps': [asdict(step) for step in startup_workflow.steps],
        },
    })

    cycles = 0
    while True:
        cycle_started_at = datetime.now(UTC)
        try:
            active_strategy = load_active_strategy_snapshot()
            if previous_strategy_version is None:
                previous_strategy_version = active_strategy.version
            elif active_strategy.version != previous_strategy_version:
                _log_event({
                    'event': 'strategy_hot_swap_detected',
                    'observed_at': cycle_started_at,
                    'previous_version': previous_strategy_version,
                    'active_strategy_version': active_strategy.version,
                    'active_strategy_source': active_strategy.source,
                    'active_strategy_family': active_strategy.metadata.get('family'),
                    'active_strategy_config_path': active_strategy.metadata.get('config_path'),
                    'active_strategy_promoted_at': active_strategy.metadata.get('promoted_at'),
                    'promotion_note': active_strategy.metadata.get('promotion_note'),
                })
                request_event = {
                    'event': 'strategy_upgrade_event_requested',
                    'observed_at': cycle_started_at,
                    'previous_version': previous_strategy_version,
                    'active_strategy_version': active_strategy.version,
                    'active_strategy_source': active_strategy.source,
                    'request_reason': 'detected_active_strategy_version_change',
                    'execution_policy': 'deferred_out_of_band',
                    'position_handover_policy': 'strategy_switch_handling',
                }
                _log_event(request_event)
                _store_upgrade_request(request_event)
                previous_strategy_version = active_strategy.version
            result = pipeline.run_cycle_parallel()
            artifact = persist_parallel_execution_artifact(result)
            summary = artifact.get('summary', {}) if isinstance(artifact, dict) else {}
            primary_summary = summary.get('primary_summary') or {}
            cycle_event = {
                'event': 'cycle_ok',
                'observed_at': cycle_started_at,
                'runtime_mode': summary.get('runtime_mode'),
                'active_strategy_version': summary.get('active_strategy_version'),
                'symbol': summary.get('symbol'),
                'regime': summary.get('regime'),
                'entered_accounts': summary.get('entered_accounts'),
                'accepted_accounts': summary.get('accepted_accounts'),
                'blocked_accounts': summary.get('blocked_accounts'),
                'strategy_results': summary.get('strategy_results'),
            }
            _log_event(cycle_event)

            for row in (artifact.get('results') or {}).values():
                row_summary = row.get('summary', {}) if isinstance(row, dict) else {}
                notifier.notify_trade(row_summary, row)
                notifier.notify_warning(row_summary)
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
    daemon_lock.close()


if __name__ == '__main__':
    main()
