from src.execution.exchange_snapshot import ExchangeSnapshotProvider


class FakeSettings:
    def strategy_for_account_alias(self, account):
        return 'trend'

    def account_for_strategy(self, strategy):
        return object()

    def execution_symbol(self, strategy, symbol):
        return 'BTC/USDT:USDT'


def test_exchange_snapshot_provider_maps_live_snapshot(monkeypatch):
    class FakeExchange: ...

    class FakeOkx:
        def __init__(self, settings, account):
            self.exchange = FakeExchange()

    def fake_live_position_snapshot(exchange, execution_symbol):
        return {'side': 'long', 'contracts': 2.0}

    import src.execution.exchange_snapshot as m
    monkeypatch.setattr(m, 'OkxClient', FakeOkx)
    monkeypatch.setattr(m, 'live_position_snapshot', fake_live_position_snapshot)

    provider = ExchangeSnapshotProvider(FakeSettings())
    snap = provider.fetch_position('trend', 'BTC-USDT-SWAP')
    assert snap is not None
    assert snap.account == 'trend'
    assert snap.symbol == 'BTC-USDT-SWAP'
    assert snap.side == 'long'
    assert snap.size == 2.0
