from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.review.compare import FLAT_COMPARE_ALIAS
from src.review.ingestion import canonicalize_history_row
from src.review.performance import DEFAULT_COMPARE_ACCOUNTS


ROUND_DIGITS = 10


def _update_drawdown_state(
    *,
    equity_value: float,
    peak_by_alias: dict[str, float | None],
    max_drawdown_by_alias: dict[str, float | None],
    alias: str,
) -> None:
    peak = peak_by_alias[alias]
    if peak is None or equity_value > peak:
        peak_by_alias[alias] = equity_value
        peak = equity_value
    if peak is None or peak <= 0:
        return
    drawdown_pct = ((peak - equity_value) / peak) * 100.0
    current = max_drawdown_by_alias[alias]
    if current is None or drawdown_pct > current:
        max_drawdown_by_alias[alias] = drawdown_pct


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


def _later_metric_candidate(
    *,
    current_ts: datetime | None,
    candidate_ts: datetime | None,
) -> bool:
    if candidate_ts is None:
        return current_ts is None
    if current_ts is None:
        return True
    return candidate_ts >= current_ts


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
    first_funding_total = {alias: None for alias in DEFAULT_COMPARE_ACCOUNTS}
    latest_funding_total = {alias: None for alias in DEFAULT_COMPARE_ACCOUNTS}
    earliest_funding_ts = {alias: None for alias in DEFAULT_COMPARE_ACCOUNTS}
    latest_funding_ts = {alias: None for alias in DEFAULT_COMPARE_ACCOUNTS}
    latest_total_pnl = {alias: None for alias in DEFAULT_COMPARE_ACCOUNTS}
    latest_total_pnl_ts = {alias: None for alias in DEFAULT_COMPARE_ACCOUNTS}
    latest_realized_pnl = {alias: None for alias in DEFAULT_COMPARE_ACCOUNTS}
    latest_realized_pnl_ts = {alias: None for alias in DEFAULT_COMPARE_ACCOUNTS}
    first_unrealized_pnl = {alias: None for alias in DEFAULT_COMPARE_ACCOUNTS}
    first_unrealized_pnl_ts = {alias: None for alias in DEFAULT_COMPARE_ACCOUNTS}
    latest_unrealized_pnl = {alias: None for alias in DEFAULT_COMPARE_ACCOUNTS}
    latest_unrealized_pnl_ts = {alias: None for alias in DEFAULT_COMPARE_ACCOUNTS}
    latest_equity_snapshot = {alias: None for alias in DEFAULT_COMPARE_ACCOUNTS}
    latest_equity_snapshot_ts = {alias: None for alias in DEFAULT_COMPARE_ACCOUNTS}
    latest_equity_end = {alias: None for alias in DEFAULT_COMPARE_ACCOUNTS}
    first_equity_start = {alias: None for alias in DEFAULT_COMPARE_ACCOUNTS}
    max_drawdown_by_curve = {alias: None for alias in DEFAULT_COMPARE_ACCOUNTS}
    equity_peak = {alias: None for alias in DEFAULT_COMPARE_ACCOUNTS}
    latest_drawdown = {alias: None for alias in DEFAULT_COMPARE_ACCOUNTS}
    exposure_counts = {alias: 0 for alias in DEFAULT_COMPARE_ACCOUNTS}
    earliest_metric_ts = {alias: None for alias in DEFAULT_COMPARE_ACCOUNTS}
    latest_metric_ts = {alias: None for alias in DEFAULT_COMPARE_ACCOUNTS}

    filtered_rows: list[tuple[datetime | None, int, dict[str, Any]]] = []
    for idx, row in enumerate(rows):
        row_ts = _row_timestamp(row)
        if row_ts is not None:
            if window_start is not None and row_ts < window_start:
                continue
            if window_end is not None and row_ts >= window_end:
                continue
        filtered_rows.append((row_ts, idx, row))

    filtered_rows.sort(key=lambda item: (item[0] is None, item[0] or datetime.max.replace(tzinfo=UTC), item[1]))

    total_rows = len(filtered_rows)
    for row_ts, _, row in filtered_rows:
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
            funding_total_usdt = metric_row.get('funding_total_usdt')
            if funding_total_usdt is not None:
                if row_ts is None:
                    if first_funding_total[alias] is None:
                        first_funding_total[alias] = float(funding_total_usdt)
                    latest_funding_total[alias] = float(funding_total_usdt)
                else:
                    if earliest_funding_ts[alias] is None or row_ts < earliest_funding_ts[alias]:
                        earliest_funding_ts[alias] = row_ts
                        first_funding_total[alias] = float(funding_total_usdt)
                    if latest_funding_ts[alias] is None or row_ts >= latest_funding_ts[alias]:
                        latest_funding_ts[alias] = row_ts
                        latest_funding_total[alias] = float(funding_total_usdt)
            pnl_usdt = metric_row.get('pnl_usdt')
            if pnl_usdt is not None and _later_metric_candidate(current_ts=latest_total_pnl_ts[alias], candidate_ts=row_ts):
                latest_total_pnl[alias] = float(pnl_usdt)
                latest_total_pnl_ts[alias] = row_ts
            realized_pnl_usdt = metric_row.get('realized_pnl_usdt')
            if realized_pnl_usdt is not None and _later_metric_candidate(current_ts=latest_realized_pnl_ts[alias], candidate_ts=row_ts):
                latest_realized_pnl[alias] = float(realized_pnl_usdt)
                latest_realized_pnl_ts[alias] = row_ts
            unrealized_pnl_usdt = metric_row.get('unrealized_pnl_usdt')
            if unrealized_pnl_usdt is not None:
                unrealized_value = float(unrealized_pnl_usdt)
                if row_ts is None:
                    if first_unrealized_pnl[alias] is None:
                        first_unrealized_pnl[alias] = unrealized_value
                        first_unrealized_pnl_ts[alias] = row_ts
                else:
                    if first_unrealized_pnl_ts[alias] is None or row_ts < first_unrealized_pnl_ts[alias]:
                        first_unrealized_pnl[alias] = unrealized_value
                        first_unrealized_pnl_ts[alias] = row_ts
                if _later_metric_candidate(current_ts=latest_unrealized_pnl_ts[alias], candidate_ts=row_ts):
                    latest_unrealized_pnl[alias] = unrealized_value
                    latest_unrealized_pnl_ts[alias] = row_ts
            equity_start_usdt = metric_row.get('equity_start_usdt')
            if equity_start_usdt is not None:
                if row_ts is None:
                    if first_equity_start[alias] is None:
                        first_equity_start[alias] = float(equity_start_usdt)
                else:
                    if earliest_metric_ts[alias] is None or row_ts < earliest_metric_ts[alias]:
                        earliest_metric_ts[alias] = row_ts
                        first_equity_start[alias] = float(equity_start_usdt)
                _update_drawdown_state(
                    equity_value=float(equity_start_usdt),
                    peak_by_alias=equity_peak,
                    max_drawdown_by_alias=max_drawdown_by_curve,
                    alias=alias,
                )

            equity_usdt = metric_row.get('equity_usdt')
            if equity_usdt is not None:
                if _later_metric_candidate(current_ts=latest_equity_snapshot_ts[alias], candidate_ts=row_ts):
                    latest_equity_snapshot[alias] = float(equity_usdt)
                    latest_equity_snapshot_ts[alias] = row_ts
                if first_equity_start[alias] is None:
                    if row_ts is None:
                        first_equity_start[alias] = float(equity_usdt)
                    elif earliest_metric_ts[alias] is None or row_ts < earliest_metric_ts[alias]:
                        earliest_metric_ts[alias] = row_ts
                        first_equity_start[alias] = float(equity_usdt)
                _update_drawdown_state(
                    equity_value=float(equity_usdt),
                    peak_by_alias=equity_peak,
                    max_drawdown_by_alias=max_drawdown_by_curve,
                    alias=alias,
                )
            equity_end_usdt = metric_row.get('equity_end_usdt')
            if equity_end_usdt is not None:
                if row_ts is None:
                    latest_equity_end[alias] = float(equity_end_usdt)
                    if first_equity_start[alias] is None:
                        first_equity_start[alias] = float(equity_end_usdt)
                else:
                    if first_equity_start[alias] is None and (earliest_metric_ts[alias] is None or row_ts < earliest_metric_ts[alias]):
                        earliest_metric_ts[alias] = row_ts
                        first_equity_start[alias] = float(equity_end_usdt)
                    if latest_metric_ts[alias] is None or row_ts >= latest_metric_ts[alias]:
                        latest_metric_ts[alias] = row_ts
                        latest_equity_end[alias] = float(equity_end_usdt)
                _update_drawdown_state(
                    equity_value=float(equity_end_usdt),
                    peak_by_alias=equity_peak,
                    max_drawdown_by_alias=max_drawdown_by_curve,
                    alias=alias,
                )
            elif equity_usdt is not None and row_ts is not None:
                if latest_metric_ts[alias] is None or row_ts >= latest_metric_ts[alias]:
                    latest_metric_ts[alias] = row_ts
                    latest_equity_end[alias] = float(equity_usdt)
            max_drawdown_pct = metric_row.get('max_drawdown_pct')
            if max_drawdown_pct is not None:
                explicit_value = float(max_drawdown_pct)
                if latest_drawdown[alias] is None or explicit_value > latest_drawdown[alias]:
                    latest_drawdown[alias] = explicit_value

    for alias in DEFAULT_COMPARE_ACCOUNTS:
        existing = base_metrics.setdefault(alias, {})
        existing.setdefault('source', 'aggregated')
        existing['trade_count'] = int(existing.get('trade_count') or 0) + counts[alias]
        if total_rows > 0:
            existing['exposure_time_pct'] = float(existing.get('exposure_time_pct') or 0.0) or round(100.0 * exposure_counts[alias] / total_rows, 2)
        if latest_total_pnl[alias] is not None and existing.get('pnl_usdt') is None:
            existing['pnl_usdt'] = latest_total_pnl[alias]
        if latest_realized_pnl[alias] is not None and existing.get('realized_pnl_usdt') is None:
            existing['realized_pnl_usdt'] = latest_realized_pnl[alias]
        if first_unrealized_pnl[alias] is not None and existing.get('unrealized_pnl_start_usdt') is None:
            existing['unrealized_pnl_start_usdt'] = first_unrealized_pnl[alias]
        if latest_unrealized_pnl[alias] is not None and existing.get('unrealized_pnl_usdt') is None:
            existing['unrealized_pnl_usdt'] = latest_unrealized_pnl[alias]
        if latest_equity_snapshot[alias] is not None and existing.get('equity_usdt') is None:
            existing['equity_usdt'] = latest_equity_snapshot[alias]
        if latest_equity_end[alias] is not None and existing.get('equity_end_usdt') is None:
            existing['equity_end_usdt'] = latest_equity_end[alias]
        if first_equity_start[alias] is not None and existing.get('equity_start_usdt') is None:
            existing['equity_start_usdt'] = first_equity_start[alias]
        if existing.get('equity_change_usdt') is None:
            start = existing.get('equity_start_usdt')
            end = existing.get('equity_end_usdt', existing.get('equity_usdt'))
            if start is not None and end is not None:
                existing['equity_change_usdt'] = float(end) - float(start)
        if existing.get('unrealized_pnl_change_usdt') is None:
            start_unrealized = existing.get('unrealized_pnl_start_usdt')
            end_unrealized = existing.get('unrealized_pnl_usdt')
            if start_unrealized is not None and end_unrealized is not None:
                existing['unrealized_pnl_change_usdt'] = float(end_unrealized) - float(start_unrealized)
        curve_drawdown = max_drawdown_by_curve[alias]
        explicit_drawdown = latest_drawdown[alias]
        chosen_drawdown = None
        if curve_drawdown is not None and explicit_drawdown is not None:
            chosen_drawdown = max(curve_drawdown, explicit_drawdown)
        else:
            chosen_drawdown = curve_drawdown if curve_drawdown is not None else explicit_drawdown
        if chosen_drawdown is not None and existing.get('max_drawdown_pct') is None:
            existing['max_drawdown_pct'] = round(float(chosen_drawdown), 6)
        if fee_seen[alias]:
            existing['fee_usdt'] = round(float(existing.get('fee_usdt') or 0.0) + fee_totals[alias], ROUND_DIGITS)
        if latest_funding_total[alias] is not None:
            existing['funding_total_usdt'] = latest_funding_total[alias]
            if first_funding_total[alias] is not None:
                existing['funding_start_total_usdt'] = first_funding_total[alias]
            if existing.get('funding_usdt') is None:
                start_total = first_funding_total[alias]
                end_total = latest_funding_total[alias]
                if start_total is not None and end_total is not None:
                    existing['funding_usdt'] = round(float(end_total) - float(start_total), ROUND_DIGITS)
        elif funding_seen[alias]:
            existing['funding_usdt'] = round(float(existing.get('funding_usdt') or 0.0) + funding_totals[alias], ROUND_DIGITS)
        if existing.get('realized_pnl_usdt') is None:
            equity_change = existing.get('equity_change_usdt')
            unrealized_change = existing.get('unrealized_pnl_change_usdt')
            if equity_change is not None and unrealized_change is not None:
                funding_component = float(existing.get('funding_usdt') or 0.0)
                existing['realized_pnl_usdt'] = round(float(equity_change) - float(unrealized_change) - funding_component, ROUND_DIGITS)

    if FLAT_COMPARE_ALIAS not in base_metrics:
        base_metrics[FLAT_COMPARE_ALIAS] = {'source': 'aggregated', 'trade_count': 0, 'exposure_time_pct': 0.0}

    return base_metrics
