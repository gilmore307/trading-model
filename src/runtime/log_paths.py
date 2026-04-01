from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from src.runtime.business_time import to_business

RUNTIME_DIR = Path('/root/.openclaw/workspace/projects/crypto-trading/logs/runtime')
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def business_day_stamp(now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    return to_business(now).strftime('%Y-%m-%d')


def dated_runtime_dir(kind: str, now: datetime | None = None) -> Path:
    path = RUNTIME_DIR / kind
    path.mkdir(parents=True, exist_ok=True)
    return path


def dated_jsonl_path(kind: str, now: datetime | None = None) -> Path:
    return dated_runtime_dir(kind, now) / f'{business_day_stamp(now)}.jsonl'
