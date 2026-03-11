from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from src.review.compare import FLAT_COMPARE_ALIAS
from src.review.performance import DEFAULT_COMPARE_ACCOUNTS


@dataclass(slots=True)
class AggregatedAccountMetrics:
    account: str
    pnl_usdt: float | None = None
    equity_usdt: float | None = None
    trade_count: int = 0
    fee_usdt: float | None = None
    exposure_time_pct: float | None = None
    source: str = 'aggregated'


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def aggregate_from_execution_history(history_path: str | Path, base_metrics: dict[str, dict[str, Any]] | None = None) -> dict[str, dict[str, Any]]:
    base_metrics = {k: dict(v) for k, v in (base_metrics or {}).items()}
    rows = _load_jsonl(Path(history_path))
    counts = {alias: 0 for alias in DEFAULT_COMPARE_ACCOUNTS}
    fee_totals = {alias: 0.0 for alias in DEFAULT_COMPARE_ACCOUNTS}
    fee_seen = {alias: False for alias in DEFAULT_COMPARE_ACCOUNTS}
    exposure_counts = {alias: 0 for alias in DEFAULT_COMPARE_ACCOUNTS}

    total_rows = len(rows)
    for row in rows:
        summary = row.get('summary', {})
        plan_account = summary.get('plan_account')
        plan_action = summary.get('plan_action')
        receipt_accepted = summary.get('receipt_accepted')
        receipt_mode = summary.get('receipt_mode')

        if plan_account in counts and plan_action in {'enter', 'exit'} and receipt_accepted is not False:
            counts[plan_account] += 1

        compare_snapshot = row.get('compare_snapshot', {})
        for account_row in compare_snapshot.get('accounts', []):
            alias = account_row.get('account')
            if alias in exposure_counts and account_row.get('has_position'):
                exposure_counts[alias] += 1

        composite_owner = summary.get('composite_position_owner')
        composite_action = summary.get('composite_plan_action')
        if composite_owner == 'router_composite' and composite_action in {'enter', 'exit'}:
            counts['router_composite'] += 1
        elif composite_owner in counts and composite_action in {'enter', 'exit'}:
            counts['router_composite'] += 1

        # Fee aggregation remains placeholder-friendly until a canonical receipt fee source is persisted.
        # Accept externally supplied fee values via base_metrics for now.

    for alias in DEFAULT_COMPARE_ACCOUNTS:
        existing = base_metrics.setdefault(alias, {})
        existing.setdefault('source', 'aggregated')
        existing['trade_count'] = int(existing.get('trade_count') or 0) + counts[alias]
        if total_rows > 0:
            existing['exposure_time_pct'] = float(existing.get('exposure_time_pct') or 0.0) or round(100.0 * exposure_counts[alias] / total_rows, 2)
        if fee_seen[alias]:
            existing['fee_usdt'] = float(existing.get('fee_usdt') or 0.0) + fee_totals[alias]

    if FLAT_COMPARE_ALIAS not in base_metrics:
        base_metrics[FLAT_COMPARE_ALIAS] = {'source': 'aggregated', 'trade_count': 0, 'exposure_time_pct': 0.0}

    return base_metrics
