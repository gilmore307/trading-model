from src.routing.switch_policy import SwitchContext, evaluate_switch
from src.state.live_position import LivePosition, LivePositionStatus
from src.strategies.executors import ExecutionPlan


def test_switch_policy_adopts_target_when_no_existing_position():
    decision = evaluate_switch(
        SwitchContext(
            current_position=None,
            current_strategy=None,
            target_strategy='trend',
            target_plan=ExecutionPlan(regime='trend', account='router_composite', action='enter', side='long', size=1.0),
        )
    )
    assert decision.action == 'adopt_target_plan'
    assert decision.reason == 'no_existing_position'


def test_switch_policy_keeps_position_when_target_priority_is_higher():
    current = LivePosition(account='router_composite', symbol='BTC-USDT-SWAP', route='range', status=LivePositionStatus.OPEN, side='long', size=1.0)
    decision = evaluate_switch(
        SwitchContext(
            current_position=current,
            current_strategy='range',
            target_strategy='trend',
            target_plan=ExecutionPlan(regime='trend', account='router_composite', action='enter', side='long', size=1.0),
            target_has_position=False,
        )
    )
    assert decision.action == 'keep_current_position'
    assert decision.reason == 'target_priority_preserves_exposure'


def test_switch_policy_closes_when_target_priority_is_lower():
    current = LivePosition(account='router_composite', symbol='BTC-USDT-SWAP', route='trend', status=LivePositionStatus.OPEN, side='long', size=1.0)
    decision = evaluate_switch(
        SwitchContext(
            current_position=current,
            current_strategy='trend',
            target_strategy='range',
            target_plan=ExecutionPlan(regime='range', account='router_composite', action='enter', side='short', size=1.0),
            target_has_position=False,
        )
    )
    assert decision.action == 'close_and_wait'
    assert decision.reason == 'target_priority_too_low_close_wait'


def test_switch_policy_keeps_when_target_has_same_direction_position():
    current = LivePosition(account='router_composite', symbol='BTC-USDT-SWAP', route='trend', status=LivePositionStatus.OPEN, side='long', size=1.0)
    decision = evaluate_switch(
        SwitchContext(
            current_position=current,
            current_strategy='trend',
            target_strategy='crowded',
            target_plan=ExecutionPlan(regime='crowded', account='router_composite', action='enter', side='short', size=1.0),
            target_has_position=True,
            target_position_side='long',
        )
    )
    assert decision.action == 'keep_current_position'
    assert decision.reason == 'target_same_direction_keep'


def test_switch_policy_closes_when_target_has_opposite_direction_position():
    current = LivePosition(account='router_composite', symbol='BTC-USDT-SWAP', route='trend', status=LivePositionStatus.OPEN, side='long', size=1.0)
    decision = evaluate_switch(
        SwitchContext(
            current_position=current,
            current_strategy='trend',
            target_strategy='crowded',
            target_plan=ExecutionPlan(regime='crowded', account='router_composite', action='enter', side='short', size=1.0),
            target_has_position=True,
            target_position_side='short',
        )
    )
    assert decision.action == 'close_and_wait'
    assert decision.reason == 'target_opposite_direction_close_wait'
