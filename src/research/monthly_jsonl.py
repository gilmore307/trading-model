from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_one_jsonl(path: Path, *, skip_invalid: bool = True) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open('r', encoding='utf-8') as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                if skip_invalid:
                    continue
                raise ValueError(f'invalid jsonl at {path}:{line_no}')
            if isinstance(value, dict):
                rows.append(value)
    return rows


def load_monthly_jsonl_rows(path: str | Path, *, skip_invalid: bool = True) -> list[dict[str, Any]]:
    target = Path(path)
    if target.is_file():
        rows = _load_one_jsonl(target, skip_invalid=skip_invalid)
        rows.sort(key=lambda row: int(row.get('ts', 0)))
        return rows

    if not target.exists():
        raise FileNotFoundError(target)
    if not target.is_dir():
        raise ValueError(f'expected file or directory: {target}')

    rows: list[dict[str, Any]] = []
    for jsonl_path in sorted(target.glob('*.jsonl')):
        rows.extend(_load_one_jsonl(jsonl_path, skip_invalid=skip_invalid))
    rows.sort(key=lambda row: int(row.get('ts', 0)))
    return rows
