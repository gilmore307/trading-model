from datetime import UTC, datetime

from src.market.hub import MarketDataHub
from src.market.ingestion import BtcPollingIngestor


class FakeExchange:
    def fetch_funding_rate(self, symbol):
        return {'fundingRate': 0.01, 'nextFundingTimestamp': 1000, 'markPrice': None, 'indexPrice': None}

    def fetch_open_interest(self, symbol):
        return {'openInterestValue': 1000}

    def fetch_mark_ohlcv(self, symbol, timeframe='1m', limit=1):
        return [[1000, 0, 0, 0, 101, 0]]

    def fetch_index_ohlcv(self, symbol, timeframe='1m', limit=1):
        return [[1000, 0, 0, 0, 100, 0]]


class FakeClient:
    def __init__(self):
        self.exchange = FakeExchange()


def test_fetch_derivatives_falls_back_to_mark_index_basis():
    ing = BtcPollingIngestor.__new__(BtcPollingIngestor)
    ing.settings = type('S', (), {'ccxt_symbol': lambda self, s: s})()
    ing.hub = MarketDataHub()
    ing.symbol = 'BTC-USDT-SWAP'
    ing.client = FakeClient()
    snap = ing._fetch_derivatives()
    assert snap is not None
    assert snap.basis_pct == 0.01
