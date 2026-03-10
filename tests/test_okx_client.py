from src.exchange.okx_client import OkxClientRegistry, exit_order_side, normalize_contract_amount


class FakeExchange:
    def __init__(self):
        self.markets = {
            "ETH/USDT:USDT": {"limits": {"amount": {"min": 0.01}}},
            "ETH/USDT": {"limits": {"amount": {"min": 0.01}}},
        }
        self.calls = []

    def load_markets(self):
        return self.markets

    def market(self, symbol):
        return self.markets[symbol]

    def amount_to_precision(self, symbol, amount):
        return f"{amount:.2f}"

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


class FakeAccount:
    def __init__(self, alias="default", label="OpenClaw1"):
        self.alias = alias
        self.label = label
        self.api_key = f"key-{alias}"
        self.api_secret = f"secret-{alias}"
        self.api_passphrase = f"pass-{alias}"


class FakeSettings:
    okx_demo = True

    def ccxt_symbol(self, raw_symbol: str) -> str:
        return raw_symbol

    def account_for_strategy(self, strategy_name: str):
        mapping = {
            "breakout": FakeAccount("default", "OpenClaw1"),
            "pullback": FakeAccount("openclaw2", "OpenClaw2"),
            "meanrev": FakeAccount("openclaw3", "OpenClaw3"),
        }
        return mapping[strategy_name]


class DummyOkxClient:
    def __init__(self):
        self.settings = FakeSettings()
        self.exchange = FakeExchange()
        self.spot_exchange = FakeExchange()
        self.account_alias = "default"
        self.account_label = "OpenClaw1"

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


def test_normalize_contract_amount_uses_exchange_precision_and_min_amount():
    exchange = FakeExchange()
    assert normalize_contract_amount(exchange, "ETH/USDT:USDT", 1.8199999999) == 1.82


def test_normalize_contract_amount_rejects_amount_below_minimum():
    exchange = FakeExchange()
    try:
        normalize_contract_amount(exchange, "ETH/USDT:USDT", 0.001)
    except RuntimeError as exc:
        assert "below minimum" in str(exc)
    else:
        raise AssertionError("normalize_contract_amount should reject amount below minimum")


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
    assert result["requested_amount"] == 0.48
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
    assert result["requested_amount"] == 0.48
    assert result["amount"] == 0.48


def test_create_exit_order_normalizes_aggregated_amount_before_submit():
    from src.exchange.okx_client import OkxClient

    client = DummyOkxClient()
    result = OkxClient.create_exit_order(client, "ETH/USDT:USDT", "short", 1.8199999999)

    assert client.exchange.calls == [{
        "symbol": "ETH/USDT:USDT",
        "order_type": "market",
        "side": "buy",
        "amount": 1.82,
        "price": None,
        "params": {"tdMode": "cross", "reduceOnly": True},
    }]
    assert result["requested_amount"] == 1.8199999999
    assert result["amount"] == 1.82


def test_convert_asset_to_usdt_uses_spot_cash_mode():
    from src.exchange.okx_client import OkxClient

    client = DummyOkxClient()
    result = OkxClient.convert_asset_to_usdt(client, "ETH", 1.8199999999)

    assert client.spot_exchange.calls == [{
        "symbol": "ETH/USDT",
        "order_type": "market",
        "side": "sell",
        "amount": 1.82,
        "price": None,
        "params": {"tdMode": "cash"},
    }]
    assert result["symbol"] == "ETH/USDT"
    assert result["amount"] == 1.82
    assert result["account_alias"] == "default"


def test_okx_client_registry_reuses_clients_by_account_alias():
    settings = FakeSettings()
    registry = OkxClientRegistry(settings)

    breakout_client = registry.for_strategy("breakout")
    breakout_client_2 = registry.for_strategy("breakout")
    pullback_client = registry.for_strategy("pullback")

    assert breakout_client is breakout_client_2
    assert breakout_client.account_alias == "default"
    assert breakout_client.account_label == "OpenClaw1"
    assert pullback_client.account_alias == "openclaw2"
    assert pullback_client.account_label == "OpenClaw2"
