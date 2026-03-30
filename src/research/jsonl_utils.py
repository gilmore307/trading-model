from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_jsonl_rows(path: Path, *, skip_invalid: bool = True) -> list[dict[str, Any]]:
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
