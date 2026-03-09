from src.execution.executor import DemoExecutor
from src.risk.manager import RiskManager
from src.runner.live_trader import apply_state_patch, ensure_bucket, position_key
from src.storage.state import StateStore
from src.strategy.breakout import BreakoutStrategy
from src.strategy.meanrev import MeanReversionStrategy
from src.strategy.pullback import PullbackStrategy


def test_breakout_long_signal():
    strategy = BreakoutStrategy(lookback=3)
    candles = [
        [0, 0, 10, 5, 8, 0],
        [1, 0, 11, 6, 9, 0],
        [2, 0, 12, 7, 10, 0],
        [3, 0, 13, 8, 14, 0],
    ]
    signal = strategy.evaluate("BTC-USDT-SWAP", candles)
    assert signal.side == "long"
    assert signal.strategy == "breakout"


def test_pullback_and_meanrev_frameworks_return_named_signals():
    pullback = PullbackStrategy(lookback=3)
    meanrev = MeanReversionStrategy(lookback=4, threshold=0.01)
    candles = [
        [0, 0, 10, 9, 9.5, 0],
        [1, 0, 11, 10, 10.5, 0],
        [2, 0, 12, 11, 11.5, 0],
        [3, 0, 12, 10, 10.8, 0],
        [4, 0, 12, 9, 9.6, 0],
    ]
    assert pullback.evaluate("ETH-USDT-SWAP", candles).strategy == "pullback"
    assert meanrev.evaluate("ETH-USDT-SWAP", candles).strategy == "meanrev"


def test_risk_allows_add_on_same_side_when_bucket_has_capital():
    risk = RiskManager(max_open_positions=2, signal_cooldown_bars=12)
    key = position_key("breakout", "BTC-USDT-SWAP")
    snapshot = {
        "positions": {
            key: [{"status": "open", "side": "long"}],
        },
        "last_signals": {},
        "history": [],
        "buckets": {
            key: {"initial_capital_usdt": 500.0, "available_usdt": 400.0, "allocated_usdt": 100.0},
        },
    }
    decision = risk.allow_entry(snapshot=snapshot, position_key=key, side="long", bar_id=100, notional_usdt=100)
    assert decision.allowed is True


def test_risk_sizes_entry_from_bucket_risk_budget_and_volatility():
    risk = RiskManager(risk_per_trade_fraction=0.01, min_stop_distance_ratio=0.003, atr_lookback=3, stop_atr_multiple=1.5)
    bucket = {
        "initial_capital_usdt": 500.0,
        "available_usdt": 500.0,
        "allocated_usdt": 0.0,
    }
    candles = [
        [0, 0, 102, 99, 100, 0],
        [1, 0, 103, 100, 101, 0],
        [2, 0, 104, 101, 102, 0],
        [3, 0, 105, 102, 103, 0],
    ]
    sizing = risk.plan_entry_size(bucket=bucket, candles=candles, leverage=5)
    assert round(sizing.risk_budget_usdt, 6) == 5.0
    assert sizing.stop_distance_ratio > 0.003
    assert sizing.capped_notional_usdt > 0
    assert round(sizing.margin_required_usdt * sizing.leverage, 8) == round(sizing.capped_notional_usdt, 8)


def test_executor_returns_state_patch_and_runner_applies_it():
    executor = DemoExecutor(armed=False)
    key = position_key("breakout", "BTC-USDT-SWAP")
    snapshot = {"positions": {}, "last_signals": {}, "history": [], "buckets": {}}
    bucket = ensure_bucket(snapshot, key, "breakout", "BTC-USDT-SWAP", 500.0)
    result = executor.submit_entry_signal(
        position_key=key,
        symbol="BTC-USDT-SWAP",
        strategy="breakout",
        side="long",
        reason="breakout_high",
        bar_id=123,
        order_size_usdt=100,
        margin_required_usdt=20,
        leverage=5,
        bucket=bucket,
        existing_positions=[],
    )
    snapshot = apply_state_patch(snapshot, result.state_patch)
    assert result.mode == "dry_run"
    assert snapshot["positions"][key][0]["status"] == "open"
    assert snapshot["positions"][key][0]["venue_order_side"] is None
    assert snapshot["positions"][key][0]["margin_required_usdt"] == 20
    assert snapshot["positions"][key][0]["requested_amount"] is None
    assert snapshot["last_signals"][key]["bar_id"] == 123
    assert snapshot["history"][0]["venue_order_side"] is None
    assert snapshot["history"][0]["margin_required_usdt"] == 20
    assert snapshot["open_positions"] == 1
    assert snapshot["buckets"][key]["available_usdt"] == 480.0


def test_executor_exit_aggregates_contract_amount_not_usdt_notional():
    class FakeClient:
        def __init__(self):
            self.calls = []

        def create_exit_order(self, symbol, position_side, amount):
            self.calls.append({
                "symbol": symbol,
                "position_side": position_side,
                "amount": amount,
            })
            return {
                "order_id": "exit-1",
                "status": "filled",
                "amount": amount,
                "requested_amount": amount,
                "order_side": "buy",
                "ccxt_symbol": symbol,
            }

    client = FakeClient()
    executor = DemoExecutor(armed=True, client=client)
    key = position_key("meanrev", "BTC-USDT-SWAP")
    positions = [
        {"status": "open", "side": "short", "notional_usdt": 100.0, "amount": 0.56},
        {"status": "open", "side": "short", "notional_usdt": 100.0, "amount": 0.56},
        {"status": "open", "side": "short", "notional_usdt": 100.0, "amount": 0.56},
        {"status": "open", "side": "short", "notional_usdt": 100.0, "amount": 0.14},
    ]
    bucket = {
        "initial_capital_usdt": 500.0,
        "available_usdt": 100.0,
        "allocated_usdt": 400.0,
    }

    result = executor.submit_exit_signal(
        position_key=key,
        symbol="BTC/USDT:USDT",
        strategy="meanrev",
        positions=positions,
        reason="no_meanrev|exit_all",
        bar_id=789,
        bucket=bucket,
        exit_side=None,
    )

    assert client.calls[0]["symbol"] == "BTC/USDT:USDT"
    assert client.calls[0]["position_side"] == "short"
    assert abs(client.calls[0]["amount"] - 1.82) < 1e-9
    assert result.submitted is True
    assert abs(result.venue_response["amount"] - 1.82) < 1e-9
    snapshot = apply_state_patch({"positions": {}, "last_signals": {}, "history": [], "buckets": {}}, result.state_patch)
    assert abs(snapshot["positions"][key][0]["exit_requested_amount"] - 1.82) < 1e-9
    assert abs(snapshot["positions"][key][0]["exit_amount"] - 1.82) < 1e-9
    assert snapshot["history"][0]["tracked_amount"] == client.calls[0]["amount"]


def test_executor_exit_releases_bucket_capital():
    executor = DemoExecutor(armed=False)
    key = position_key("meanrev", "SOL-USDT-SWAP")
    positions = [{
        "status": "open",
        "side": "short",
        "notional_usdt": 100.0,
        "amount": 5.0,
    }]
    bucket = {
        "initial_capital_usdt": 500.0,
        "available_usdt": 400.0,
        "allocated_usdt": 100.0,
    }
    result = executor.submit_exit_signal(
        position_key=key,
        symbol="SOL-USDT-SWAP",
        strategy="meanrev",
        positions=positions,
        reason="no_meanrev|exit_short",
        bar_id=456,
        bucket=bucket,
        exit_side=None,
    )
    snapshot = apply_state_patch({"positions": {}, "last_signals": {}, "history": [], "buckets": {}}, result.state_patch)
    assert snapshot["positions"][key][0]["status"] == "closed"
    assert snapshot["buckets"][key]["available_usdt"] == 500.0
    assert snapshot["open_positions"] == 0


def test_state_store_backfills_open_positions_and_buckets(tmp_path):
    store = StateStore(tmp_path / "state.json")
    store.save({
        "positions": {
            "breakout:BTC-USDT-SWAP": [{"status": "open", "side": "long"}],
            "pullback:ETH-USDT-SWAP": [{"status": "closed", "side": "short"}],
        },
        "last_signals": {},
        "history": [],
        "buckets": {
            "breakout:BTC-USDT-SWAP": {"available_usdt": 400.0},
        },
    })
    snapshot = store.load()
    assert snapshot["open_positions"] == 1
    assert snapshot["buckets"]["breakout:BTC-USDT-SWAP"]["available_usdt"] == 400.0


def test_state_store_normalizes_execution_metadata_fields(tmp_path):
    store = StateStore(tmp_path / "state.json")
    store.save({
        "positions": {
            "meanrev:BTC-USDT-SWAP": [{"status": "open", "side": "short", "symbol": "BTC/USDT:USDT", "amount": 0.14, "notional_usdt": 100.0}],
        },
        "last_signals": {},
        "history": [],
        "buckets": {},
    })
    snapshot = store.load()
    pos = snapshot["positions"]["meanrev:BTC-USDT-SWAP"][0]
    assert pos["venue_ccxt_symbol"] == "BTC/USDT:USDT"
    assert pos["requested_amount"] == 0.14
    assert pos["requested_notional_usdt"] == 100.0
    assert pos["exit_requested_amount"] == 0.14
    assert pos["exit_amount"] is None


def test_state_store_migrates_legacy_symbol_only_positions(tmp_path):
    store = StateStore(tmp_path / "state.json")
    (tmp_path / "state.json").write_text(
        '{\n'
        '  "positions": {"BTC-USDT-SWAP": {"status": "open", "side": "long", "notional_usdt": 100}},\n'
        '  "last_signals": {"BTC-USDT-SWAP": {"side": "flat", "bar_id": 1, "reason": "legacy"}},\n'
        '  "history": [{"type": "entry", "symbol": "BTC-USDT-SWAP", "side": "long"}]\n'
        '}'
    )
    snapshot = store.load()
    assert "breakout:BTC-USDT-SWAP" in snapshot["positions"]
    assert isinstance(snapshot["positions"]["breakout:BTC-USDT-SWAP"], list)
    assert "breakout:BTC-USDT-SWAP" in snapshot["last_signals"]
    assert snapshot["history"][0]["position_key"] == "breakout:BTC-USDT-SWAP"
    assert snapshot["buckets"]["breakout:BTC-USDT-SWAP"]["allocated_usdt"] == 100.0
