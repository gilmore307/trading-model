from src.runtime.mode import RuntimeMode
from src.runtime.mode_policy import policy_for_mode
from src.runtime.store import RuntimeStore
from src.runtime.workflow import next_mode_after


def test_mode_policy_semantics_match_project_rules():
    assert policy_for_mode(RuntimeMode.TRADE).allow_strategy_execution is True
    assert policy_for_mode(RuntimeMode.TRADE).force_dry_run is False
    assert policy_for_mode(RuntimeMode.CALIBRATE).allow_normal_routing is False
    assert policy_for_mode(RuntimeMode.CALIBRATE).requires_flatten_workflow is True
    assert policy_for_mode(RuntimeMode.RESET).requires_flatten_workflow is True


def test_runtime_store_changes_mode():
    store = RuntimeStore()
    store.set_mode(RuntimeMode.TRADE, 'manual')
    assert store.get().mode == RuntimeMode.TRADE
    assert store.get().reason == 'manual'


def test_workflow_auto_transitions():
    assert next_mode_after(RuntimeMode.CALIBRATE).to_mode == RuntimeMode.TRADE
    assert next_mode_after(RuntimeMode.RESET).to_mode == RuntimeMode.DEVELOP
    assert next_mode_after(RuntimeMode.TEST).to_mode == RuntimeMode.DEVELOP
