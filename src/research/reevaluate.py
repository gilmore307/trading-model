from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Any

from src.config.settings import Settings
from src.runners.regime_runner import RegimeRunnerOutput
from src.strategies.executors import CompressionExecutor, CrowdedExecutor, ExecutionPlan, RangeExecutor, ShockExecutor, TrendExecutor


def output_from_research_row(row: dict[str, Any], *, settings: Settings | None = None) -> RegimeRunnerOutput:
    return RegimeRunnerOutput(
        observed_at=datetime.fromisoformat(str(row['timestamp']).replace('Z', '+00:00')),
        symbol=row['symbol'],
        background_4h={'primary': row.get('bg_regime'), 'confidence': row.get('bg_confidence')},
        primary_15m={'primary': row.get('primary_regime'), 'confidence': row.get('primary_confidence')},
        override_1m=None if row.get('override_regime') is None else {'primary': row.get('override_regime'), 'confidence': row.get('override_confidence')},
        background_features=row.get('background_features') or {},
        primary_features=row.get('primary_features') or {},
        override_features=row.get('override_features') or {},
        final_decision={'primary': row.get('final_regime'), 'confidence': row.get('final_confidence')},
        route_decision={'account': row.get('route_account') or row.get('executor_regime'), 'strategy_family': row.get('route_strategy_family'), 'trade_enabled': row.get('route_trade_enabled')},
        decision_summary=row.get('decision_summary') or {},
        settings=settings,
    )


def settings_with_overrides(overrides: dict[str, Any], *, base: Settings | None = None) -> Settings:
    base = base or Settings.load()
    filtered = {k: v for k, v in overrides.items() if hasattr(base, k)}
    return replace(base, **filtered)


def reevaluate_strategy_row(*, row: dict[str, Any], strategy: str, parameter_overrides: dict[str, Any] | None = None, base_settings: Settings | None = None) -> ExecutionPlan:
    settings = settings_with_overrides(parameter_overrides or {}, base=base_settings)
    output = output_from_research_row(row, settings=settings)
    if strategy == 'trend':
        return TrendExecutor().build_plan(output)
    if strategy == 'range':
        return RangeExecutor().build_plan(output)
    if strategy == 'compression':
        return CompressionExecutor().build_plan(output)
    if strategy == 'crowded':
        return CrowdedExecutor().build_plan(output)
    if strategy == 'shock':
        return ShockExecutor().build_plan(output)
    raise NotImplementedError(f'reevaluation hook not yet implemented for strategy={strategy}')
