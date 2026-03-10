from __future__ import annotations

import os
from pathlib import Path

ROOT = Path('/root/.openclaw/workspace/projects/okx-trading').resolve()
RUN_DAEMON_PATH = (ROOT / 'run_daemon.sh').resolve()


def _proc_cwd(pid: str) -> Path | None:
    try:
        return Path(os.readlink(f'/proc/{pid}/cwd')).resolve()
    except Exception:
        return None


def _proc_cmdline(pid: str) -> str:
    try:
        raw = Path(f'/proc/{pid}/cmdline').read_bytes()
    except Exception:
        return ''
    return raw.replace(b'\x00', b' ').decode(errors='ignore').strip()


def list_okx_trading_daemon_pids() -> list[dict]:
    current_pid = os.getpid()
    matches: list[dict] = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        pid = proc.name
        try:
            pid_int = int(pid)
        except Exception:
            continue
        if pid_int == current_pid:
            continue
        cwd = _proc_cwd(pid)
        cmdline = _proc_cmdline(pid)
        if not cmdline:
            continue
        daemon_like = 'run_daemon.sh' in cmdline
        same_project = cwd == ROOT
        explicit_path = str(RUN_DAEMON_PATH) in cmdline
        relative_path = 'bash ./run_daemon.sh' in cmdline and same_project
        if daemon_like and (same_project or explicit_path or relative_path):
            matches.append({
                'pid': pid_int,
                'cwd': str(cwd) if cwd else None,
                'cmdline': cmdline,
            })
    return sorted(matches, key=lambda row: row['pid'])


def current_daemon_pid() -> int | None:
    pidfile = ROOT / 'logs' / 'service' / 'daemon.pid'
    if not pidfile.exists():
        return None
    try:
        return int(pidfile.read_text().strip())
    except Exception:
        return None


def assert_single_okx_trading_daemon_context(*, allow_current_run_daemon_pid: int | None = None) -> None:
    matches = list_okx_trading_daemon_pids()
    if allow_current_run_daemon_pid is not None:
        matches = [row for row in matches if row['pid'] != allow_current_run_daemon_pid]
    if matches:
        details = '; '.join(f"pid={row['pid']} cwd={row['cwd']} cmd={row['cmdline']}" for row in matches)
        raise RuntimeError(f'conflicting_okx_trading_daemon_instances_detected: {details}')
