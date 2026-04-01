from src.runners.process_strategy_upgrade_request import _decide_position_handover


def test_handover_decision_no_open_position():
    decision = _decide_position_handover([], requested_version='v2')
    assert decision['handover_action'] == 'no_open_position'


def test_handover_decision_single_owner_prefers_transfer():
    decision = _decide_position_handover([
        {'position_owner': 'trend', 'route': 'trend', 'size': 1.0},
    ], requested_version='v2')
    assert decision['handover_action'] == 'transfer_ownership'


def test_handover_decision_multiple_owners_prefers_close_and_wait():
    decision = _decide_position_handover([
        {'position_owner': 'trend', 'route': 'trend', 'size': 1.0},
        {'position_owner': 'mean_revert', 'route': 'mean_revert', 'size': 1.0},
    ], requested_version='v2')
    assert decision['handover_action'] == 'close_and_wait'
