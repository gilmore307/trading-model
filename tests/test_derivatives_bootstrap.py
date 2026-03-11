from datetime import UTC, datetime

from src.market.hub import MarketDataHub
from src.market.ingestion import BtcPollingIngestor
from src.market.models import DerivativesSnapshot


class FakeExchange:
    def fetch_funding_rate_history(self, symbol, limit=60):
        return [
            {'timestamp': 1000, 'fundingRate': 0.01},
            {'timestamp': 2000, 'fundingRate': 0.02},
        ]

    def fetch_open_interest_history(self, symbol, timeframe='5m', limit=60):
        return [
            {'timestamp': 1000, 'openInterest': 100},
            {'timestamp': 2000, 'openInterest': 150},
        ]

    def fetch_mark_ohlcv(self, symbol, timeframe='5m', limit=60):
        return [
            [1000, 0, 0, 0, 101, 0],
            [2000, 0, 0, 0, 103, 0],
        ]

    def fetch_index_ohlcv(self, symbol, timeframe='5m', limit=60):
        return [
            [1000, 0, 0, 0, 100, 0],
            [2000, 0, 0, 0, 100, 0],
        ]


class FakeClient:
    def __init__(self):
        self.exchange = FakeExchange()


def test_bootstrap_derivatives_history_inserts_rows():
    ing = BtcPollingIngestor.__new__(BtcPollingIngestor)
    ing.settings = type('S', (), {'ccxt_symbol': lambda self, s: s})()
    ing.hub = MarketDataHub()
    ing.symbol = 'BTC-USDT-SWAP'
    ing.client = FakeClient()
    ing._bootstrapped_derivatives = False
    inserted = ing.bootstrap_derivatives_history(limit=10)
    snap = ing.hub.snapshot('BTC-USDT-SWAP')
    assert inserted >= 2
    assert len(snap.derivatives_history) >= 2
    assert snap.derivatives_history[-1].open_interest == 150.0
