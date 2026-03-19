from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import UTC, datetime
from typing import Any

from pathlib import Path
import json

from src.review.aggregator import aggregate_from_execution_history
from src.review.framework import ReviewWindow, build_review_plan
from src.review.performance import build_performance_snapshot
from src.routing.router import REGIME_ACCOUNT_MAP


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


def _build_regime_local_summary(history_rows: list[dict[str, Any]]) -> dict[str, Any]:
    buckets: dict[str, dict[str, Any]] = {}
    for row in history_rows:
        summary = row.get('summary') if isinstance(row.get('summary'), dict) else row
        regime = str(summary.get('regime') or summary.get('final_regime') or 'unknown')
        route_family = str(summary.get('route_strategy_family') or 'none')
        eligible = bool(summary.get('strategy_stats_eligible', False))
        account_metrics = summary.get('account_metrics') if isinstance(summary.get('account_metrics'), dict) else {}
        plan_account = summary.get('plan_account') or summary.get('route_account') or (next(iter(account_metrics.keys())) if account_metrics else None)
        pnl = 0.0
        if plan_account in account_metrics and isinstance(account_metrics.get(plan_account), dict):
            pnl = _row_pnl(account_metrics[plan_account])
        bucket = buckets.setdefault(regime, {
            'regime': regime,
            'total_cycles': 0,
            'clean_cycles': 0,
            'excluded_cycles': 0,
            'clean_pnl_usdt': 0.0,
            'excluded_pnl_usdt': 0.0,
            'route_families': {},
        })
        bucket['total_cycles'] += 1
        bucket['route_families'][route_family] = bucket['route_families'].get(route_family, 0) + 1
        if eligible:
            bucket['clean_cycles'] += 1
            bucket['clean_pnl_usdt'] = round(float(bucket['clean_pnl_usdt']) + pnl, 10)
        else:
            bucket['excluded_cycles'] += 1
            bucket['excluded_pnl_usdt'] = round(float(bucket['excluded_pnl_usdt']) + pnl, 10)
    rows = []
    for regime, bucket in buckets.items():
        dominant_route = None
        if bucket['route_families']:
            dominant_route = sorted(bucket['route_families'].items(), key=lambda item: (-item[1], item[0]))[0][0]
        rows.append({
            'regime': regime,
            'total_cycles': bucket['total_cycles'],
            'clean_cycles': bucket['clean_cycles'],
            'excluded_cycles': bucket['excluded_cycles'],
            'clean_pnl_usdt': bucket['clean_pnl_usdt'],
            'excluded_pnl_usdt': bucket['excluded_pnl_usdt'],
            'dominant_route_family': dominant_route,
            'route_families': bucket['route_families'],
        })
    rows.sort(key=lambda item: (-int(item['total_cycles']), item['regime']))
    return {
        'rows': rows,
        'status': 'ready' if rows else 'placeholder',
    }


def _build_overlap_summary(history_rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for row in history_rows:
        feature_snapshot = row.get('feature_snapshot') if isinstance(row.get('feature_snapshot'), dict) else {}
        final_regime = row.get('final_regime') or ((row.get('summary') or {}).get('regime') if isinstance(row.get('summary'), dict) else None)
        primary = feature_snapshot.get('primary_15m') if isinstance(feature_snapshot.get('primary_15m'), dict) else {}
        scores = primary.get('scores') if isinstance(primary.get('scores'), dict) else {}
        if not scores:
            continue
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        top_name, top_score = ranked[0]
        second_name, second_score = ranked[1] if len(ranked) > 1 else (None, 0.0)
        gap = round(float(top_score) - float(second_score), 10)
        if gap > 0.15:
            continue
        rows.append({
            'final_regime': final_regime or top_name,
            'top_regime': top_name,
            'top_score': top_score,
            'runner_up_regime': second_name,
            'runner_up_score': second_score,
            'score_gap': gap,
        })
    rows.sort(key=lambda item: (item['score_gap'], str(item['final_regime'])))
    return {
        'rows': rows[:50],
        'status': 'ready' if rows else 'placeholder',
    }


def _build_mapping_validity_summary(history_rows: list[dict[str, Any]]) -> dict[str, Any]:
    expected_map = {str(regime.value): account for regime, account in REGIME_ACCOUNT_MAP.items()}
    buckets: dict[str, dict[str, Any]] = {}
    for row in history_rows:
        summary = row.get('summary') if isinstance(row.get('summary'), dict) else row
        regime = str(summary.get('regime') or summary.get('final_regime') or 'unknown')
        route_account = summary.get('route_account') or summary.get('plan_account')
        expected_account = expected_map.get(regime)
        bucket = buckets.setdefault(regime, {
            'regime': regime,
            'expected_account': expected_account,
            'total_cycles': 0,
            'matched_cycles': 0,
            'routed_none_cycles': 0,
            'route_counts': {},
        })
        bucket['total_cycles'] += 1
        route_key = 'none' if route_account is None else str(route_account)
        bucket['route_counts'][route_key] = bucket['route_counts'].get(route_key, 0) + 1
        if route_account is None:
            bucket['routed_none_cycles'] += 1
        if route_account == expected_account:
            bucket['matched_cycles'] += 1
    rows = []
    for regime, bucket in buckets.items():
        total = int(bucket['total_cycles'])
        matched = int(bucket['matched_cycles'])
        match_rate = 0.0 if total <= 0 else round((matched / total) * 100.0, 4)
        dominant_route = sorted(bucket['route_counts'].items(), key=lambda item: (-item[1], item[0]))[0][0] if bucket['route_counts'] else None
        rows.append({
            'regime': regime,
            'expected_account': bucket['expected_account'],
            'dominant_route': dominant_route,
            'total_cycles': total,
            'matched_cycles': matched,
            'match_rate_pct': match_rate,
            'routed_none_cycles': int(bucket['routed_none_cycles']),
            'route_counts': bucket['route_counts'],
        })
    rows.sort(key=lambda item: (-int(item['total_cycles']), item['regime']))
    return {
        'rows': rows,
        'status': 'ready' if rows else 'placeholder',
    }


def _build_strategy_activity_summary(history_rows: list[dict[str, Any]]) -> dict[str, Any]:
    buckets: dict[str, dict[str, Any]] = {}
    matrix: dict[str, dict[str, dict[str, int]]] = {}
    for row in history_rows:
        shadow_plans = row.get('shadow_plans') if isinstance(row.get('shadow_plans'), dict) else {}
        if not shadow_plans:
            continue
        final_regime = row.get('final_regime') or ((row.get('summary') or {}).get('regime') if isinstance(row.get('summary'), dict) else None)
        regime_key = str(final_regime or 'unknown')
        for strategy_name, plan in shadow_plans.items():
            if not isinstance(plan, dict):
                continue
            bucket = buckets.setdefault(str(strategy_name), {
                'strategy_name': str(strategy_name),
                'total_cycles': 0,
                'watch_count': 0,
                'arm_count': 0,
                'enter_count': 0,
                'by_regime': {},
            })
            bucket['total_cycles'] += 1
            action = str(plan.get('action') or 'hold')
            if action in {'watch', 'hold'}:
                bucket['watch_count'] += 1
            elif action == 'arm':
                bucket['arm_count'] += 1
            elif action == 'enter':
                bucket['enter_count'] += 1
            regime_bucket = bucket['by_regime'].setdefault(regime_key, {'watch': 0, 'arm': 0, 'enter': 0})
            matrix_bucket = matrix.setdefault(str(strategy_name), {}).setdefault(regime_key, {'watch': 0, 'arm': 0, 'enter': 0})
            if action in {'watch', 'hold'}:
                regime_bucket['watch'] += 1
                matrix_bucket['watch'] += 1
            elif action == 'arm':
                regime_bucket['arm'] += 1
                matrix_bucket['arm'] += 1
            elif action == 'enter':
                regime_bucket['enter'] += 1
                matrix_bucket['enter'] += 1
    rows = []
    for strategy_name, bucket in buckets.items():
        rows.append({
            'strategy_name': strategy_name,
            'total_cycles': bucket['total_cycles'],
            'watch_count': bucket['watch_count'],
            'arm_count': bucket['arm_count'],
            'enter_count': bucket['enter_count'],
            'activity_rate_pct': 0.0 if bucket['total_cycles'] <= 0 else round(((bucket['arm_count'] + bucket['enter_count']) / bucket['total_cycles']) * 100.0, 4),
            'by_regime': bucket['by_regime'],
        })
    rows.sort(key=lambda item: (-int(item['enter_count']), -int(item['arm_count']), item['strategy_name']))
    return {
        'rows': rows,
        'matrix': matrix,
        'status': 'ready' if rows else 'placeholder',
    }


def _build_shadow_decision_summary(history_rows: list[dict[str, Any]]) -> dict[str, Any]:
    buckets: dict[str, dict[str, Any]] = {}
    for row in history_rows:
        shadow_plans = row.get('shadow_plans') if isinstance(row.get('shadow_plans'), dict) else {}
        if not shadow_plans:
            continue
        summary = row.get('summary') if isinstance(row.get('summary'), dict) else row
        regime = str(summary.get('regime') or row.get('final_regime') or 'unknown')
        selected_family = str(summary.get('route_strategy_family') or 'none')
        bucket = buckets.setdefault(regime, {
            'regime': regime,
            'selected_family': selected_family,
            'enter_counts': {},
            'arm_counts': {},
            'total_cycles': 0,
        })
        bucket['total_cycles'] += 1
        for strategy_name, plan in shadow_plans.items():
            if not isinstance(plan, dict):
                continue
            action = str(plan.get('action') or 'hold')
            if action == 'enter':
                bucket['enter_counts'][strategy_name] = bucket['enter_counts'].get(strategy_name, 0) + 1
            elif action == 'arm':
                bucket['arm_counts'][strategy_name] = bucket['arm_counts'].get(strategy_name, 0) + 1
    rows = []
    for regime, bucket in buckets.items():
        def _top(counter: dict[str, int]) -> list[dict[str, Any]]:
            return [
                {'strategy_name': name, 'count': count}
                for name, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:5]
            ]
        enter_top = _top(bucket['enter_counts'])
        arm_top = _top(bucket['arm_counts'])
        rows.append({
            'regime': regime,
            'selected_family': bucket['selected_family'],
            'total_cycles': bucket['total_cycles'],
            'enter_top': enter_top,
            'arm_top': arm_top,
            'selected_family_enter_count': bucket['enter_counts'].get(bucket['selected_family'], 0),
            'selected_family_arm_count': bucket['arm_counts'].get(bucket['selected_family'], 0),
        })
    rows.sort(key=lambda item: (-int(item['total_cycles']), item['regime']))
    return {
        'rows': rows,
        'status': 'ready' if rows else 'placeholder',
    }


def _build_execution_quality_summary(history_rows: list[dict[str, Any]]) -> dict[str, Any]:
    clean = 0
    excluded = 0
    reasons: dict[str, int] = {}
    excluded_pnl_usdt = 0.0
    excluded_rows: list[dict[str, Any]] = []
    anomaly_groups: dict[str, dict[str, Any]] = {}
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
        sample = {'account': account, 'reason': reason, 'pnl_usdt': pnl}
        excluded_rows.append(sample)
        group = anomaly_groups.setdefault(reason, {'reason': reason, 'count': 0, 'pnl_usdt': 0.0, 'accounts': [], 'samples': []})
        group['count'] += 1
        group['pnl_usdt'] = round(float(group['pnl_usdt']) + pnl, 10)
        if account is not None and account not in group['accounts']:
            group['accounts'].append(account)
        if len(group['samples']) < 5:
            group['samples'].append(sample)
    top_excluded_reasons = [
        {'reason': key, 'count': value}
        for key, value in sorted(reasons.items(), key=lambda item: (-item[1], item[0]))
    ]
    anomaly_breakdown = sorted(anomaly_groups.values(), key=lambda item: (-int(item['count']), str(item['reason'])))
    return {
        'clean_trade_count': clean,
        'excluded_trade_count': excluded,
        'excluded_pnl_usdt': round(excluded_pnl_usdt, 10),
        'top_excluded_reasons': top_excluded_reasons,
        'excluded_samples': excluded_rows[:20],
        'anomaly_breakdown': anomaly_breakdown,
        'status': 'ready' if history_rows else 'placeholder',
    }


def _build_regime_local_section(regime_local: dict[str, Any]) -> dict[str, Any]:
    items = []
    rows = regime_local.get('rows', []) if isinstance(regime_local, dict) else []
    if rows:
        items.append({'kind': 'regime_rows', 'rows': rows})
    highlights = []
    for row in rows[:5]:
        highlights.append(f"{row.get('regime')}:clean={row.get('clean_cycles')}/excluded={row.get('excluded_cycles')}")
    return {
        'key': 'regime_local_review',
        'title': 'Regime-Local Review',
        'status': regime_local.get('status', 'placeholder'),
        'items': items,
        'highlights': highlights,
    }


def _build_overlap_section(overlap: dict[str, Any]) -> dict[str, Any]:
    rows = overlap.get('rows', []) if isinstance(overlap, dict) else []
    items = [{'kind': 'overlap_rows', 'rows': rows}] if rows else []
    highlights = []
    for row in rows[:6]:
        highlights.append(f"{row.get('final_regime')}: top={row.get('top_regime')} runner_up={row.get('runner_up_regime')} gap={row.get('score_gap')}")
    return {
        'key': 'overlap_review',
        'title': 'Regime Overlap Review',
        'status': overlap.get('status', 'placeholder'),
        'items': items,
        'highlights': highlights,
    }


def _build_mapping_validity_section(mapping_validity: dict[str, Any]) -> dict[str, Any]:
    rows = mapping_validity.get('rows', []) if isinstance(mapping_validity, dict) else []
    items = [{'kind': 'mapping_rows', 'rows': rows}] if rows else []
    highlights = []
    for row in rows[:6]:
        highlights.append(f"{row.get('regime')}:expected={row.get('expected_account')} dominant={row.get('dominant_route')} match={row.get('match_rate_pct')}%")
    return {
        'key': 'mapping_validity_review',
        'title': 'Mapping Validity Review',
        'status': mapping_validity.get('status', 'placeholder'),
        'items': items,
        'highlights': highlights,
    }


def _build_strategy_activity_section(activity: dict[str, Any]) -> dict[str, Any]:
    rows = activity.get('rows', []) if isinstance(activity, dict) else []
    items = [{'kind': 'activity_rows', 'rows': rows}] if rows else []
    highlights = []
    for row in rows[:6]:
        highlights.append(f"{row.get('strategy_name')}: enter={row.get('enter_count')} arm={row.get('arm_count')} watch={row.get('watch_count')} activity={row.get('activity_rate_pct')}%")
    return {
        'key': 'strategy_activity_review',
        'title': 'Strategy Activity Review',
        'status': activity.get('status', 'placeholder'),
        'items': items,
        'highlights': highlights,
    }


def _build_shadow_decision_section(shadow: dict[str, Any]) -> dict[str, Any]:
    rows = shadow.get('rows', []) if isinstance(shadow, dict) else []
    items = [{'kind': 'shadow_rows', 'rows': rows}] if rows else []
    highlights = []
    for row in rows[:6]:
        enter_top = row.get('enter_top') or []
        leader = enter_top[0]['strategy_name'] if enter_top else 'none'
        highlights.append(f"{row.get('regime')}: selected={row.get('selected_family')} top_enter={leader}")
    return {
        'key': 'shadow_decision_review',
        'title': 'Shadow Decision Review',
        'status': shadow.get('status', 'placeholder'),
        'items': items,
        'highlights': highlights,
    }


def _build_execution_quality_section(execution_quality: dict[str, Any]) -> dict[str, Any]:
    items = []
    if execution_quality.get('anomaly_breakdown'):
        items.append({'kind': 'anomaly_breakdown', 'rows': execution_quality.get('anomaly_breakdown', [])})
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
                if item.get('kind') == 'anomaly_breakdown':
                    for row in item.get('rows', [])[:5]:
                        lines.append(
                            f"anomaly {row.get('reason')}: count={row.get('count')} pnl={row.get('pnl_usdt')} accounts={','.join(row.get('accounts', []))}"
                        )
                elif item.get('kind') == 'excluded_reasons':
                    for row in item.get('rows', [])[:5]:
                        lines.append(f"excluded_reason {row.get('reason')}: {row.get('count')}")
                elif item.get('kind') == 'excluded_samples':
                    for row in item.get('rows', [])[:3]:
                        lines.append(f"excluded_sample {row.get('account')}: reason={row.get('reason')} pnl={row.get('pnl_usdt')}")
            blocks.append({'key': key, 'title': section.get('title'), 'lines': lines})
        elif key == 'regime_local_review' and section.get('status') == 'ready':
            lines = []
            for item in section.get('items', []):
                if item.get('kind') == 'regime_rows':
                    for row in item.get('rows', [])[:6]:
                        lines.append(
                            f"regime {row.get('regime')}: cycles={row.get('total_cycles')} clean={row.get('clean_cycles')} excluded={row.get('excluded_cycles')} clean_pnl={row.get('clean_pnl_usdt')} dominant_route={row.get('dominant_route_family')}"
                        )
            blocks.append({'key': key, 'title': section.get('title'), 'lines': lines})
        elif key == 'mapping_validity_review' and section.get('status') == 'ready':
            lines = []
            for item in section.get('items', []):
                if item.get('kind') == 'mapping_rows':
                    for row in item.get('rows', [])[:6]:
                        lines.append(
                            f"mapping {row.get('regime')}: expected={row.get('expected_account')} dominant={row.get('dominant_route')} matched={row.get('matched_cycles')}/{row.get('total_cycles')} ({row.get('match_rate_pct')}%)"
                        )
            blocks.append({'key': key, 'title': section.get('title'), 'lines': lines})
        elif key == 'overlap_review' and section.get('status') == 'ready':
            lines = []
            for item in section.get('items', []):
                if item.get('kind') == 'overlap_rows':
                    for row in item.get('rows', [])[:6]:
                        lines.append(
                            f"overlap {row.get('final_regime')}: top={row.get('top_regime')}({row.get('top_score')}) runner_up={row.get('runner_up_regime')}({row.get('runner_up_score')}) gap={row.get('score_gap')}"
                        )
            blocks.append({'key': key, 'title': section.get('title'), 'lines': lines})
        elif key == 'strategy_activity_review' and section.get('status') == 'ready':
            lines = []
            for item in section.get('items', []):
                if item.get('kind') == 'activity_rows':
                    for row in item.get('rows', [])[:6]:
                        lines.append(
                            f"activity {row.get('strategy_name')}: enter={row.get('enter_count')} arm={row.get('arm_count')} watch={row.get('watch_count')} activity={row.get('activity_rate_pct')}%"
                        )
            blocks.append({'key': key, 'title': section.get('title'), 'lines': lines})
        elif key == 'shadow_decision_review' and section.get('status') == 'ready':
            lines = []
            for item in section.get('items', []):
                if item.get('kind') == 'shadow_rows':
                    for row in item.get('rows', [])[:6]:
                        enter_top = ','.join(f"{x.get('strategy_name')}:{x.get('count')}" for x in row.get('enter_top', []))
                        arm_top = ','.join(f"{x.get('strategy_name')}:{x.get('count')}" for x in row.get('arm_top', []))
                        lines.append(
                            f"shadow {row.get('regime')}: selected={row.get('selected_family')} enter_top=[{enter_top}] arm_top=[{arm_top}]"
                        )
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
    regime_local = _build_regime_local_summary(history_rows)
    mapping_validity = _build_mapping_validity_summary(history_rows)
    overlap = _build_overlap_summary(history_rows)
    strategy_activity = _build_strategy_activity_summary(history_rows)
    shadow_decision = _build_shadow_decision_summary(history_rows)
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
        _build_regime_local_section(regime_local),
        _build_mapping_validity_section(mapping_validity),
        _build_overlap_section(overlap),
        _build_strategy_activity_section(strategy_activity),
        _build_shadow_decision_section(shadow_decision),
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
            'regime_local': regime_local,
            'mapping_validity': mapping_validity,
            'overlap': overlap,
            'strategy_activity': strategy_activity,
            'shadow_decision': shadow_decision,
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
