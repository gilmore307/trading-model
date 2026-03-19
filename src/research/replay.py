from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
import json

from src.research.dataset_builder import build_research_row
from src.research.runtime_adapters import regime_local_artifact_to_snapshot_row
from src.runners.regime_runner import RegimeRunnerOutput


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    raise ValueError(f'unsupported datetime value: {value!r}')


def output_from_row(row: dict[str, Any]) -> RegimeRunnerOutput:
    if row.get('artifact_type') == 'regime_local_cycle':
        row = regime_local_artifact_to_snapshot_row(row)
    return RegimeRunnerOutput(
        observed_at=_parse_dt(row['observed_at'] if 'observed_at' in row else row['timestamp']),
        symbol=row['symbol'],
        background_4h=row['background_4h'],
        primary_15m=row['primary_15m'],
        override_1m=row.get('override_1m'),
        background_features=row.get('background_features') or {},
        primary_features=row.get('primary_features') or {},
        override_features=row.get('override_features') or {},
        final_decision=row['final_decision'],
        route_decision=row['route_decision'],
        decision_summary=row.get('decision_summary') or {},
        settings=None,
    )


def load_snapshot_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows = []
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def build_dataset_from_snapshot_rows(rows: list[dict[str, Any]], *, close_prices: list[float] | None = None, horizons: dict[str, int] | None = None) -> list[dict[str, Any]]:
    if close_prices is None:
        inferred_prices = []
        for row in rows:
            if row.get('artifact_type') == 'regime_local_cycle':
                row = regime_local_artifact_to_snapshot_row(row)
            primary = row.get('primary_features') or {}
            price = primary.get('last_price')
            inferred_prices.append(None if price is None else float(price))
        if inferred_prices and all(p is not None for p in inferred_prices):
            close_prices = [float(p) for p in inferred_prices]
    dataset = []
    for idx, row in enumerate(rows):
        output = output_from_row(row)
        dataset.append(build_research_row(output=output, prices=close_prices, index=idx if close_prices is not None else None, horizons=horizons))
    return dataset
