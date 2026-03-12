from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.review.compare import FLAT_COMPARE_ALIAS
from src.review.ingestion import canonicalize_history_row
from src.review.performance import DEFAULT_COMPARE_ACCOUNTS


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


def _row_timestamp(row: dict[str, Any]) -> datetime | None:
    candidates = [
        row.get('observed_at'),
        row.get('timestamp'),
        row.get('ts'),
    ]
    summary = row.get('summary') if isinstance(row.get('summary'), dict) else {}
    receipt = row.get('receipt') if isinstance(row.get('receipt'), dict) else {}
    meta = row.get('meta') if isinstance(row.get('meta'), dict) else {}
    candidates.extend([
        summary.get('observed_at'),
        summary.get('generated_at'),
        receipt.get('observed_at'),
        meta.get('generated_at'),
    ])
    for candidate in candidates:
        parsed = _parse_dt(candidate)
        if parsed is not None:
            return parsed
    return None


def aggregate_from_execution_history(
    history_path: str | Path,
    base_metrics: dict[str, dict[str, Any]] | None = None,
    *,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
) -> dict[str, dict[str, Any]]:
    base_metrics = {k: dict(v) for k, v in (base_metrics or {}).items()}
    rows = _load_jsonl(Path(history_path))
    if window_start is not None:
        window_start = window_start.astimezone(UTC)
    if window_end is not None:
        window_end = window_end.astimezone(UTC)
    counts = {alias: 0 for alias in DEFAULT_COMPARE_ACCOUNTS}
    fee_totals = {alias: 0.0 for alias in DEFAULT_COMPARE_ACCOUNTS}
    fee_seen = {alias: False for alias in DEFAULT_COMPARE_ACCOUNTS}
    funding_totals = {alias: 0.0 for alias in DEFAULT_COMPARE_ACCOUNTS}
    funding_seen = {alias: False for alias in DEFAULT_COMPARE_ACCOUNTS}
    latest_pnl = {alias: None for alias in DEFAULT_COMPARE_ACCOUNTS}
    latest_realized = {alias: None for alias in DEFAULT_COMPARE_ACCOUNTS}
    latest_unrealized = {alias: None for alias in DEFAULT_COMPARE_ACCOUNTS}
    latest_equity = {alias: None for alias in DEFAULT_COMPARE_ACCOUNTS}
    latest_equity_end = {alias: None for alias in DEFAULT_COMPARE_ACCOUNTS}
    first_equity = {alias: None for alias in DEFAULT_COMPARE_ACCOUNTS}
    latest_drawdown = {alias: None for alias in DEFAULT_COMPARE_ACCOUNTS}
    exposure_counts = {alias: 0 for alias in DEFAULT_COMPARE_ACCOUNTS}
    earliest_metric_ts = {alias: None for alias in DEFAULT_COMPARE_ACCOUNTS}
    latest_metric_ts = {alias: None for alias in DEFAULT_COMPARE_ACCOUNTS}

    filtered_rows: list[dict[str, Any]] = []
    for row in rows:
        row_ts = _row_timestamp(row)
        if row_ts is not None:
            if window_start is not None and row_ts < window_start:
                continue
            if window_end is not None and row_ts >= window_end:
                continue
        filtered_rows.append(row)

    total_rows = len(filtered_rows)
    for row in filtered_rows:
        row_ts = _row_timestamp(row)
        summary = row.get('summary', {})
        plan_account = summary.get('plan_account')
        plan_action = summary.get('plan_action')
        receipt_accepted = summary.get('receipt_accepted')

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

        canonical_metrics = canonicalize_history_row(row)
        for alias, metric_row in canonical_metrics.items():
            if alias not in counts:
                continue
            fee_usdt = metric_row.get('fee_usdt')
            if fee_usdt is not None:
                fee_totals[alias] += float(fee_usdt)
                fee_seen[alias] = True
            funding_usdt = metric_row.get('funding_usdt')
            if funding_usdt is not None:
                funding_totals[alias] += float(funding_usdt)
                funding_seen[alias] = True
            pnl_usdt = metric_row.get('pnl_usdt')
            if pnl_usdt is not None:
                latest_pnl[alias] = float(pnl_usdt)
            realized_pnl_usdt = metric_row.get('realized_pnl_usdt')
            if realized_pnl_usdt is not None:
                latest_realized[alias] = float(realized_pnl_usdt)
            unrealized_pnl_usdt = metric_row.get('unrealized_pnl_usdt')
            if unrealized_pnl_usdt is not None:
                latest_unrealized[alias] = float(unrealized_pnl_usdt)
            equity_usdt = metric_row.get('equity_usdt')
            if equity_usdt is not None:
                latest_equity[alias] = float(equity_usdt)
                if row_ts is None:
                    if first_equity[alias] is None:
                        first_equity[alias] = float(equity_usdt)
                else:
                    if earliest_metric_ts[alias] is None or row_ts < earliest_metric_ts[alias]:
                        earliest_metric_ts[alias] = row_ts
                        first_equity[alias] = float(equity_usdt)
            equity_end_usdt = metric_row.get('equity_end_usdt')
            if equity_end_usdt is not None:
                if row_ts is None:
                    latest_equity_end[alias] = float(equity_end_usdt)
                    if first_equity[alias] is None:
                        first_equity[alias] = float(equity_end_usdt)
                else:
                    if earliest_metric_ts[alias] is None or row_ts < earliest_metric_ts[alias]:
                        earliest_metric_ts[alias] = row_ts
                        first_equity[alias] = float(equity_end_usdt)
                    if latest_metric_ts[alias] is None or row_ts >= latest_metric_ts[alias]:
                        latest_metric_ts[alias] = row_ts
                        latest_equity_end[alias] = float(equity_end_usdt)
            elif equity_usdt is not None and row_ts is not None:
                if latest_metric_ts[alias] is None or row_ts >= latest_metric_ts[alias]:
                    latest_metric_ts[alias] = row_ts
                    latest_equity_end[alias] = float(equity_usdt)
            max_drawdown_pct = metric_row.get('max_drawdown_pct')
            if max_drawdown_pct is not None:
                latest_drawdown[alias] = float(max_drawdown_pct)

    for alias in DEFAULT_COMPARE_ACCOUNTS:
        existing = base_metrics.setdefault(alias, {})
        existing.setdefault('source', 'aggregated')
        existing['trade_count'] = int(existing.get('trade_count') or 0) + counts[alias]
        if total_rows > 0:
            existing['exposure_time_pct'] = float(existing.get('exposure_time_pct') or 0.0) or round(100.0 * exposure_counts[alias] / total_rows, 2)
        if latest_pnl[alias] is not None and existing.get('pnl_usdt') is None:
            existing['pnl_usdt'] = latest_pnl[alias]
        if latest_realized[alias] is not None and existing.get('realized_pnl_usdt') is None:
            existing['realized_pnl_usdt'] = latest_realized[alias]
        if latest_unrealized[alias] is not None and existing.get('unrealized_pnl_usdt') is None:
            existing['unrealized_pnl_usdt'] = latest_unrealized[alias]
        if latest_equity[alias] is not None and existing.get('equity_usdt') is None:
            existing['equity_usdt'] = latest_equity[alias]
        if latest_equity_end[alias] is not None and existing.get('equity_end_usdt') is None:
            existing['equity_end_usdt'] = latest_equity_end[alias]
        if first_equity[alias] is not None and existing.get('equity_start_usdt') is None:
            existing['equity_start_usdt'] = first_equity[alias]
        if existing.get('equity_change_usdt') is None:
            start = existing.get('equity_start_usdt')
            end = existing.get('equity_end_usdt', existing.get('equity_usdt'))
            if start is not None and end is not None:
                existing['equity_change_usdt'] = float(end) - float(start)
        if latest_drawdown[alias] is not None and existing.get('max_drawdown_pct') is None:
            existing['max_drawdown_pct'] = latest_drawdown[alias]
        if fee_seen[alias]:
            existing['fee_usdt'] = float(existing.get('fee_usdt') or 0.0) + fee_totals[alias]
        if funding_seen[alias]:
            existing['funding_usdt'] = float(existing.get('funding_usdt') or 0.0) + funding_totals[alias]

    if FLAT_COMPARE_ALIAS not in base_metrics:
        base_metrics[FLAT_COMPARE_ALIAS] = {'source': 'aggregated', 'trade_count': 0, 'exposure_time_pct': 0.0}

    return base_metrics
