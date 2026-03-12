import pytest

import src.exchange.okx_client as okx_client_module
from src.exchange.okx_client import OkxClientRegistry, account_balance_summary, exit_order_side, normalize_contract_amount


class FakeExchange:
    def __init__(self):
        self.markets = {
            "ETH/USDT:USDT": {"limits": {"amount": {"min": 0.01}}},
            "ETH/USDT": {"limits": {"amount": {"min": 0.01}}},
        }
        self.calls = []
        self.balance = {
            "info": {
                "totalEq": "1500",
                "details": [
                    {"ccy": "USDT", "eqUsd": "1500", "upl": "25.5"},
                ],
            }
        }

    def fetch_ticker(self, symbol):
        return {"last": 2000.0, "bid": 1999.0, "ask": 2001.0}

    def fetch_balance(self):
        return self.balance

    def fetch_positions(self, symbols):
        return []

    def fetch_my_trades(self, symbol, since=None, limit=None):
        return []

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

    def fetch_order_fees(self, execution_symbol, order_id, since_ms=None, side=None, amount=None):
        return None

    def ensure_markets_loaded(self):
        if not getattr(self.exchange, "markets", None):
            self.exchange.load_markets()


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(okx_client_module.time, "sleep", lambda _seconds: None)


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
        "params": {"tdMode": "cross", "posSide": "net", "reduceOnly": True},
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
        "params": {"tdMode": "cross", "posSide": "net", "reduceOnly": True},
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
        "params": {"tdMode": "cross", "posSide": "net", "reduceOnly": True},
    }]
    assert result["requested_amount"] == 1.8199999999
    assert result["amount"] == 1.82


def test_convert_asset_to_usdt_uses_spot_cross_mode():
    from src.exchange.okx_client import OkxClient

    client = DummyOkxClient()
    result = OkxClient.convert_asset_to_usdt(client, "ETH", 1.8199999999)

    assert client.spot_exchange.calls == [{
        "symbol": "ETH/USDT",
        "order_type": "market",
        "side": "sell",
        "amount": 1.82,
        "price": None,
        "params": {"tdMode": "cross"},
    }]
    assert result["symbol"] == "ETH/USDT"
    assert result["amount"] == 1.82
    assert result["account_alias"] == "default"


def test_create_entry_order_uses_windowed_verification_delays(monkeypatch):
    from src.exchange.okx_client import OkxClient

    client = DummyOkxClient()
    snapshots = [
        None,
        {"symbol": "ETH/USDT:USDT", "side": "long", "contracts": 0.05},
    ]

    def fake_snapshot(_exchange, _symbol):
        return snapshots.pop(0)

    monkeypatch.setattr(okx_client_module, "live_position_snapshot", fake_snapshot)
    result = OkxClient.create_entry_order(client, "ETH/USDT:USDT", "long", 100.0)

    assert [row["delay_seconds"] for row in result["verification_attempts"]] == [5.0, 10.0]
    assert result["verified_entry"] is True
    assert result["live_side"] == "long"
    assert result["live_contracts"] == 0.05


def test_create_exit_order_adds_single_doublecheck_when_trade_was_confirmed(monkeypatch):
    from src.exchange.okx_client import OkxClient

    client = DummyOkxClient()
    client.fetch_order_fees = lambda *args, **kwargs: {"fill_count": 1, "fee_usdt": 0.1}
    snapshots = [
        {"symbol": "ETH/USDT:USDT", "side": "long", "contracts": 0.48},
        None,
    ]

    def fake_snapshot(_exchange, _symbol):
        return snapshots.pop(0)

    monkeypatch.setattr(okx_client_module, "live_position_snapshot", fake_snapshot)
    result = OkxClient.create_exit_order(client, "ETH/USDT:USDT", "long", 0.48)

    assert [row["attempt"] for row in result["verification_attempts"]] == [1, "1-doublecheck"]
    assert [row["delay_seconds"] for row in result["verification_attempts"]] == [5.0, 1.5]
    assert all(row["trade_confirmed"] is True for row in result["verification_attempts"])
    assert result["verified_flat"] is True
    assert result["remaining_contracts"] == 0.0


def test_account_balance_summary_extracts_usdt_equity_and_upl():
    summary = account_balance_summary(
        {
            'info': {
                'totalEq': '1500',
                'details': [
                    {'ccy': 'USDT', 'eqUsd': '1500.5', 'upl': '20.25'},
                ],
            }
        },
        account_alias='trend',
        account_label='Trend',
    )
    assert summary['account_alias'] == 'trend'
    assert summary['equity_end_usdt'] == 1500.5
    assert summary['equity_usdt'] == 1500.5
    assert summary['unrealized_pnl_usdt'] == 20.25
    assert summary['pnl_usdt'] == 20.25


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
