from src.review.reconcile_state import reconcile_snapshot


def test_reconcile_closes_positions_when_exchange_side_mismatches_and_releases_bucket():
    state = {
        "positions": {
            "breakout:ETH-USDT-SWAP": [
                {
                    "position_key": "breakout:ETH-USDT-SWAP",
                    "symbol": "ETH/USDT:USDT",
                    "strategy": "breakout",
                    "side": "short",
                    "status": "open",
                    "notional_usdt": 100.0,
                    "amount": 0.48,
                    "account_alias": "default",
                },
                {
                    "position_key": "breakout:ETH-USDT-SWAP",
                    "symbol": "ETH/USDT:USDT",
                    "strategy": "breakout",
                    "side": "short",
                    "status": "open",
                    "notional_usdt": 200.0,
                    "amount": 0.48,
                    "account_alias": "default",
                },
            ]
        },
        "buckets": {
            "breakout:ETH-USDT-SWAP": {
                "available_usdt": 200.0,
                "allocated_usdt": 300.0,
            }
        },
        "last_signals": {},
        "history": [],
    }
    live_open = {
        "default::ETH/USDT:USDT": {
            "account_alias": "default",
            "symbol": "ETH/USDT:USDT",
            "contracts": 0.48,
            "side": "long",
        }
    }

    updated, closed_keys, normalized_keys = reconcile_snapshot(state, live_open, now_bar_id=123456)

    positions = updated["positions"]["breakout:ETH-USDT-SWAP"]
    assert [p["status"] for p in positions] == ["closed", "closed"]
    assert positions[0]["exit_reason"] == "reconcile_exchange_side_mismatch:short!=long"
    assert positions[1]["exit_bar_id"] == 123456
    assert updated["buckets"]["breakout:ETH-USDT-SWAP"]["available_usdt"] == 500.0
    assert updated["buckets"]["breakout:ETH-USDT-SWAP"]["allocated_usdt"] == 0.0
    assert closed_keys == [{"position_key": "breakout:ETH-USDT-SWAP", "released_usdt": 300.0}]
    assert normalized_keys == []


def test_reconcile_normalizes_live_contracts_across_matching_open_positions():
    state = {
        "positions": {
            "meanrev:BTC-USDT-SWAP": [
                {
                    "position_key": "meanrev:BTC-USDT-SWAP",
                    "symbol": "BTC/USDT:USDT",
                    "strategy": "meanrev",
                    "side": "short",
                    "status": "open",
                    "notional_usdt": 100.0,
                    "amount": 0.98,
                    "account_alias": "openclaw3",
                },
                {
                    "position_key": "meanrev:BTC-USDT-SWAP",
                    "symbol": "BTC/USDT:USDT",
                    "strategy": "meanrev",
                    "side": "short",
                    "status": "open",
                    "notional_usdt": 100.0,
                    "amount": 0.98,
                    "account_alias": "openclaw3",
                },
            ]
        },
        "buckets": {
            "meanrev:BTC-USDT-SWAP": {
                "available_usdt": 300.0,
                "allocated_usdt": 200.0,
            }
        },
        "last_signals": {},
        "history": [],
    }
    live_open = {
        "openclaw3::BTC/USDT:USDT": {
            "account_alias": "openclaw3",
            "symbol": "BTC/USDT:USDT",
            "contracts": 1.54,
            "side": "short",
        }
    }

    updated, closed_keys, normalized_keys = reconcile_snapshot(state, live_open, now_bar_id=789)

    positions = updated["positions"]["meanrev:BTC-USDT-SWAP"]
    assert [p["status"] for p in positions] == ["open", "open"]
    assert [p["amount"] for p in positions] == [0.77, 0.77]
    assert updated["buckets"]["meanrev:BTC-USDT-SWAP"]["available_usdt"] == 300.0
    assert updated["buckets"]["meanrev:BTC-USDT-SWAP"]["allocated_usdt"] == 200.0
    assert closed_keys == []
    assert normalized_keys == [{
        "position_key": "meanrev:BTC-USDT-SWAP",
        "account_alias": "openclaw3",
        "symbol": "BTC/USDT:USDT",
        "side": "short",
        "live_contracts": 1.54,
        "open_items": 2,
        "per_position_amount": 0.77,
    }]
