from src.runtime.bucket_state import BucketStateStore
from src.runtime.workflows import OkxWorkflowHooks


class FakeAccount:
    def __init__(self, alias):
        self.alias = alias


class FakeSettings:
    strategies = ['trend']
    symbols = ['BTC-USDT-SWAP']
    bucket_initial_capital_usdt = 20000.0

    def account_for_strategy(self, strategy):
        return FakeAccount('trend')

    def execution_symbol(self, strategy, symbol):
        return symbol


class FakeClient:
    def __init__(self, settings, account):
        self.account = account

    def current_live_position(self, symbol):
        if symbol == 'BTC-USDT-SWAP':
            return {'side': 'long', 'contracts': 1.5}
        return None

    def create_exit_order(self, symbol, side, amount):
        return {'order_id': 'x1', 'symbol': symbol, 'side': side, 'amount': amount}


def test_okx_workflow_hooks_flatten_verify_and_reset(monkeypatch):
    import src.runtime.workflows as m
    monkeypatch.setattr(m, 'OkxClient', FakeClient)
    hooks = OkxWorkflowHooks(FakeSettings(), bucket_store=BucketStateStore())
    flatten = hooks.flatten_all_positions()
    assert flatten.ok is True
    assert 'trend:BTC-USDT-SWAP:x1' in flatten.detail

    verify = hooks.verify_flat()
    assert verify.ok is False
    assert 'non_flat=' in verify.detail

    reset = hooks.reset_bucket_state(destructive=False)
    assert reset.ok is True
    assert 'trend:BTC-USDT-SWAP:20000.0' in reset.detail
