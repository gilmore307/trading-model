from src.runtime.workflows import OkxWorkflowHooks


class FakeAccount:
    def __init__(self, alias):
        self.alias = alias
        self.label = alias


class FakeSettings:
    buffer_capital_usdt = 500.0
    bucket_initial_capital_usdt = 20000.0
    strategies = ['trend']
    symbols = ['BTC-USDT-SWAP']

    def account_for_strategy(self, strategy):
        return FakeAccount('trend')


class FakeBucketStore:
    def reset_bucket(self, account, symbol, capital):
        return type('S', (), {'account': account, 'symbol': symbol, 'capital_usdt': capital})()


class FakeClient:
    def __init__(self, positions=None, summaries=None, margin_exposures=None):
        self._positions = list(positions or [])
        self._summaries = list(summaries or [])
        self._margin_exposures = list(margin_exposures or [])
        self.exit_calls = []

    def all_live_positions(self):
        return list(self._positions)

    def create_exit_order(self, symbol, side, amount):
        self.exit_calls.append((symbol, side, amount))
        return {'order_id': f'exit-{symbol}'}

    def account_balance_summary(self):
        if self._summaries:
            return self._summaries.pop(0)
        return {'usdt_available': 1000.0, 'assets': [{'asset': 'USDT', 'available': 1000.0, 'equity': 1000.0}]}

    def margin_exposure_summary(self):
        return list(self._margin_exposures)

    def non_usdt_assets(self):
        return []


def test_flatten_all_positions_uses_all_live_positions(monkeypatch):
    client = FakeClient(positions=[
        {'symbol': 'BTC/USDT:USDT', 'side': 'long', 'contracts': 1.0},
        {'symbol': 'ETH/USDT:USDT', 'side': 'short', 'contracts': 2.0},
    ])
    monkeypatch.setattr('src.runtime.workflows.OkxClient', lambda settings, account: client)
    hooks = OkxWorkflowHooks(FakeSettings(), bucket_store=FakeBucketStore())
    result = hooks.flatten_all_positions()
    assert result.ok is True
    assert client.exit_calls == [
        ('BTC/USDT:USDT', 'long', 1.0),
        ('ETH/USDT:USDT', 'short', 2.0),
    ]


def test_verify_flat_checks_all_positions(monkeypatch):
    client = FakeClient(positions=[{'symbol': 'OKB/USDT:USDT', 'side': 'long', 'contracts': 0.5}])
    monkeypatch.setattr('src.runtime.workflows.OkxClient', lambda settings, account: client)
    hooks = OkxWorkflowHooks(FakeSettings(), bucket_store=FakeBucketStore())
    result = hooks.verify_flat()
    assert result.ok is False
    assert 'OKB/USDT:USDT' in (result.detail or '')


def test_verify_startup_capital_retries_before_failing(monkeypatch):
    client = FakeClient(summaries=[
        {'usdt_available': 1000.0, 'assets': [{'asset': 'USDT', 'available': 1000.0, 'equity': 1000.0}, {'asset': 'ETH', 'available': 0.2, 'equity': 0.2}]},
        {'usdt_available': 1000.0, 'assets': [{'asset': 'USDT', 'available': 1000.0, 'equity': 1000.0}]},
    ])
    monkeypatch.setattr('src.runtime.workflows.OkxClient', lambda settings, account: client)
    monkeypatch.setattr('src.runtime.workflows.time.sleep', lambda _s: None)
    hooks = OkxWorkflowHooks(FakeSettings(), bucket_store=FakeBucketStore())
    result = hooks.verify_startup_capital()
    assert result.ok is True
