from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.config.settings import Settings
from src.exchange.okx_client import OkxClient
from src.execution.executor import DemoExecutor
from src.notify.openclaw_notify import OpenClawNotifier
from src.risk.manager import RiskManager
from src.storage.state import StateStore
from src.strategy.breakout import BreakoutStrategy
from src.strategy.meanrev import MeanReversionStrategy
from src.strategy.pullback import PullbackStrategy


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
        }
        buckets[key] = bucket
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
        1 for item in updated["positions"].values() if item.get("status") == "open"
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Read-only connectivity check")
    parser.add_argument("--notify-test", action="store_true", help="Send a Discord test message via OpenClaw")
    parser.add_argument("--arm-demo-submit", action="store_true", help="Allow demo submission path in executor")
    parser.add_argument("--no-state-write", action="store_true", help="Do not persist state updates")
    args = parser.parse_args()

    settings = Settings.load()
    settings.ensure_demo_only()

    notifier = OpenClawNotifier(target=settings.discord_channel)
    state = StateStore(Path.home() / "openclaw-automation" / "logs" / "state.json")
    risk = RiskManager(
        max_open_positions=settings.max_open_positions,
        signal_cooldown_bars=settings.signal_cooldown_bars,
    )
    strategies = build_strategies(settings)
    client = OkxClient(settings)
    executor = DemoExecutor(
        armed=(args.arm_demo_submit and not settings.dry_run),
        client=client,
    )

    if args.notify_test:
        result = notifier.send("OKX demo trader scaffold test: notifier path is working.")
        print(json.dumps(result, indent=2))
        return

    if args.check:
        result = client.check_connectivity()
        print(json.dumps(result, indent=2, default=str))
        return

    snapshot = state.load()
    report = []
    max_lookback = max(
        settings.breakout_lookback,
        settings.pullback_lookback,
        settings.meanrev_lookback,
    )

    for symbol in settings.symbols:
        candles = client.fetch_ohlcv(symbol, settings.timeframe, limit=max(50, max_lookback + 5))
        bar_id = int(candles[-1][0]) if candles else -1

        for strategy in strategies:
            key = position_key(strategy.name, symbol)
            bucket = ensure_bucket(snapshot, key, strategy.name, symbol, settings.bucket_initial_capital_usdt)
            current_position = snapshot.get("positions", {}).get(key)
            signal = strategy.evaluate(symbol, candles)

            if current_position and current_position.get("status") == "open":
                current_side = current_position.get("side")
                should_exit = signal.side == "flat" or signal.side != current_side
                if should_exit:
                    exit_reason = f"{signal.reason}|exit_{current_side}"
                    execution = executor.submit_exit_signal(
                        position_key=key,
                        symbol=symbol,
                        strategy=strategy.name,
                        position=current_position,
                        reason=exit_reason,
                        bar_id=bar_id,
                        bucket=bucket,
                    )
                    snapshot = apply_state_patch(snapshot, execution.state_patch)
                    report.append({
                        "symbol": symbol,
                        "strategy": strategy.name,
                        "action": "exit",
                        "position_key": key,
                        "reason": exit_reason,
                        "execution": execution.mode,
                        "detail": execution.detail,
                    })
                    current_position = snapshot.get("positions", {}).get(key)
                    bucket = snapshot.get("buckets", {}).get(key, bucket)
                else:
                    report.append({
                        "symbol": symbol,
                        "strategy": strategy.name,
                        "action": "hold",
                        "position_key": key,
                        "side": current_side,
                        "reason": signal.reason,
                    })
                    continue

            if signal.side == "flat":
                snapshot.setdefault("last_signals", {})[key] = {
                    "side": signal.side,
                    "reason": signal.reason,
                    "bar_id": bar_id,
                }
                report.append({
                    "symbol": symbol,
                    "strategy": strategy.name,
                    "action": "skip",
                    "position_key": key,
                    "signal": signal.side,
                    "reason": signal.reason,
                })
                continue

            if current_position and current_position.get("status") == "open":
                continue

            order_size_usdt = min(settings.default_order_size_usdt, float(bucket.get("available_usdt", 0.0)))
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
                    "symbol": symbol,
                    "strategy": strategy.name,
                    "action": "blocked",
                    "position_key": key,
                    "signal": signal.side,
                    "blocked": decision.reason,
                })
                continue

            execution = executor.submit_entry_signal(
                position_key=key,
                symbol=symbol,
                strategy=strategy.name,
                side=signal.side,
                reason=signal.reason,
                bar_id=bar_id,
                order_size_usdt=order_size_usdt,
                bucket=bucket,
            )
            snapshot = apply_state_patch(snapshot, execution.state_patch)
            report_item = {
                "symbol": symbol,
                "strategy": strategy.name,
                "action": "entry",
                "position_key": key,
                "signal": signal.side,
                "reason": signal.reason,
                "execution": execution.mode,
                "detail": execution.detail,
                "notional_usdt": order_size_usdt,
                "bucket_available_usdt": snapshot.get("buckets", {}).get(key, {}).get("available_usdt"),
            }
            if execution.venue_response is not None:
                report_item["venue_order_id"] = execution.venue_response.get("order_id")
                report_item["venue_status"] = execution.venue_response.get("status")
                report_item["reference_price"] = execution.venue_response.get("reference_price")
                report_item["amount"] = execution.venue_response.get("amount")
            report.append(report_item)

    if not args.no_state_write:
        state.save(snapshot)

    print(json.dumps({
        "mode": "dry_run" if executor.armed is False else "demo_submit",
        "symbols": settings.symbols,
        "strategies": [strategy.name for strategy in strategies],
        "report": report,
        "open_positions": snapshot.get("open_positions", 0),
        "bucket_count": len(snapshot.get("buckets", {})),
    }, indent=2, default=str))


if __name__ == "__main__":
    main()
