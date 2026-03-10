from __future__ import annotations

import argparse
import json
from pathlib import Path
from datetime import datetime, UTC
from zoneinfo import ZoneInfo

from src.config.settings import Settings
from src.exchange.okx_client import OkxClientRegistry
from src.execution.executor import DemoExecutor
from src.notify.openclaw_notify import OpenClawNotifier
from src.risk.manager import RiskManager
from src.storage.market_data import MarketDataStore
from src.storage.state import StateStore
from src.strategy.breakout import BreakoutStrategy
from src.strategy.meanrev import MeanReversionStrategy
from src.strategy.pullback import PullbackStrategy

BJ = ZoneInfo('Asia/Shanghai')


def account_symbol_key(account_alias: str, symbol: str) -> str:
    return f"{account_alias}::{symbol}"


def exchange_live_position_map(exchange_positions: list[dict], account_alias: str) -> dict[str, dict]:
    live_positions: dict[str, dict] = {}
    for position in exchange_positions:
        contracts = float(position.get("contracts") or 0.0)
        if contracts == 0:
            continue
        symbol = position.get("symbol")
        if not symbol:
            continue
        live_positions[account_symbol_key(account_alias, symbol)] = {
            "account_alias": account_alias,
            "side": position.get("side"),
            "contracts": abs(contracts),
            "hedged": bool(position.get("hedged")),
            "pos_side": position.get("info", {}).get("posSide"),
            "raw_pos": position.get("info", {}).get("pos"),
            "symbol": symbol,
        }
    return live_positions


def local_live_position_map(snapshot: dict) -> dict[str, dict]:
    local_positions: dict[str, dict] = {}
    for key, value in snapshot.get("positions", {}).items():
        items = value if isinstance(value, list) else [value]
        open_items = [item for item in items if item.get("status") == "open"]
        if not open_items:
            continue
        symbol = open_items[0].get("symbol")
        account_alias = open_items[0].get("account_alias", "default")
        if not symbol:
            continue
        local_positions[account_symbol_key(account_alias, symbol)] = {
            "account_alias": account_alias,
            "symbol": symbol,
            "position_keys": sorted({item.get("position_key") or key for item in open_items}),
            "strategies": sorted({item.get("strategy") for item in open_items if item.get("strategy")}),
            "count": len(open_items),
            "sides": sorted({item.get("side") for item in open_items}),
            "amount": round(sum(float(item.get("amount") or 0.0) for item in open_items), 10),
            "notional_usdt": round(sum(float(item.get("notional_usdt") or 0.0) for item in open_items), 10),
        }
    return local_positions


def merge_exchange_live_positions(per_account_positions: dict[str, list[dict]]) -> dict[str, dict]:
    merged: dict[str, dict] = {}
    for account_alias, positions in per_account_positions.items():
        merged.update(exchange_live_position_map(positions, account_alias))
    return merged


def position_alignment_report(snapshot: dict, per_account_positions: dict[str, list[dict]]) -> dict:
    local_positions = local_live_position_map(snapshot)
    live_positions = merge_exchange_live_positions(per_account_positions)
    mismatches = []
    all_keys = sorted(set(local_positions) | set(live_positions))
    for composite_key in all_keys:
        local = local_positions.get(composite_key)
        exchange = live_positions.get(composite_key)
        if local is None:
            mismatches.append({
                "account_alias": exchange.get("account_alias") if exchange else None,
                "symbol": exchange.get("symbol") if exchange else composite_key,
                "type": "missing_local_position",
                "exchange": exchange,
            })
            continue
        if exchange is None:
            mismatches.append({
                "account_alias": local.get("account_alias"),
                "symbol": local.get("symbol"),
                "type": "missing_exchange_position",
                "local": local,
            })
            continue
        local_sides = local.get("sides") or []
        if len(local_sides) != 1:
            mismatches.append({
                "account_alias": local.get("account_alias"),
                "symbol": local.get("symbol"),
                "type": "multiple_local_sides",
                "local": local,
                "exchange": exchange,
            })
            continue
        local_side = local_sides[0]
        local_amount = float(local.get("amount") or 0.0)
        exchange_contracts = float(exchange.get("contracts") or 0.0)
        if local_side != exchange.get("side"):
            mismatches.append({
                "account_alias": local.get("account_alias"),
                "symbol": local.get("symbol"),
                "type": "side_mismatch",
                "local": local,
                "exchange": exchange,
            })
            continue
        if abs(local_amount - exchange_contracts) > 1e-9:
            mismatches.append({
                "account_alias": local.get("account_alias"),
                "symbol": local.get("symbol"),
                "type": "amount_mismatch",
                "local": local,
                "exchange": exchange,
                "difference": round(local_amount - exchange_contracts, 10),
            })
    return {
        "ok": len(mismatches) == 0,
        "mismatches": mismatches,
        "exchange_live_positions": live_positions,
        "local_live_positions": local_positions,
    }


def position_key(strategy_name: str, symbol: str) -> str:
    return f"{strategy_name}:{symbol}"


def ensure_bucket(snapshot: dict, key: str, strategy_name: str, symbol: str, initial_capital_usdt: float) -> dict:
    buckets = snapshot.setdefault("buckets", {})
    bucket = buckets.get(key)
    if bucket is None:
        bucket = {
            "strategy": strategy_name,
            "symbol": symbol,
            "initial_capital_usdt": initial_capital_usdt,
            "available_usdt": initial_capital_usdt,
            "allocated_usdt": 0.0,
            "locked": False,
            "lock_reason": None,
        }
        buckets[key] = bucket
    else:
        bucket.setdefault("locked", False)
        bucket.setdefault("lock_reason", None)
    return bucket


def apply_state_patch(snapshot: dict, patch: dict) -> dict:
    updated = {
        **snapshot,
        "positions": {**snapshot.get("positions", {})},
        "last_signals": {**snapshot.get("last_signals", {})},
        "history": list(snapshot.get("history", [])),
        "buckets": {**snapshot.get("buckets", {})},
    }
    updated["positions"].update(patch.get("positions", {}))
    updated["last_signals"].update(patch.get("last_signals", {}))
    updated["buckets"].update(patch.get("buckets", {}))
    updated["history"].extend(patch.get("history_append", []))
    updated["open_positions"] = sum(
        1
        for value in updated["positions"].values()
        for item in (value if isinstance(value, list) else [value])
        if item.get("status") == "open"
    )
    return updated


def build_strategies(settings: Settings) -> list:
    registry = {
        "breakout": BreakoutStrategy(lookback=settings.breakout_lookback),
        "pullback": PullbackStrategy(lookback=settings.pullback_lookback),
        "meanrev": MeanReversionStrategy(
            lookback=settings.meanrev_lookback,
            threshold=settings.meanrev_threshold,
        ),
    }
    return [registry[name] for name in settings.strategies if name in registry]


def in_review_pause_window(now_utc: datetime | None = None) -> bool:
    now_utc = now_utc or datetime.now(UTC)
    now_bj = now_utc.astimezone(BJ)
    return now_bj.weekday() == 6 and now_bj.hour == 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Read-only connectivity check")
    parser.add_argument("--notify-test", action="store_true", help="Send a Discord test message via OpenClaw")
    parser.add_argument("--arm-demo-submit", action="store_true", help="Allow demo submission path in executor")
    parser.add_argument("--no-state-write", action="store_true", help="Do not persist state updates")
    parser.add_argument("--market-only", action="store_true", help="Collect market data only, without signals or state mutations")
    args = parser.parse_args()

    settings = Settings.load()
    settings.ensure_demo_only()

    notifier = OpenClawNotifier(target=settings.discord_channel)
    logs_root = Path.home() / ".openclaw" / "workspace" / "projects" / "okx-trading" / "logs"
    state = StateStore(logs_root / "state.json")
    market_data = MarketDataStore(logs_root / "market-data")
    risk = RiskManager(
        signal_cooldown_bars=settings.signal_cooldown_bars,
        risk_per_trade_fraction=settings.risk_per_trade_fraction,
        min_stop_distance_ratio=settings.min_stop_distance_ratio,
        atr_lookback=settings.atr_lookback,
        stop_atr_multiple=settings.stop_atr_multiple,
    )
    strategies = build_strategies(settings)
    client_registry = OkxClientRegistry(settings)
    trading_enabled = (args.arm_demo_submit and not settings.dry_run and not in_review_pause_window())

    if args.notify_test:
        result = notifier.send("OKX demo trader scaffold test: notifier path is working.")
        print(json.dumps(result, indent=2))
        return

    max_lookback = max(
        settings.breakout_lookback,
        settings.pullback_lookback,
        settings.meanrev_lookback,
    )

    if args.check:
        result = {strategy.name: client_registry.for_strategy(strategy.name).check_connectivity() for strategy in strategies}
        print(json.dumps(result, indent=2, default=str))
        return

    if args.market_only:
        writes = []
        for strategy in strategies:
            client = client_registry.for_strategy(strategy.name)
            for symbol in settings.symbols:
                exec_symbol = settings.execution_symbol(strategy.name, symbol)
                candles = client.fetch_ohlcv(exec_symbol, settings.timeframe, limit=max(50, max_lookback + 5))
                written = market_data.append_ohlc(f"{client.account_alias}:{exec_symbol}", candles)
                writes.append({
                    'account_alias': client.account_alias,
                    'account_label': client.account_label,
                    'strategy': strategy.name,
                    'symbol': symbol,
                    'execution_symbol': exec_symbol,
                    'candles': len(candles),
                    'written': written,
                })
        print(json.dumps({
            'mode': 'market_only',
            'strategy_accounts': client_registry.accounts_by_strategy(),
            'writes': writes,
        }, indent=2, default=str))
        return

    snapshot = state.load()
    starting_history_len = len(snapshot.get("history", []))
    report = []

    tracked_symbols_by_alias: dict[str, set[str]] = {}
    for strategy in strategies:
        client = client_registry.for_strategy(strategy.name)
        tracked_symbols_by_alias.setdefault(client.account_alias, set())
        for symbol in settings.symbols:
            tracked_symbols_by_alias[client.account_alias].add(settings.execution_symbol(strategy.name, symbol))

    per_account_positions: dict[str, list[dict]] = {}
    for strategy in strategies:
        client = client_registry.for_strategy(strategy.name)
        if client.account_alias in per_account_positions:
            continue
        per_account_positions[client.account_alias] = client.exchange.fetch_positions(sorted(tracked_symbols_by_alias[client.account_alias]))

    alignment = position_alignment_report(snapshot, per_account_positions)
    if trading_enabled and not alignment["ok"]:
        trading_enabled = False
        report.append({
            "action": "protection_block",
            "reason": "position_alignment_mismatch",
            "mismatches": alignment["mismatches"],
        })
        if settings.discord_channel:
            notifier.send(
                "OKX demo trader paused new submissions: local/exchange position alignment mismatch detected. "
                f"Mismatches: {json.dumps(alignment['mismatches'], ensure_ascii=False)}"
            )

    for symbol in settings.symbols:
        for strategy in strategies:
            client = client_registry.for_strategy(strategy.name)
            executor = DemoExecutor(
                armed=trading_enabled,
                client=client,
            )
            exec_symbol = settings.execution_symbol(strategy.name, symbol)
            key = position_key(strategy.name, symbol)
            bucket = ensure_bucket(snapshot, key, strategy.name, symbol, settings.bucket_initial_capital_usdt)
            position_list = snapshot.get("positions", {}).get(key, []) or []
            open_positions = [p for p in position_list if p.get("status") == "open"]
            candles = client.fetch_ohlcv(exec_symbol, settings.timeframe, limit=max(50, max_lookback + 5))
            market_data.append_ohlc(f"{client.account_alias}:{exec_symbol}", candles)
            bar_id = int(candles[-1][0]) if candles else -1
            signal = strategy.evaluate(symbol, candles)

            if signal.side == "flat" and open_positions:
                execution = executor.submit_exit_signal(
                    position_key=key,
                    symbol=exec_symbol,
                    strategy=strategy.name,
                    positions=position_list,
                    reason=f"{signal.reason}|exit_all",
                    bar_id=bar_id,
                    bucket=bucket,
                    exit_side=None,
                )
                snapshot = apply_state_patch(snapshot, execution.state_patch)
                exit_verified_flat = None if execution.venue_response is None else execution.venue_response.get("verified_flat")
                if exit_verified_flat is False:
                    locked_bucket = {
                        **snapshot.get("buckets", {}).get(key, bucket),
                        "locked": True,
                        "lock_reason": f"exit_incomplete:{bar_id}",
                    }
                    snapshot = apply_state_patch(snapshot, {
                        "buckets": {key: locked_bucket},
                        "history_append": [{
                            "event_id": f"{key}:bucket_lock:{bar_id}",
                            "trade_id": key,
                            "type": "bucket_lock",
                            "position_key": key,
                            "symbol": exec_symbol,
                            "strategy": strategy.name,
                            "reason": f"exit_incomplete:{bar_id}",
                            "bar_id": bar_id,
                            "mode": execution.mode,
                        }],
                    })
                report.append({
                    "account_alias": client.account_alias,
                    "account_label": client.account_label,
                    "symbol": symbol,
                    "execution_symbol": exec_symbol,
                    "strategy": strategy.name,
                    "action": "exit_all",
                    "position_key": key,
                    "reason": f"{signal.reason}|exit_all",
                    "execution": execution.mode,
                    "detail": execution.detail,
                    "exit_verified_flat": exit_verified_flat,
                    "remaining_contracts": None if execution.venue_response is None else execution.venue_response.get("remaining_contracts"),
                    "exit_attempt_count": 0 if execution.venue_response is None else len(execution.venue_response.get("order_attempts") or []),
                    "bucket_locked": bool(exit_verified_flat is False),
                })
                position_list = snapshot.get("positions", {}).get(key, []) or []
                open_positions = [p for p in position_list if p.get("status") == "open"]
                bucket = snapshot.get("buckets", {}).get(key, bucket)

            if signal.side == "flat":
                snapshot.setdefault("last_signals", {})[key] = {
                    "side": signal.side,
                    "reason": signal.reason,
                    "bar_id": bar_id,
                }
                report.append({
                    "account_alias": client.account_alias,
                    "account_label": client.account_label,
                    "symbol": symbol,
                    "execution_symbol": exec_symbol,
                    "strategy": strategy.name,
                    "action": "skip",
                    "position_key": key,
                    "signal": signal.side,
                    "reason": signal.reason,
                })
                continue

            if bucket.get("locked"):
                snapshot.setdefault("last_signals", {})[key] = {
                    "side": signal.side,
                    "reason": signal.reason,
                    "bar_id": bar_id,
                }
                report.append({
                    "account_alias": client.account_alias,
                    "account_label": client.account_label,
                    "symbol": symbol,
                    "execution_symbol": exec_symbol,
                    "strategy": strategy.name,
                    "action": "blocked",
                    "position_key": key,
                    "signal": signal.side,
                    "blocked": f"bucket_locked:{bucket.get('lock_reason') or 'unknown'}",
                })
                continue

            leverage = risk.dynamic_leverage(symbol, signal.side, candles)
            sizing = risk.plan_entry_size(bucket=bucket, candles=candles, leverage=leverage)
            order_size_usdt = sizing.margin_required_usdt
            decision = risk.allow_entry(
                snapshot=snapshot,
                position_key=key,
                side=signal.side,
                bar_id=bar_id,
                notional_usdt=order_size_usdt,
            )
            if not decision.allowed:
                snapshot.setdefault("last_signals", {})[key] = {
                    "side": signal.side,
                    "reason": signal.reason,
                    "bar_id": bar_id,
                }
                report.append({
                    "account_alias": client.account_alias,
                    "account_label": client.account_label,
                    "symbol": symbol,
                    "execution_symbol": exec_symbol,
                    "strategy": strategy.name,
                    "action": "blocked",
                    "position_key": key,
                    "signal": signal.side,
                    "blocked": decision.reason,
                })
                continue

            execution = executor.submit_entry_signal(
                position_key=key,
                symbol=exec_symbol,
                strategy=strategy.name,
                side=signal.side,
                reason=signal.reason,
                bar_id=bar_id,
                order_size_usdt=sizing.capped_notional_usdt,
                margin_required_usdt=sizing.margin_required_usdt,
                leverage=leverage,
                bucket=bucket,
                existing_positions=position_list,
            )
            snapshot = apply_state_patch(snapshot, execution.state_patch)
            entry_verified = None if execution.venue_response is None else execution.venue_response.get("verified_entry")
            if entry_verified is False:
                locked_bucket = {
                    **snapshot.get("buckets", {}).get(key, bucket),
                    "locked": True,
                    "lock_reason": f"entry_incomplete:{bar_id}",
                }
                snapshot = apply_state_patch(snapshot, {
                    "buckets": {key: locked_bucket},
                    "history_append": [{
                        "event_id": f"{key}:bucket_lock:{bar_id}",
                        "trade_id": key,
                        "type": "bucket_lock",
                        "position_key": key,
                        "symbol": exec_symbol,
                        "strategy": strategy.name,
                        "reason": f"entry_incomplete:{bar_id}",
                        "bar_id": bar_id,
                        "mode": execution.mode,
                    }],
                })
            report_item = {
                "account_alias": client.account_alias,
                "account_label": client.account_label,
                "symbol": symbol,
                "execution_symbol": exec_symbol,
                "strategy": strategy.name,
                "action": "entry",
                "position_key": key,
                "signal": signal.side,
                "reason": signal.reason,
                "execution": execution.mode,
                "detail": execution.detail,
                "margin_usdt": order_size_usdt,
                "effective_notional_usdt": sizing.capped_notional_usdt,
                "risk_budget_usdt": sizing.risk_budget_usdt,
                "stop_distance_ratio": sizing.stop_distance_ratio,
                "leverage": leverage,
                "bucket_available_usdt": snapshot.get("buckets", {}).get(key, {}).get("available_usdt"),
            }
            if execution.venue_response is not None:
                report_item["venue_order_id"] = execution.venue_response.get("order_id")
                report_item["venue_status"] = execution.venue_response.get("status")
                report_item["reference_price"] = execution.venue_response.get("reference_price")
                report_item["amount"] = execution.venue_response.get("amount")
                report_item["entry_verified"] = execution.venue_response.get("verified_entry")
                report_item["live_contracts"] = execution.venue_response.get("live_contracts")
                report_item["live_side"] = execution.venue_response.get("live_side")
            report_item["bucket_locked"] = bool(entry_verified is False)
            report.append(report_item)

    market_data.append_events(snapshot.get("history", [])[starting_history_len:])

    if not args.no_state_write:
        state.save(snapshot)

    print(json.dumps({
        "mode": "dry_run" if trading_enabled is False else "demo_submit",
        "trading_enabled": trading_enabled,
        "strategy_accounts": client_registry.accounts_by_strategy(),
        "alignment_ok": alignment["ok"],
        "alignment_mismatches": alignment["mismatches"],
        "symbols": settings.symbols,
        "strategies": [strategy.name for strategy in strategies],
        "report": report,
        "open_positions": snapshot.get("open_positions", 0),
        "bucket_count": len(snapshot.get("buckets", {})),
    }, indent=2, default=str))


if __name__ == "__main__":
    main()
