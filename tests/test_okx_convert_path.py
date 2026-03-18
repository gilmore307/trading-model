from src.exchange.okx_client import OkxClient


class FakeSpotExchange:
    def __init__(self):
        self.calls = []
        self.markets = {'ETH/USDT': {'limits': {'amount': {'min': 0.01}}}}

    def privatePostAssetConvertEstimateQuote(self, params):
        return {'data': [{'quoteId': 'q1', 'rfqSz': params['rfqSz'], 'rfqSzCcy': params['rfqSzCcy']}]}

    def privatePostAssetConvertTrade(self, params):
        return {'data': [{'tradeId': 't1', 'state': 'filled'}]}

    def load_markets(self):
        return self.markets

    def market(self, symbol):
        return self.markets[symbol]

    def amount_to_precision(self, symbol, amount):
        return f'{amount:.2f}'

    def create_order(self, symbol, order_type, side, amount, price, params):
        self.calls.append((symbol, order_type, side, amount, price, params))
        return {'id': 'fallback'}


class FakeClient:
    account_alias = 'trend'
    account_label = 'Trend'

    def __init__(self):
        self.spot_exchange = FakeSpotExchange()


def test_convert_asset_to_usdt_uses_convert_endpoint_when_available():
    result = OkxClient.convert_asset_to_usdt(FakeClient(), 'ETH', 1.23)
    assert result['convert'] is True
    assert result['quote_id'] == 'q1'
    assert result['order_id'] == 't1'
