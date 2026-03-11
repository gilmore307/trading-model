from datetime import UTC, datetime

from src.execution.pipeline import ExecutionCycleResult, ExecutionDecisionTrace
from src.runners.regime_runner import RegimeRunnerOutput
from src.review.compare import build_compare_snapshot
from src.strategies.executors import ExecutionPlan


def test_build_compare_snapshot_marks_selected_strategy_and_owner():
    result = ExecutionCycleResult(
        regime_output=RegimeRunnerOutput(
            observed_at=datetime.now(UTC),
            symbol='BTC-USDT-SWAP',
            background_4h={'primary': 'trend', 'confidence': 0.8, 'reasons': [], 'secondary': [], 'tradable': True},
            primary_15m={'primary': 'trend', 'confidence': 0.8, 'reasons': [], 'secondary': [], 'tradable': True},
            override_1m=None,
            background_features={},
            primary_features={},
            override_features={},
            final_decision={'primary': 'trend', 'confidence': 0.8, 'reasons': [], 'secondary': [], 'tradable': True},
            route_decision={'regime': 'trend', 'account': 'trend', 'strategy_family': 'trend', 'trade_enabled': True, 'allow_reason': 'route_to_trend', 'block_reason': None},
            decision_summary={'regime': 'trend', 'confidence': 0.8, 'tradable': True, 'account': 'trend', 'strategy_family': 'trend', 'trade_enabled': True, 'allow_reason': 'route_to_trend', 'block_reason': None, 'reasons': [], 'secondary': [], 'diagnostics': []},
        ),
        plan=ExecutionPlan(regime='trend', account='trend', action='enter', reason='demo'),
        receipt=None,
        local_position=None,
        verification_position=None,
        reconcile_result=None,
        decision_trace=ExecutionDecisionTrace(mode='trade', mode_allows_routing=True, decision_trade_enabled=True, route_trade_enabled=True, pipeline_trade_enabled=True),
        runtime_state={'mode': 'trade'},
        route_state=None,
        live_positions=[{'account': 'trend', 'symbol': 'BTC-USDT-SWAP', 'status': 'open', 'side': 'long', 'size': 1.0}],
        router_composite={'account': 'router_composite', 'selected_strategy': 'trend', 'position_owner': 'trend', 'switch_action': 'adopt_target_plan', 'position': {'side': 'long'}},
    )
    snapshot = build_compare_snapshot(result)
    trend_row = next(row for row in snapshot['accounts'] if row['account'] == 'trend')
    assert trend_row['selected_by_router'] is True
    assert trend_row['owns_composite_position'] is True
    assert 'router_selected:trend' in snapshot['highlights']
    assert 'composite_owner:trend' in snapshot['highlights']


def test_build_compare_snapshot_flags_selection_owner_divergence():
    result = ExecutionCycleResult(
        regime_output=RegimeRunnerOutput(
            observed_at=datetime.now(UTC),
            symbol='BTC-USDT-SWAP',
            background_4h={'primary': 'trend', 'confidence': 0.8, 'reasons': [], 'secondary': [], 'tradable': True},
            primary_15m={'primary': 'trend', 'confidence': 0.8, 'reasons': [], 'secondary': [], 'tradable': True},
            override_1m=None,
            background_features={},
            primary_features={},
            override_features={},
            final_decision={'primary': 'trend', 'confidence': 0.8, 'reasons': [], 'secondary': [], 'tradable': True},
            route_decision={'regime': 'trend', 'account': 'trend', 'strategy_family': 'trend', 'trade_enabled': True, 'allow_reason': 'route_to_trend', 'block_reason': None},
            decision_summary={'regime': 'trend', 'confidence': 0.8, 'tradable': True, 'account': 'trend', 'strategy_family': 'trend', 'trade_enabled': True, 'allow_reason': 'route_to_trend', 'block_reason': None, 'reasons': [], 'secondary': [], 'diagnostics': []},
        ),
        plan=ExecutionPlan(regime='trend', account='trend', action='hold', reason='keep'),
        receipt=None,
        local_position=None,
        verification_position=None,
        reconcile_result=None,
        decision_trace=ExecutionDecisionTrace(mode='trade', mode_allows_routing=True, decision_trade_enabled=True, route_trade_enabled=True, pipeline_trade_enabled=True),
        runtime_state={'mode': 'trade'},
        route_state=None,
        live_positions=[{'account': 'trend', 'symbol': 'BTC-USDT-SWAP', 'status': 'open', 'side': 'long', 'size': 1.0}],
        router_composite={'account': 'router_composite', 'selected_strategy': 'crowded', 'position_owner': 'trend', 'switch_action': 'keep_current_position', 'position': {'side': 'long'}},
    )
    snapshot = build_compare_snapshot(result)
    assert 'router_selection_differs_from_position_owner' in snapshot['highlights']
