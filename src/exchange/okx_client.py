from __future__ import annotations

from typing import Any

import ccxt

from src.config.settings import Settings


class OkxClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.exchange = ccxt.okx({
            "apiKey": settings.okx_api_key,
            "secret": settings.okx_api_secret,
            "password": settings.okx_api_passphrase,
            "enableRateLimit": True,
            "options": {
                "defaultType": "swap",
            },
        })
        self.exchange.set_sandbox_mode(settings.okx_demo)

    def check_connectivity(self) -> dict[str, Any]:
        markets = self.exchange.load_markets()
        symbols_found: list[str] = []
        ticker_status: dict[str, Any] = {}
        for strategy_name in self.settings.strategies:
            for raw_symbol in self.settings.symbols:
                execution_symbol = self.settings.execution_symbol(strategy_name, raw_symbol)
                key = f"{strategy_name}:{raw_symbol}"
                if execution_symbol not in markets:
                    ticker_status[key] = {
                        "ok": False,
                        "reason": "symbol_not_found",
                        "ccxt_symbol": execution_symbol,
                    }
                    continue
                symbols_found.append(key)
                try:
                    ticker = self.exchange.fetch_ticker(execution_symbol)
                    ticker_status[key] = {
                        "ok": True,
                        "ccxt_symbol": execution_symbol,
                        "last": ticker.get("last"),
                        "bid": ticker.get("bid"),
                        "ask": ticker.get("ask"),
                    }
                except Exception as exc:
                    ticker_status[key] = {
                        "ok": False,
                        "ccxt_symbol": execution_symbol,
                        "reason": str(exc),
                    }
        balance = self.exchange.fetch_balance()
        return {
            "exchange": self.exchange.id,
            "demo": self.settings.okx_demo,
            "symbols_found": symbols_found,
            "ticker_status": ticker_status,
            "balance_keys": sorted(list(balance.keys()))[:10],
        }

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 200):
        execution_symbol = self.settings.ccxt_symbol(symbol)
        return self.exchange.fetch_ohlcv(execution_symbol, timeframe=timeframe, limit=limit)

    def ensure_markets_loaded(self) -> None:
        if not getattr(self.exchange, "markets", None):
            self.exchange.load_markets()

    def create_entry_order(self, symbol: str, signal_side: str, notional_usdt: float) -> dict[str, Any]:
        self.ensure_markets_loaded()
        execution_symbol = self.settings.ccxt_symbol(symbol)
        market = self.exchange.market(execution_symbol)
        ticker = self.exchange.fetch_ticker(execution_symbol)
        last_price = float(ticker.get("last") or ticker.get("bid") or ticker.get("ask") or 0)
        if last_price <= 0:
            raise RuntimeError(f"Unable to determine last price for {symbol}")

        contract_size = float(market.get("contractSize") or 1.0)
        raw_amount = notional_usdt / (last_price * contract_size)
        amount = float(self.exchange.amount_to_precision(execution_symbol, raw_amount))
        min_amount = float((market.get("limits", {}).get("amount", {}) or {}).get("min") or 0)
        if amount < min_amount:
            amount = min_amount

        order_side = "buy" if signal_side == "long" else "sell"
        params = {
            "tdMode": "cross",
        }
        order = self.exchange.create_order(execution_symbol, "market", order_side, amount, None, params)
        return {
            "symbol": symbol,
            "ccxt_symbol": execution_symbol,
            "signal_side": signal_side,
            "order_side": order_side,
            "amount": amount,
            "notional_usdt": notional_usdt,
            "reference_price": last_price,
            "order_id": order.get("id"),
            "status": order.get("status"),
            "raw": order,
        }

    def create_exit_order(self, symbol: str, position_side: str, amount: float) -> dict[str, Any]:
        if amount <= 0:
            raise RuntimeError(f"Refusing to exit {symbol}: tracked amount is missing or invalid")

        self.ensure_markets_loaded()
        execution_symbol = self.settings.ccxt_symbol(symbol)
        order_side = "sell" if position_side == "long" else "buy"
        params = {
            "tdMode": "cross",
            "reduceOnly": True,
        }
        order = self.exchange.create_order(execution_symbol, "market", order_side, amount, None, params)
        return {
            "symbol": symbol,
            "ccxt_symbol": execution_symbol,
            "position_side": position_side,
            "order_side": order_side,
            "amount": amount,
            "order_id": order.get("id"),
            "status": order.get("status"),
            "raw": order,
        }
