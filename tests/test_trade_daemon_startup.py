from src.runtime.mode import RuntimeMode
from src.runtime.store import RuntimeStore
from src.runners.trade_daemon import ensure_trade_start_ready
from src.runtime.workflows import WorkflowHooks, WorkflowStepResult


class ReadyHooks(WorkflowHooks):
    def __init__(self):
        self.calls = []

    def verify_startup_capital(self):
        self.calls.append('verify_startup_capital')
        return WorkflowStepResult(name='verify_startup_capital', ok=True, detail='ready')


class NeedsCalibrateHooks(WorkflowHooks):
    def __init__(self):
        self.calls = []

    def verify_startup_capital(self):
        self.calls.append('verify_startup_capital')
        return WorkflowStepResult(name='verify_startup_capital', ok=False, detail='residual_non_usdt=ETH')

    def flatten_all_positions(self):
        self.calls.append('flatten_all_positions')
        return WorkflowStepResult(name='flatten_all_positions', ok=True, detail='no_live_positions')

    def verify_flat(self):
        self.calls.append('verify_flat')
        return WorkflowStepResult(name='verify_flat', ok=True, detail='all_flat')

    def convert_non_usdt_assets(self):
        self.calls.append('convert_non_usdt_assets')
        return WorkflowStepResult(name='convert_non_usdt_assets', ok=True, detail='ETH:submitted')

    def verify_startup_capital_after(self):
        self.calls.append('verify_startup_capital_after')
        return WorkflowStepResult(name='verify_startup_capital', ok=True, detail='ready')

    def verify_startup_capital(self):
        self.calls.append('verify_startup_capital')
        if self.calls.count('verify_startup_capital') == 1:
            return WorkflowStepResult(name='verify_startup_capital', ok=False, detail='residual_non_usdt=ETH')
        return WorkflowStepResult(name='verify_startup_capital', ok=True, detail='ready')

    def reset_bucket_state(self, destructive: bool):
        self.calls.append(f'reset_bucket_state:{destructive}')
        return WorkflowStepResult(name='reset_bucket_state', ok=True, detail=f'destructive={destructive}')


def test_ensure_trade_start_ready_returns_none_when_startup_ready():
    store = RuntimeStore()
    store.set_mode(RuntimeMode.TRADE, reason='daemon_start_trade_mode')
    hooks = ReadyHooks()
    result = ensure_trade_start_ready(settings=object(), runtime_store=store, hooks=hooks)
    assert result is None
    assert hooks.calls == ['verify_startup_capital']
    assert store.get().mode == RuntimeMode.TRADE


def test_ensure_trade_start_ready_runs_calibrate_when_startup_not_ready():
    store = RuntimeStore()
    store.set_mode(RuntimeMode.TRADE, reason='daemon_start_trade_mode')
    hooks = NeedsCalibrateHooks()
    result = ensure_trade_start_ready(settings=object(), runtime_store=store, hooks=hooks)
    assert result is not None
    assert result.workflow == 'calibrate'
    assert result.ended_mode == 'trade'
    assert hooks.calls == [
        'verify_startup_capital',
        'flatten_all_positions',
        'verify_flat',
        'convert_non_usdt_assets',
        'verify_startup_capital',
        'reset_bucket_state:False',
    ]
    assert store.get().mode == RuntimeMode.TRADE
