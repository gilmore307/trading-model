from src.runner.live_trader import (
    account_symbol_key,
    exchange_live_position_map,
    local_live_position_map,
    position_alignment_report,
)


def test_account_symbol_key_namespaces_symbol_by_account():
    assert account_symbol_key("default", "BTC/USDT:USDT") == "default::BTC/USDT:USDT"
    assert account_symbol_key("openclaw2", "BTC/USDT:USDT") == "openclaw2::BTC/USDT:USDT"


def test_local_live_position_map_aggregates_open_positions_by_account_and_symbol():
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
                    "account_alias": "openclaw3",
                },
                {
                    "position_key": "meanrev:BTC-USDT-SWAP",
                    "symbol": "BTC/USDT:USDT",
                    "strategy": "meanrev",
                    "side": "short",
                    "status": "open",
                    "amount": 0.77,
                    "notional_usdt": 100.0,
                    "account_alias": "openclaw3",
                },
            ]
        }
    }

    assert local_live_position_map(snapshot) == {
        "openclaw3::BTC/USDT:USDT": {
            "account_alias": "openclaw3",
            "symbol": "BTC/USDT:USDT",
            "position_keys": ["meanrev:BTC-USDT-SWAP"],
            "strategies": ["meanrev"],
            "count": 2,
            "sides": ["short"],
            "amount": 1.54,
            "notional_usdt": 200.0,
        }
    }


def test_exchange_live_position_map_uses_absolute_contracts_and_account_namespace():
    exchange_positions = [
        {
            "symbol": "BTC/USDT:USDT",
            "side": "short",
            "contracts": -1.54,
            "hedged": False,
            "info": {"posSide": "net", "pos": "-1.54"},
        }
    ]

    assert exchange_live_position_map(exchange_positions, "openclaw3") == {
        "openclaw3::BTC/USDT:USDT": {
            "account_alias": "openclaw3",
            "symbol": "BTC/USDT:USDT",
            "side": "short",
            "contracts": 1.54,
            "hedged": False,
            "pos_side": "net",
            "raw_pos": "-1.54",
        }
    }


def test_position_alignment_report_ok_when_local_matches_exchange_same_account():
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
                    "account_alias": "openclaw3",
                },
                {
                    "position_key": "meanrev:BTC-USDT-SWAP",
                    "symbol": "BTC/USDT:USDT",
                    "strategy": "meanrev",
                    "side": "short",
                    "status": "open",
                    "amount": 0.77,
                    "notional_usdt": 100.0,
                    "account_alias": "openclaw3",
                },
            ]
        }
    }
    per_account_positions = {
        "openclaw3": [
            {
                "symbol": "BTC/USDT:USDT",
                "side": "short",
                "contracts": 1.54,
                "hedged": False,
                "info": {"posSide": "net", "pos": "-1.54"},
            }
        ]
    }

    report = position_alignment_report(snapshot, per_account_positions)

    assert report["ok"] is True
    assert report["mismatches"] == []


def test_position_alignment_report_detects_missing_local_position_in_specific_account():
    snapshot = {"positions": {}}
    per_account_positions = {
        "openclaw2": [
            {
                "symbol": "BTC/USDT:USDT",
                "side": "short",
                "contracts": 1.54,
                "hedged": False,
                "info": {"posSide": "net", "pos": "-1.54"},
            }
        ]
    }

    report = position_alignment_report(snapshot, per_account_positions)

    assert report["ok"] is False
    assert report["mismatches"][0]["type"] == "missing_local_position"
    assert report["mismatches"][0]["account_alias"] == "openclaw2"


def test_position_alignment_report_detects_same_symbol_on_different_account_as_mismatch():
    snapshot = {
        "positions": {
            "meanrev:BTC-USDT-SWAP": [
                {
                    "position_key": "meanrev:BTC-USDT-SWAP",
                    "symbol": "BTC/USDT:USDT",
                    "strategy": "meanrev",
                    "side": "short",
                    "status": "open",
                    "amount": 1.54,
                    "notional_usdt": 200.0,
                    "account_alias": "openclaw3",
                }
            ]
        }
    }
    per_account_positions = {
        "default": [
            {
                "symbol": "BTC/USDT:USDT",
                "side": "short",
                "contracts": 1.54,
                "hedged": False,
                "info": {"posSide": "net", "pos": "-1.54"},
            }
        ]
    }

    report = position_alignment_report(snapshot, per_account_positions)

    assert report["ok"] is False
    assert {item["type"] for item in report["mismatches"]} == {"missing_exchange_position", "missing_local_position"}
