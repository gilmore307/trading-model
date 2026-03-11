from src.runtime.mode import RuntimeMode
from src.runtime.store import RuntimeStore
from src.runtime.workflows import RuntimeWorkflowRunner, WorkflowHooks


class DummyHooks(WorkflowHooks):
    def __init__(self):
        self.calls = []

    def flatten_all_positions(self):
        self.calls.append('flatten')
        return super().flatten_all_positions()

    def verify_flat(self):
        self.calls.append('verify_flat')
        return super().verify_flat()

    def reset_bucket_state(self, destructive: bool):
        self.calls.append(f'reset_bucket_state:{destructive}')
        return super().reset_bucket_state(destructive)


def test_calibrate_workflow_includes_flatten_verify_reset_and_returns_to_trade():
    store = RuntimeStore()
    hooks = DummyHooks()
    runner = RuntimeWorkflowRunner(runtime_store=store, hooks=hooks)
    result = runner.run(RuntimeMode.CALIBRATE)
    assert hooks.calls == ['flatten', 'verify_flat', 'reset_bucket_state:False']
    assert result.ended_mode == 'trade'
    assert store.get().mode == RuntimeMode.TRADE


def test_reset_workflow_includes_flatten_verify_reset_and_returns_to_develop():
    store = RuntimeStore()
    hooks = DummyHooks()
    runner = RuntimeWorkflowRunner(runtime_store=store, hooks=hooks)
    result = runner.run(RuntimeMode.RESET)
    assert hooks.calls == ['flatten', 'verify_flat', 'reset_bucket_state:True']
    assert result.ended_mode == 'develop'
    assert store.get().mode == RuntimeMode.DEVELOP
