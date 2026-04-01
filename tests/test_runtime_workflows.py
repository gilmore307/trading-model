from src.runtime.mode import RuntimeMode
from src.runtime.store import RuntimeStore
from src.runtime.workflows import RuntimeWorkflowRunner, WorkflowHooks, run_calibrate_event, run_review_event, run_strategy_upgrade_event


class DummyHooks(WorkflowHooks):
    def __init__(self):
        self.calls = []

    def run_review(self):
        self.calls.append('run_review')
        return super().run_review()

    def run_test_workflow(self):
        self.calls.append('run_test_workflow')
        return super().run_test_workflow()

    def flatten_all_positions(self):
        self.calls.append('flatten')
        return super().flatten_all_positions()

    def verify_flat(self):
        self.calls.append('verify_flat')
        return super().verify_flat()

    def flatten_all_margin_positions(self):
        self.calls.append('flatten_all_margin_positions')
        return super().flatten_all_margin_positions()

    def verify_margin_flat(self):
        self.calls.append('verify_margin_flat')
        return super().verify_margin_flat()

    def convert_non_usdt_assets(self):
        self.calls.append('convert_non_usdt_assets')
        return super().convert_non_usdt_assets()

    def verify_startup_capital(self):
        self.calls.append('verify_startup_capital')
        return super().verify_startup_capital()

    def reset_bucket_state(self, destructive: bool):
        self.calls.append(f'reset_bucket_state:{destructive}')
        return super().reset_bucket_state(destructive)

    def clear_analysis_history(self):
        self.calls.append('clear_analysis_history')
        return super().clear_analysis_history()


def test_review_workflow_runs_review_without_auto_transition():
    store = RuntimeStore()
    hooks = DummyHooks()
    runner = RuntimeWorkflowRunner(runtime_store=store, hooks=hooks)
    result = runner.run(RuntimeMode.REVIEW)
    assert hooks.calls == ['run_review']
    assert result.ended_mode == 'review'
    assert store.get().mode == RuntimeMode.REVIEW


def test_test_workflow_runs_dedicated_test_actions_and_returns_to_develop():
    store = RuntimeStore()
    hooks = DummyHooks()
    runner = RuntimeWorkflowRunner(runtime_store=store, hooks=hooks)
    result = runner.run(RuntimeMode.TEST)
    assert hooks.calls == ['run_test_workflow']
    assert result.ended_mode == 'develop'
    assert store.get().mode == RuntimeMode.DEVELOP


def test_calibrate_workflow_includes_flatten_margin_convert_verify_reset_without_auto_transition():
    store = RuntimeStore()
    hooks = DummyHooks()
    runner = RuntimeWorkflowRunner(runtime_store=store, hooks=hooks)
    result = runner.run(RuntimeMode.CALIBRATE)
    assert hooks.calls == ['flatten', 'verify_flat', 'flatten_all_margin_positions', 'verify_margin_flat', 'convert_non_usdt_assets', 'verify_startup_capital', 'reset_bucket_state:False']
    assert result.ended_mode == 'calibrate'
    assert store.get().mode == RuntimeMode.CALIBRATE


def test_reset_workflow_includes_flatten_margin_convert_verify_reset_clear_history_and_returns_to_develop():
    store = RuntimeStore()
    hooks = DummyHooks()
    runner = RuntimeWorkflowRunner(runtime_store=store, hooks=hooks)
    result = runner.run(RuntimeMode.RESET)
    assert hooks.calls == ['flatten', 'verify_flat', 'flatten_all_margin_positions', 'verify_margin_flat', 'convert_non_usdt_assets', 'verify_startup_capital', 'reset_bucket_state:True', 'clear_analysis_history']
    assert result.ended_mode == 'develop'
    assert store.get().mode == RuntimeMode.DEVELOP


def test_review_event_runs_without_mode_switching():
    hooks = DummyHooks()
    result = run_review_event(hooks=hooks)
    assert hooks.calls == ['run_review']
    assert result.workflow == 'review_event'
    assert result.started_mode == 'trade'
    assert result.ended_mode == 'trade'


def test_calibrate_event_runs_without_mode_switching():
    hooks = DummyHooks()
    result = run_calibrate_event(hooks=hooks)
    assert hooks.calls == ['flatten', 'verify_flat', 'flatten_all_margin_positions', 'verify_margin_flat', 'convert_non_usdt_assets', 'verify_startup_capital', 'reset_bucket_state:False']
    assert result.workflow == 'calibrate_event'
    assert result.started_mode == 'trade'
    assert result.ended_mode == 'trade'


def test_calibrate_event_supports_destructive_cleanup_variant():
    hooks = DummyHooks()
    result = run_calibrate_event(hooks=hooks, destructive=True)
    assert hooks.calls == ['flatten', 'verify_flat', 'flatten_all_margin_positions', 'verify_margin_flat', 'convert_non_usdt_assets', 'verify_startup_capital', 'reset_bucket_state:True', 'clear_analysis_history']
    assert result.workflow == 'calibrate_event'
    assert result.destructive is True


def test_strategy_upgrade_event_runs_calibrate_and_review_without_mode_switching():
    hooks = DummyHooks()
    payload = run_strategy_upgrade_event(hooks=hooks)
    assert hooks.calls == ['flatten', 'verify_flat', 'flatten_all_margin_positions', 'verify_margin_flat', 'convert_non_usdt_assets', 'verify_startup_capital', 'reset_bucket_state:False', 'run_review']
    assert payload['event'] == 'strategy_upgrade_event'
    assert payload['started_mode'] == 'trade'
    assert payload['ended_mode'] == 'trade'
