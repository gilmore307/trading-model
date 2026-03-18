from src.runtime.mode import RuntimeMode
from src.runtime.store import RuntimeStore
from src.runtime.workflows import RuntimeWorkflowRunner, WorkflowHooks


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

    def convert_non_usdt_assets(self):
        self.calls.append('convert_non_usdt_assets')
        return super().convert_non_usdt_assets()

    def verify_startup_capital(self):
        self.calls.append('verify_startup_capital')
        return super().verify_startup_capital()

    def reset_bucket_state(self, destructive: bool):
        self.calls.append(f'reset_bucket_state:{destructive}')
        return super().reset_bucket_state(destructive)


def test_review_workflow_runs_review_and_returns_to_calibrate():
    store = RuntimeStore()
    hooks = DummyHooks()
    runner = RuntimeWorkflowRunner(runtime_store=store, hooks=hooks)
    result = runner.run(RuntimeMode.REVIEW)
    assert hooks.calls == ['run_review']
    assert result.ended_mode == 'calibrate'
    assert store.get().mode == RuntimeMode.CALIBRATE


def test_test_workflow_runs_dedicated_test_actions_and_returns_to_develop():
    store = RuntimeStore()
    hooks = DummyHooks()
    runner = RuntimeWorkflowRunner(runtime_store=store, hooks=hooks)
    result = runner.run(RuntimeMode.TEST)
    assert hooks.calls == ['run_test_workflow']
    assert result.ended_mode == 'develop'
    assert store.get().mode == RuntimeMode.DEVELOP


def test_calibrate_workflow_includes_flatten_convert_verify_reset_and_returns_to_trade():
    store = RuntimeStore()
    hooks = DummyHooks()
    runner = RuntimeWorkflowRunner(runtime_store=store, hooks=hooks)
    result = runner.run(RuntimeMode.CALIBRATE)
    assert hooks.calls == ['flatten', 'verify_flat', 'convert_non_usdt_assets', 'verify_startup_capital', 'reset_bucket_state:False']
    assert result.ended_mode == 'trade'
    assert store.get().mode == RuntimeMode.TRADE


def test_reset_workflow_includes_flatten_convert_verify_reset_and_returns_to_develop():
    store = RuntimeStore()
    hooks = DummyHooks()
    runner = RuntimeWorkflowRunner(runtime_store=store, hooks=hooks)
    result = runner.run(RuntimeMode.RESET)
    assert hooks.calls == ['flatten', 'verify_flat', 'convert_non_usdt_assets', 'verify_startup_capital', 'reset_bucket_state:True']
    assert result.ended_mode == 'develop'
    assert store.get().mode == RuntimeMode.DEVELOP
