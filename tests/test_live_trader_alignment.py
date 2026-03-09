from src.runner.live_trader import (
    exchange_live_position_map,
    local_live_position_map,
    position_alignment_report,
)


def test_local_live_position_map_aggregates_open_positions_by_symbol():
    snapshot = {
        "positions": {
            "meanrev:BTC-USDT-SWAP": [
                {
                    "position_key": "meanrev:BTC-USDT-SWAP",
                    "symbol": "BTC/USDT:USDT",
                    "strategy": "meanrev",
                    "side": "short",
                    "status": "open",
                    "amount": 0.77,
                    "notional_usdt": 100.0,
                },
                {
                    "position_key": "meanrev:BTC-USDT-SWAP",
                    "symbol": "BTC/USDT:USDT",
                    "strategy": "meanrev",
                    "side": "short",
                    "status": "open",
                    "amount": 0.77,
                    "notional_usdt": 100.0,
                },
            ]
        }
    }

    assert local_live_position_map(snapshot) == {
        "BTC/USDT:USDT": {
            "position_keys": ["meanrev:BTC-USDT-SWAP"],
            "strategies": ["meanrev"],
            "count": 2,
            "sides": ["short"],
            "amount": 1.54,
            "notional_usdt": 200.0,
        }
    }


def test_exchange_live_position_map_uses_absolute_contracts():
    exchange_positions = [
        {
            "symbol": "BTC/USDT:USDT",
            "side": "short",
            "contracts": -1.54,
            "hedged": False,
            "info": {"posSide": "net", "pos": "-1.54"},
        }
    ]

    assert exchange_live_position_map(exchange_positions) == {
        "BTC/USDT:USDT": {
            "side": "short",
            "contracts": 1.54,
            "hedged": False,
            "pos_side": "net",
            "raw_pos": "-1.54",
        }
    }


def test_position_alignment_report_ok_when_local_matches_exchange():
    snapshot = {
        "positions": {
            "meanrev:BTC-USDT-SWAP": [
                {
                    "position_key": "meanrev:BTC-USDT-SWAP",
                    "symbol": "BTC/USDT:USDT",
                    "strategy": "meanrev",
                    "side": "short",
                    "status": "open",
                    "amount": 0.77,
                    "notional_usdt": 100.0,
                },
                {
                    "position_key": "meanrev:BTC-USDT-SWAP",
                    "symbol": "BTC/USDT:USDT",
                    "strategy": "meanrev",
                    "side": "short",
                    "status": "open",
                    "amount": 0.77,
                    "notional_usdt": 100.0,
                },
            ]
        }
    }
    exchange_positions = [
        {
            "symbol": "BTC/USDT:USDT",
            "side": "short",
            "contracts": 1.54,
            "hedged": False,
            "info": {"posSide": "net", "pos": "-1.54"},
        }
    ]

    report = position_alignment_report(snapshot, exchange_positions)

    assert report["ok"] is True
    assert report["mismatches"] == []


def test_position_alignment_report_detects_missing_local_position():
    snapshot = {"positions": {}}
    exchange_positions = [
        {
            "symbol": "BTC/USDT:USDT",
            "side": "short",
            "contracts": 1.54,
            "hedged": False,
            "info": {"posSide": "net", "pos": "-1.54"},
        }
    ]

    report = position_alignment_report(snapshot, exchange_positions)

    assert report["ok"] is False
    assert report["mismatches"][0]["type"] == "missing_local_position"


def test_position_alignment_report_detects_side_mismatch():
    snapshot = {
        "positions": {
            "meanrev:BTC-USDT-SWAP": [
                {
                    "position_key": "meanrev:BTC-USDT-SWAP",
                    "symbol": "BTC/USDT:USDT",
                    "strategy": "meanrev",
                    "side": "long",
                    "status": "open",
                    "amount": 1.54,
                    "notional_usdt": 200.0,
                }
            ]
        }
    }
    exchange_positions = [
        {
            "symbol": "BTC/USDT:USDT",
            "side": "short",
            "contracts": 1.54,
            "hedged": False,
            "info": {"posSide": "net", "pos": "-1.54"},
        }
    ]

    report = position_alignment_report(snapshot, exchange_positions)

    assert report["ok"] is False
    assert report["mismatches"][0]["type"] == "side_mismatch"
