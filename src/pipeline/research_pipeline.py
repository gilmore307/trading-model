from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PIPELINE_DIR = ROOT / 'logs' / 'pipeline'
RUNS_DIR = PIPELINE_DIR / 'runs'
STATE_DIR = PIPELINE_DIR / 'state'
LATEST_MANIFEST = STATE_DIR / 'latest_run.json'
DEFAULT_CONFIG_PATH = ROOT / 'config' / 'research_pipeline.json'


@dataclass
class StepResult:
    name: str
    status: str
    returncode: int
    started_at: str
    finished_at: str
    duration_sec: float
    command: list[str]
    log_path: str
    summary: dict[str, Any] | None = None
    skip_reason: str | None = None


class PipelineFailure(RuntimeError):
    pass


def utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def load_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or DEFAULT_CONFIG_PATH
    return json.loads(config_path.read_text(encoding='utf-8'))


def ensure_dirs() -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def make_run_id(prefix: str = 'research') -> str:
    return f"{prefix}_{datetime.now(tz=UTC).strftime('%Y%m%dT%H%M%SZ')}"


def _expand_value(value: Any, context: dict[str, str]) -> Any:
    if isinstance(value, str):
        return value.format(**context)
    if isinstance(value, list):
        return [_expand_value(v, context) for v in value]
    if isinstance(value, dict):
        return {k: _expand_value(v, context) for k, v in value.items()}
    return value


def build_context(config: dict[str, Any], run_id: str) -> dict[str, str]:
    artifacts = config.get('artifacts', {})
    context = {
        'root': str(ROOT),
        'run_id': run_id,
    }
    for key, value in artifacts.items():
        context[key] = _expand_value(value, context)
    return context


def _expand_paths(values: list[str] | None, context: dict[str, str]) -> list[Path]:
    expanded: list[Path] = []
    for value in values or []:
        expanded.append(ROOT / _expand_value(value, context))
    return expanded


def _latest_mtime(paths: list[Path]) -> float | None:
    existing = [path.stat().st_mtime for path in paths if path.exists()]
    return max(existing) if existing else None


def _oldest_mtime(paths: list[Path]) -> float | None:
    if not paths or any(not path.exists() for path in paths):
        return None
    return min(path.stat().st_mtime for path in paths)


def should_skip_step(step: dict[str, Any], *, context: dict[str, str]) -> tuple[bool, str | None]:
    if not step.get('skip_if_outputs_fresh'):
        return False, None
    inputs = _expand_paths(step.get('inputs'), context)
    outputs = _expand_paths(step.get('outputs'), context)
    if not outputs:
        return False, None
    oldest_output = _oldest_mtime(outputs)
    if oldest_output is None:
        return False, None
    latest_input = _latest_mtime(inputs)
    if latest_input is None:
        return True, 'outputs_exist_and_no_inputs_declared'
    if latest_input <= oldest_output:
        return True, 'outputs_newer_than_inputs'
    return False, None


def make_skipped_result(step: dict[str, Any], *, context: dict[str, str], run_dir: Path, reason: str) -> StepResult:
    step_name = step['name']
    log_path = run_dir / f'{step_name}.log'
    timestamp = utc_now_iso()
    command = _expand_value(step['command'], context)
    log_path.write_text(json.dumps({'event': 'step_skipped', 'step': step_name, 'reason': reason, 'command': command}, ensure_ascii=False) + '\n', encoding='utf-8')
    return StepResult(
        name=step_name,
        status='skipped',
        returncode=0,
        started_at=timestamp,
        finished_at=timestamp,
        duration_sec=0.0,
        command=command,
        log_path=str(log_path),
        summary=None,
        skip_reason=reason,
    )


def run_step(step: dict[str, Any], *, context: dict[str, str], run_dir: Path) -> StepResult:
    step_name = step['name']
    command = _expand_value(step['command'], context)
    started_at = utc_now_iso()
    started = time.time()
    log_path = run_dir / f'{step_name}.log'
    env = os.environ.copy()
    env.update({str(k): str(v) for k, v in step.get('env', {}).items()})

    with log_path.open('w', encoding='utf-8') as log_handle:
        log_handle.write(json.dumps({'event': 'step_start', 'step': step_name, 'started_at': started_at, 'command': command}, ensure_ascii=False) + '\n')
        log_handle.flush()
        proc = subprocess.run(
            command,
            cwd=str(ROOT),
            env=env,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    finished_at = utc_now_iso()
    duration_sec = round(time.time() - started, 3)
    summary = None
    try:
        last_lines = log_path.read_text(encoding='utf-8').strip().splitlines()
        if last_lines:
            summary = json.loads(last_lines[-1])
    except Exception:
        summary = None
    status = 'ok' if proc.returncode == 0 else 'failed'
    return StepResult(
        name=step_name,
        status=status,
        returncode=proc.returncode,
        started_at=started_at,
        finished_at=finished_at,
        duration_sec=duration_sec,
        command=command,
        log_path=str(log_path),
        summary=summary,
    )


def run_pipeline(config: dict[str, Any], *, only_steps: list[str] | None = None, skip_steps: list[str] | None = None, run_id: str | None = None) -> dict[str, Any]:
    ensure_dirs()
    actual_run_id = run_id or make_run_id(config.get('name', 'research'))
    run_dir = RUNS_DIR / actual_run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    context = build_context(config, actual_run_id)

    manifest: dict[str, Any] = {
        'run_id': actual_run_id,
        'pipeline_name': config.get('name', 'research'),
        'started_at': utc_now_iso(),
        'status': 'running',
        'config_path': str(DEFAULT_CONFIG_PATH),
        'steps': [],
        'context': context,
    }
    (run_dir / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

    selected = []
    for step in config.get('steps', []):
        name = step['name']
        if only_steps and name not in only_steps:
            continue
        if skip_steps and name in skip_steps:
            continue
        selected.append(step)

    for step in selected:
        skip, reason = should_skip_step(step, context=context)
        if skip:
            result = make_skipped_result(step, context=context, run_dir=run_dir, reason=reason or 'fresh_outputs')
        else:
            result = run_step(step, context=context, run_dir=run_dir)
        manifest['steps'].append(result.__dict__)
        (run_dir / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        if result.status not in {'ok', 'skipped'}:
            manifest['status'] = 'failed'
            manifest['finished_at'] = utc_now_iso()
            (run_dir / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
            LATEST_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
            raise PipelineFailure(f"step failed: {result.name}")

    manifest['status'] = 'ok'
    manifest['finished_at'] = utc_now_iso()
    (run_dir / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    LATEST_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return manifest
