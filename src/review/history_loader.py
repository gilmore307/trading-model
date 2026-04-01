from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(UTC)
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(UTC)
    except ValueError:
        return None


def load_jsonl_rows(path: str | Path) -> list[dict[str, Any]]:
    target = Path(path)
    rows: list[dict[str, Any]] = []
    if target.is_file():
        candidates = [target]
    elif target.is_dir():
        candidates = sorted(target.glob('*.jsonl'))
    else:
        return []
    for candidate in candidates:
        for line in candidate.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows
