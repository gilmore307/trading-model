from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path('/root/.openclaw/workspace/projects/okx-trading')
MODE_PATH = ROOT / 'logs' / 'service' / 'mode-state.json'
BJ = ZoneInfo('Asia/Shanghai')
VALID_MODES = {'trade', 'review', 'reset', 'develop'}


def default_mode(now_utc: datetime | None = None) -> str:
    now_utc = now_utc or datetime.now(UTC)
    now_bj = now_utc.astimezone(BJ)
    return 'review' if (now_bj.weekday() == 6 and now_bj.hour == 0) else 'develop'


def load_mode_state(now_utc: datetime | None = None) -> dict:
    now_utc = now_utc or datetime.now(UTC)
    now_bj = now_utc.astimezone(BJ)
    MODE_PATH.parent.mkdir(parents=True, exist_ok=True)
    source = 'default'
    mode = default_mode(now_utc)
    if MODE_PATH.exists():
        try:
            payload = json.loads(MODE_PATH.read_text())
            candidate = payload.get('mode')
            if candidate in VALID_MODES:
                mode = candidate
                source = 'manual'
        except Exception:
            source = 'default_invalid_file'
    return {
        'generated_at': now_utc.isoformat(),
        'mode': mode,
        'source': source,
        'bj_time': now_bj.isoformat(),
        'utc_time': now_utc.isoformat(),
        'valid_modes': sorted(VALID_MODES),
    }


def set_mode(mode: str, *, reason: str | None = None, actor: str = 'system', now_utc: datetime | None = None) -> dict:
    if mode not in VALID_MODES:
        raise ValueError(f'Unsupported mode: {mode}')
    now_utc = now_utc or datetime.now(UTC)
    payload = {
        'mode': mode,
        'reason': reason,
        'actor': actor,
        'updated_at': now_utc.isoformat(),
    }
    MODE_PATH.parent.mkdir(parents=True, exist_ok=True)
    MODE_PATH.write_text(json.dumps(payload, indent=2))
    return payload
