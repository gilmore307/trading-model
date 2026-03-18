from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import UTC, datetime
from typing import Any

from pathlib import Path
import json

from src.review.aggregator import aggregate_from_execution_history
from src.review.framework import ReviewWindow, build_review_plan
from src.review.performance import build_performance_snapshot


def _row_pnl(row: dict[str, Any]) -> float:
    value = row.get('pnl_usdt')
    if value is not None:
        return float(value)
    realized = row.get('realized_pnl_usdt')
    unrealized = row.get('unrealized_pnl_usdt')
    if realized is not None or unrealized is not None:
        return float(realized or 0.0) + float(unrealized or 0.0)
    return 0.0


def _row_equity_change(row: dict[str, Any]) -> float:
    value = row.get('equity_change_usdt')
    return 0.0 if value is None else float(value)


def _row_funding(row: dict[str, Any]) -> float:
    value = row.get('funding_usdt')
    return 0.0 if value is None else float(value)


@dataclass(slots=True)
class ReviewReport:
    meta: dict[str, Any]
    sections: list[dict[str, Any]]
    compare_snapshot: dict[str, Any] | None
    metrics: dict[str, Any]
    parameter_candidates: dict[str, list[dict[str, Any]]]
    decisions: list[dict[str, Any]]
    notes: list[str]
    executive_summary: dict[str, Any]
    recommended_actions: list[dict[str, Any]]
    narrative_blocks: list[dict[str, Any]]


def _score_row(row: dict[str, Any]) -> tuple[float, float, float, float]:
    pnl = _row_pnl(row)
    equity_change = _row_equity_change(row)
    fee = float(row.get('fee_usdt') or 0.0)
    funding = _row_funding(row)
    return (pnl, equity_change, -fee, funding)


def _build_performance_summary(performance_snapshot: dict[str, Any]) -> dict[str, Any]:
    accounts = performance_snapshot.get('accounts', []) if isinstance(performance_snapshot, dict) else []
    ranked = [
        row for row in accounts
        if isinstance(row, dict) and any(
            row.get(key) is not None
            for key in ('pnl_usdt', 'realized_pnl_usdt', 'unrealized_pnl_usdt', 'equity_change_usdt', 'fee_usdt', 'funding_usdt')
        )
    ]
    ranked.sort(key=_score_row, reverse=True)

    def slim(row: dict[str, Any]) -> dict[str, Any]:
        return {
            'account': row.get('account'),
            'pnl_usdt': row.get('pnl_usdt'),
            'equity_change_usdt': row.get('equity_change_usdt'),
            'fee_usdt': row.get('fee_usdt'),
            'funding_usdt': row.get('funding_usdt'),
            'realized_pnl_usdt': row.get('realized_pnl_usdt'),
            'unrealized_pnl_usdt': row.get('unrealized_pnl_usdt'),
            'equity_end_usdt': row.get('equity_end_usdt'),
            'funding_total_usdt': row.get('funding_total_usdt'),
            'trade_count': row.get('trade_count'),
            'exposure_time_pct': row.get('exposure_time_pct'),
            'source': row.get('source'),
        }

    leaderboard = [slim(row) for row in ranked]
    top = leaderboard[0] if leaderboard else None
    bottom = leaderboard[-1] if len(leaderboard) > 1 else (leaderboard[0] if leaderboard else None)

    highest_fee = None
    fee_rows = [row for row in ranked if row.get('fee_usdt') is not None]
    if fee_rows:
        highest_fee = slim(max(fee_rows, key=lambda row: float(row.get('fee_usdt') or 0.0)))

    highest_exposure = None
    exposure_rows = [row for row in ranked if row.get('exposure_time_pct') is not None]
    if exposure_rows:
        highest_exposure = slim(max(exposure_rows, key=lambda row: float(row.get('exposure_time_pct') or 0.0)))

    router_row = next((row for row in ranked if row.get('account') == 'router_composite'), None)
    non_router = [row for row in ranked if row.get('account') not in {'router_composite', 'flat_compare'}]
    best_strategy = max(non_router, key=_score_row) if non_router else None
    flat_compare = next((row for row in ranked if row.get('account') == 'flat_compare'), None)

    insights: list[str] = []
    if top is not None:
        insights.append(f"top_account:{top['account']}")
    if highest_fee is not None:
        insights.append(f"highest_fee_drag:{highest_fee['account']}")
    if highest_exposure is not None and float(highest_exposure.get('exposure_time_pct') or 0.0) >= 80.0:
        insights.append(f"high_exposure:{highest_exposure['account']}")
    if bottom is not None and _row_pnl(bottom) < 0.0:
        insights.append(f"negative_pnl:{bottom['account']}")
    if router_row is not None and best_strategy is not None:
        router_pnl = _row_pnl(router_row)
        best_pnl = _row_pnl(best_strategy)
        relation = 'outperformed' if router_pnl > best_pnl else 'underperformed' if router_pnl < best_pnl else 'matched'
        insights.append(f"router_vs_best_strategy:{relation}:{best_strategy.get('account')}")
    if router_row is not None and flat_compare is not None:
        router_pnl = _row_pnl(router_row)
        flat_pnl = _row_pnl(flat_compare)
        relation = 'ahead' if router_pnl > flat_pnl else 'behind' if router_pnl < flat_pnl else 'matched'
        insights.append(f"router_vs_flat_compare:{relation}")

    return {
        'leaderboard': leaderboard,
        'top_account': top,
        'bottom_account': bottom,
        'highest_fee_drag_account': highest_fee,
        'highest_exposure_account': highest_exposure,
        'router_vs_best_strategy': None if router_row is None or best_strategy is None else {
            'router_account': 'router_composite',
            'best_strategy_account': best_strategy.get('account'),
            'router_pnl_usdt': _row_pnl(router_row),
            'best_strategy_pnl_usdt': _row_pnl(best_strategy),
        },
        'router_vs_flat_compare': None if router_row is None or flat_compare is None else {
            'router_account': 'router_composite',
            'flat_compare_account': 'flat_compare',
            'router_pnl_usdt': _row_pnl(router_row),
            'flat_compare_pnl_usdt': _row_pnl(flat_compare),
        },
        'insights': insights,
    }


def _load_history_rows(path: str | None) -> list[dict[str, Any]]:
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in p.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def _build_execution_quality_summary(history_rows: list[dict[str, Any]]) -> dict[str, Any]:
    clean = 0
    excluded = 0
    reasons: dict[str, int] = {}
    excluded_pnl_usdt = 0.0
    excluded_rows: list[dict[str, Any]] = []
    for row in history_rows:
        summary = row.get('summary') if isinstance(row.get('summary'), dict) else {}
        eligible = bool(summary.get('strategy_stats_eligible', False))
        reason = str(summary.get('strategy_stats_reason') or ('clean_execution' if eligible else 'unknown'))
        if eligible:
            clean += 1
            continue
        excluded += 1
        reasons[reason] = reasons.get(reason, 0) + 1
        metrics = summary.get('account_metrics') if isinstance(summary.get('account_metrics'), dict) else {}
        account = summary.get('plan_account') or (next(iter(metrics.keys())) if metrics else None)
        pnl = 0.0
        if account in metrics and isinstance(metrics.get(account), dict):
            pnl = _row_pnl(metrics[account])
        excluded_pnl_usdt += pnl
        excluded_rows.append({'account': account, 'reason': reason, 'pnl_usdt': pnl})
    top_excluded_reasons = [
        {'reason': key, 'count': value}
        for key, value in sorted(reasons.items(), key=lambda item: (-item[1], item[0]))
    ]
    return {
        'clean_trade_count': clean,
        'excluded_trade_count': excluded,
        'excluded_pnl_usdt': round(excluded_pnl_usdt, 10),
        'top_excluded_reasons': top_excluded_reasons,
        'excluded_samples': excluded_rows[:20],
        'status': 'ready' if history_rows else 'placeholder',
    }


def _build_execution_quality_section(execution_quality: dict[str, Any]) -> dict[str, Any]:
    items = []
    if execution_quality.get('top_excluded_reasons'):
        items.append({'kind': 'excluded_reasons', 'rows': execution_quality.get('top_excluded_reasons', [])})
    if execution_quality.get('excluded_samples'):
        items.append({'kind': 'excluded_samples', 'rows': execution_quality.get('excluded_samples', [])})
    highlights = []
    if execution_quality.get('excluded_trade_count'):
        highlights.append(f"excluded_trade_count:{execution_quality.get('excluded_trade_count')}")
    if execution_quality.get('excluded_pnl_usdt'):
        highlights.append(f"excluded_pnl_usdt:{execution_quality.get('excluded_pnl_usdt')}")
    return {
        'key': 'execution_quality',
        'title': 'Execution Quality',
        'status': execution_quality.get('status', 'placeholder'),
        'items': items,
        'highlights': highlights,
    }


def _build_account_comparison_section(compare_snapshot: dict[str, Any] | None, performance_summary: dict[str, Any]) -> dict[str, Any]:
    leaderboard = performance_summary.get('leaderboard', []) if isinstance(performance_summary, dict) else []
    compare_rows = [] if compare_snapshot is None else compare_snapshot.get('accounts', []) or []
    items: list[dict[str, Any]] = []
    if leaderboard:
        items.append({'kind': 'leaderboard', 'rows': leaderboard})
    if compare_rows:
        items.append({'kind': 'state_snapshot', 'rows': compare_rows})
    top = performance_summary.get('top_account') if isinstance(performance_summary, dict) else None
    bottom = performance_summary.get('bottom_account') if isinstance(performance_summary, dict) else None
    highlights = []
    if top is not None:
        highlights.append(f"top_account:{top.get('account')}")
    if bottom is not None:
        highlights.append(f"bottom_account:{bottom.get('account')}")
    status = 'ready' if items else 'placeholder'
    return {
        'key': 'account_comparison',
        'title': 'Account Comparison',
        'status': status,
        'items': items,
        'highlights': highlights,
    }


def _build_router_composite_section(compare_snapshot: dict[str, Any] | None, performance_summary: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    highlights = list((compare_snapshot or {}).get('highlights', []))
    vs_best = performance_summary.get('router_vs_best_strategy') if isinstance(performance_summary, dict) else None
    vs_flat = performance_summary.get('router_vs_flat_compare') if isinstance(performance_summary, dict) else None
    if vs_best is not None:
        items.append({'kind': 'router_vs_best_strategy', 'row': vs_best})
    if vs_flat is not None:
        items.append({'kind': 'router_vs_flat_compare', 'row': vs_flat})
    status = 'ready' if items or highlights else 'placeholder'
    return {
        'key': 'router_composite_review',
        'title': 'Router Composite Review',
        'status': status,
        'items': items,
        'highlights': highlights,
    }


def _build_parameter_review_section(
    performance_summary: dict[str, Any],
    auto_candidate_params: list[dict[str, Any]],
    discuss_first_params: list[dict[str, Any]],
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    highest_fee = performance_summary.get('highest_fee_drag_account') if isinstance(performance_summary, dict) else None
    highest_exposure = performance_summary.get('highest_exposure_account') if isinstance(performance_summary, dict) else None
    bottom = performance_summary.get('bottom_account') if isinstance(performance_summary, dict) else None
    insights = performance_summary.get('insights', []) if isinstance(performance_summary, dict) else []

    if highest_fee is not None:
        items.append({
            'kind': 'candidate',
            'name': 'fee_burden_frequency_gate',
            'status': 'candidate',
            'reason': f"highest fee drag observed on {highest_fee.get('account')}",
            'target_account': highest_fee.get('account'),
            'evidence': highest_fee,
        })
        trade_count = float(highest_fee.get('trade_count') or 0.0)
        if trade_count >= 5:
            items.append({
                'kind': 'candidate',
                'name': 'cooldown_seconds',
                'status': 'candidate',
                'reason': f"high fee drag with elevated trade count on {highest_fee.get('account')}",
                'target_account': highest_fee.get('account'),
                'evidence': highest_fee,
            })

    if highest_exposure is not None and float(highest_exposure.get('exposure_time_pct') or 0.0) >= 80.0:
        items.append({
            'kind': 'candidate',
            'name': 'confidence_gate',
            'status': 'candidate',
            'reason': f"exposure stayed elevated on {highest_exposure.get('account')}",
            'target_account': highest_exposure.get('account'),
            'evidence': highest_exposure,
        })

    if bottom is not None:
        pnl = _row_pnl(bottom)
        if pnl < 0.0:
            items.append({
                'kind': 'candidate',
                'name': 'entry_threshold',
                'status': 'candidate',
                'reason': f"negative pnl on lowest ranked account {bottom.get('account')}",
                'target_account': bottom.get('account'),
                'evidence': bottom,
            })
        elif float(bottom.get('trade_count') or 0.0) >= 5:
            items.append({
                'kind': 'candidate',
                'name': 'add_position_threshold',
                'status': 'candidate',
                'reason': f"weak ranking with repeated trading on {bottom.get('account')}",
                'target_account': bottom.get('account'),
                'evidence': bottom,
            })

    for insight in insights:
        if insight.startswith('router_vs_best_strategy:underperformed:'):
            items.append({
                'kind': 'candidate',
                'name': 'router_switch_gating',
                'status': 'discuss_first',
                'reason': insight,
            })
            break

    auto_status_map = {item['name']: item['status'] for item in items if item.get('kind') == 'candidate' and item.get('status') == 'candidate'}
    discuss_status_map = {item['name']: item['status'] for item in items if item.get('kind') == 'candidate' and item.get('status') == 'discuss_first'}

    seeded_auto = []
    for row in auto_candidate_params:
        seeded_auto.append({
            'name': row['name'],
            'status': auto_status_map.get(row['name'], row.get('status', 'pending_data')),
        })

    seeded_discuss = []
    for row in discuss_first_params:
        seeded_discuss.append({
            'name': row['name'],
            'status': discuss_status_map.get(row['name'], row.get('status', 'pending_data')),
        })

    return {
        'key': 'parameter_review',
        'title': 'Parameter Review',
        'status': 'ready' if items else 'placeholder',
        'items': items,
        'seeded_candidates': seeded_auto,
        'seeded_discuss_first': seeded_discuss,
    }


def _build_executive_summary(meta: dict[str, Any], performance_summary: dict[str, Any], parameter_section: dict[str, Any], execution_quality: dict[str, Any]) -> dict[str, Any]:
    top = performance_summary.get('top_account') if isinstance(performance_summary, dict) else None
    bottom = performance_summary.get('bottom_account') if isinstance(performance_summary, dict) else None
    router_vs_best = performance_summary.get('router_vs_best_strategy') if isinstance(performance_summary, dict) else None
    router_vs_flat = performance_summary.get('router_vs_flat_compare') if isinstance(performance_summary, dict) else None
    candidate_count = len(parameter_section.get('items', [])) if isinstance(parameter_section, dict) else 0

    bullets: list[str] = []
    if top is not None:
        bullets.append(f"Top account: {top.get('account')} ({top.get('pnl_usdt')} USDT pnl)")
    if bottom is not None:
        bullets.append(f"Bottom account: {bottom.get('account')} ({bottom.get('pnl_usdt')} USDT pnl)")
    if router_vs_best is not None:
        bullets.append(
            f"Router composite vs best strategy: {router_vs_best.get('router_pnl_usdt')} vs {router_vs_best.get('best_strategy_pnl_usdt')} USDT"
        )
    if router_vs_flat is not None:
        bullets.append(
            f"Router composite vs flat compare: {router_vs_flat.get('router_pnl_usdt')} vs {router_vs_flat.get('flat_compare_pnl_usdt')} USDT"
        )
    if candidate_count:
        bullets.append(f"Parameter candidates flagged: {candidate_count}")
    if execution_quality.get('status') == 'ready':
        bullets.append(
            f"Clean vs excluded trades: {execution_quality.get('clean_trade_count', 0)} clean / {execution_quality.get('excluded_trade_count', 0)} excluded"
        )
        if execution_quality.get('excluded_trade_count', 0):
            bullets.append(f"Excluded execution-impact pnl: {execution_quality.get('excluded_pnl_usdt')} USDT")

    return {
        'label': meta.get('label'),
        'cadence': meta.get('cadence'),
        'window_start': meta.get('window_start'),
        'window_end': meta.get('window_end'),
        'bullets': bullets,
        'status': 'ready' if bullets else 'placeholder',
    }


def _build_recommended_actions(parameter_section: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for item in parameter_section.get('items', []) if isinstance(parameter_section, dict) else []:
        if item.get('kind') != 'candidate':
            continue
        actions.append({
            'title': f"Review {item.get('name')}",
            'priority': 'discuss_first' if item.get('status') == 'discuss_first' else 'candidate',
            'target_account': item.get('target_account'),
            'reason': item.get('reason'),
        })
    return actions


def _build_narrative_blocks(executive_summary: dict[str, Any], sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    if executive_summary.get('bullets'):
        blocks.append({
            'key': 'executive_summary',
            'title': 'Executive Summary',
            'lines': executive_summary['bullets'],
        })
    for section in sections:
        key = section.get('key')
        if key == 'account_comparison' and section.get('status') == 'ready':
            leaderboard = next((item.get('rows') for item in section.get('items', []) if item.get('kind') == 'leaderboard'), [])
            lines = [
                f"{idx + 1}. {row.get('account')} pnl={row.get('pnl_usdt')} fee={row.get('fee_usdt')} exposure={row.get('exposure_time_pct')}"
                for idx, row in enumerate(leaderboard[:3])
            ]
            blocks.append({'key': key, 'title': section.get('title'), 'lines': lines})
        elif key == 'router_composite_review' and section.get('status') == 'ready':
            lines = []
            for item in section.get('items', []):
                row = item.get('row') or {}
                if item.get('kind') == 'router_vs_best_strategy':
                    lines.append(
                        f"Router composite vs best strategy {row.get('best_strategy_account')}: {row.get('router_pnl_usdt')} vs {row.get('best_strategy_pnl_usdt')} USDT"
                    )
                elif item.get('kind') == 'router_vs_flat_compare':
                    lines.append(
                        f"Router composite vs flat compare: {row.get('router_pnl_usdt')} vs {row.get('flat_compare_pnl_usdt')} USDT"
                    )
            blocks.append({'key': key, 'title': section.get('title'), 'lines': lines})
        elif key == 'parameter_review' and section.get('status') == 'ready':
            lines = [
                f"{item.get('name')} [{item.get('status')}]: {item.get('reason')}"
                for item in section.get('items', [])
                if item.get('kind') == 'candidate'
            ]
            blocks.append({'key': key, 'title': section.get('title'), 'lines': lines})
        elif key == 'execution_quality' and section.get('status') == 'ready':
            lines = []
            for item in section.get('items', []):
                if item.get('kind') == 'excluded_reasons':
                    for row in item.get('rows', [])[:5]:
                        lines.append(f"excluded_reason {row.get('reason')}: {row.get('count')}")
                elif item.get('kind') == 'excluded_samples':
                    for row in item.get('rows', [])[:3]:
                        lines.append(f"excluded_sample {row.get('account')}: reason={row.get('reason')} pnl={row.get('pnl_usdt')}")
            blocks.append({'key': key, 'title': section.get('title'), 'lines': lines})
    return blocks


def build_report_scaffold(window: ReviewWindow, compare_snapshot: dict[str, Any] | None = None, metrics_by_account: dict[str, dict[str, Any]] | None = None, history_path: str | None = None) -> dict[str, Any]:
    plan = build_review_plan(window)
    cadence = plan['cadence']

    aggregated_metrics = metrics_by_account
    history_rows: list[dict[str, Any]] = []
    if history_path is not None:
        aggregated_metrics = aggregate_from_execution_history(
            history_path,
            metrics_by_account,
            window_start=window.window_start,
            window_end=window.window_end,
        )
        history_rows = _load_history_rows(history_path)
    performance_snapshot = build_performance_snapshot(aggregated_metrics)
    performance_summary = _build_performance_summary(performance_snapshot)
    execution_quality = _build_execution_quality_summary(history_rows)

    auto_candidate_params = [{'name': name, 'status': 'pending_data'} for name in plan['adjustment_policy']['auto_candidate_params']]
    discuss_first_params = [{'name': name, 'status': 'pending_data'} for name in plan['adjustment_policy']['discuss_first_params']]
    structural_params = [{'name': name, 'status': 'pending_discussion'} for name in plan['adjustment_policy']['structural_params']]

    parameter_section = _build_parameter_review_section(performance_summary, auto_candidate_params, discuss_first_params)
    sections = [
        {
            'key': 'market_regime_summary',
            'title': 'Market Regime Summary',
            'status': 'placeholder',
            'items': [],
        },
        _build_account_comparison_section(compare_snapshot, performance_summary),
        _build_router_composite_section(compare_snapshot, performance_summary),
        _build_execution_quality_section(execution_quality),
        parameter_section,
    ]

    if cadence == 'quarterly':
        sections.append(
            {
                'key': 'structural_review',
                'title': 'Structural Review',
                'status': 'placeholder',
                'items': [],
            }
        )

    meta = {
        'cadence': cadence,
        'label': plan['label'],
        'window_start': plan['window_start'],
        'window_end': plan['window_end'],
        'generated_at': datetime.now(UTC).isoformat(),
        'focus_areas': plan['focus_areas'],
        'adjustment_policy': plan['adjustment_policy'],
    }
    executive_summary = _build_executive_summary(meta, performance_summary, parameter_section, execution_quality)
    recommended_actions = _build_recommended_actions(parameter_section)
    narrative_blocks = _build_narrative_blocks(executive_summary, sections)

    report = ReviewReport(
        meta=meta,
        sections=sections,
        compare_snapshot=compare_snapshot,
        metrics={
            'performance': performance_snapshot,
            'performance_summary': performance_summary,
            'execution_quality': execution_quality,
            'risk': [],
            'fees': [],
            'regime_quality': [],
        },
        parameter_candidates={
            'auto_candidate_params': auto_candidate_params,
            'discuss_first_params': discuss_first_params,
            'structural_params': structural_params,
        },
        decisions=[],
        notes=plan['notes'],
        executive_summary=executive_summary,
        recommended_actions=recommended_actions,
        narrative_blocks=narrative_blocks,
    )
    return asdict(report)
