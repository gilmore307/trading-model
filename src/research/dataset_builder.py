from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any
import json

from src.research.labels import build_forward_return_labels
from src.runners.regime_runner import RegimeRunnerOutput
from src.strategies.executors import build_shadow_plans, executor_for


DEFAULT_HORIZONS = {
    'fwd_ret_15m': 3,
    'fwd_ret_1h': 12,
    'fwd_ret_4h': 48,
}


def build_research_row(*, output: RegimeRunnerOutput, prices: list[float] | None = None, index: int | None = None, horizons: dict[str, int] | None = None) -> dict[str, Any]:
    selected_plan = executor_for(output).build_plan(output)
    shadow_plans = build_shadow_plans(output)
    row: dict[str, Any] = {
        'timestamp': output.observed_at.isoformat(),
        'symbol': output.symbol,
        'bg_regime': output.background_4h.get('primary'),
        'bg_confidence': output.background_4h.get('confidence'),
        'primary_regime': output.primary_15m.get('primary'),
        'primary_confidence': output.primary_15m.get('confidence'),
        'override_regime': None if output.override_1m is None else output.override_1m.get('primary'),
        'override_confidence': None if output.override_1m is None else output.override_1m.get('confidence'),
        'final_regime': output.final_decision.get('primary'),
        'final_confidence': output.final_decision.get('confidence'),
        'route_account': output.route_decision.get('account'),
        'route_strategy_family': output.route_decision.get('strategy_family'),
        'route_trade_enabled': output.route_decision.get('trade_enabled'),
        'decision_summary': output.decision_summary,
        'background_features': output.background_features,
        'primary_features': output.primary_features,
        'override_features': output.override_features,
        'executor_regime': selected_plan.regime,
        'executor_action': selected_plan.action,
        'executor_side': selected_plan.side,
        'executor_size': selected_plan.size,
        'executor_reason': selected_plan.reason,
        'executor_score': selected_plan.score,
        'executor_blockers': selected_plan.blockers,
        'executor_signals': selected_plan.signals,
        'executor_subscores': selected_plan.subscores,
        'shadow_plans': shadow_plans,
    }
    if prices is not None and index is not None:
        row.update(build_forward_return_labels(prices, index, horizons or DEFAULT_HORIZONS))
    else:
        for name in (horizons or DEFAULT_HORIZONS):
            row[name] = None
    return row


def write_jsonl(rows: list[dict[str, Any]], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('w', encoding='utf-8') as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + '\n')
    return target
