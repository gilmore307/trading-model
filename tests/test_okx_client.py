from src.exchange.okx_client import exit_order_side


class FakeExchange:
    def __init__(self):
        self.markets = {"ETH/USDT:USDT": {}}
        self.calls = []

    def load_markets(self):
        return self.markets

    def create_order(self, symbol, order_type, side, amount, price, params):
        self.calls.append({
            "symbol": symbol,
            "order_type": order_type,
            "side": side,
            "amount": amount,
            "price": price,
            "params": params,
        })
        return {"id": "order-1", "status": "filled"}


class FakeSettings:
    def ccxt_symbol(self, raw_symbol: str) -> str:
        return raw_symbol


class DummyOkxClient:
    def __init__(self):
        self.settings = FakeSettings()
        self.exchange = FakeExchange()

    def ensure_markets_loaded(self):
        if not getattr(self.exchange, "markets", None):
            self.exchange.load_markets()


def test_exit_order_side_maps_net_long_to_sell_and_net_short_to_buy():
    assert exit_order_side("long") == "sell"
    assert exit_order_side("short") == "buy"


def test_exit_order_side_rejects_unknown_side():
    try:
        exit_order_side("flat")
    except ValueError as exc:
        assert "Unsupported position side" in str(exc)
    else:
        raise AssertionError("exit_order_side should reject unsupported sides")


def test_create_exit_order_uses_reduce_only_sell_for_long():
    from src.exchange.okx_client import OkxClient

    client = DummyOkxClient()
    result = OkxClient.create_exit_order(client, "ETH/USDT:USDT", "long", 0.48)

    assert client.exchange.calls == [{
        "symbol": "ETH/USDT:USDT",
        "order_type": "market",
        "side": "sell",
        "amount": 0.48,
        "price": None,
        "params": {"tdMode": "cross", "reduceOnly": True},
    }]
    assert result["position_side"] == "long"
    assert result["order_side"] == "sell"
    assert result["amount"] == 0.48


def test_create_exit_order_uses_reduce_only_buy_for_short():
    from src.exchange.okx_client import OkxClient

    client = DummyOkxClient()
    result = OkxClient.create_exit_order(client, "ETH/USDT:USDT", "short", 0.48)

    assert client.exchange.calls == [{
        "symbol": "ETH/USDT:USDT",
        "order_type": "market",
        "side": "buy",
        "amount": 0.48,
        "price": None,
        "params": {"tdMode": "cross", "reduceOnly": True},
    }]
    assert result["position_side"] == "short"
    assert result["order_side"] == "buy"
    assert result["amount"] == 0.48
