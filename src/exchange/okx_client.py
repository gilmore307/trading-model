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
        for raw_symbol in self.settings.symbols:
            symbol = self.settings.ccxt_symbol(raw_symbol)
            if symbol not in markets:
                ticker_status[raw_symbol] = {
                    "ok": False,
                    "reason": "symbol_not_found",
                    "ccxt_symbol": symbol,
                }
                continue
            symbols_found.append(raw_symbol)
            try:
                ticker = self.exchange.fetch_ticker(symbol)
                ticker_status[raw_symbol] = {
                    "ok": True,
                    "ccxt_symbol": symbol,
                    "last": ticker.get("last"),
                    "bid": ticker.get("bid"),
                    "ask": ticker.get("ask"),
                }
            except Exception as exc:
                ticker_status[raw_symbol] = {
                    "ok": False,
                    "ccxt_symbol": symbol,
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

    def fetch_ohlcv(self, raw_symbol: str, timeframe: str, limit: int = 200):
        symbol = self.settings.ccxt_symbol(raw_symbol)
        return self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

    def create_entry_order(self, raw_symbol: str, signal_side: str, notional_usdt: float) -> dict[str, Any]:
        symbol = self.settings.ccxt_symbol(raw_symbol)
        market = self.exchange.market(symbol)
        ticker = self.exchange.fetch_ticker(symbol)
        last_price = float(ticker.get("last") or ticker.get("bid") or ticker.get("ask") or 0)
        if last_price <= 0:
            raise RuntimeError(f"Unable to determine last price for {raw_symbol}")

        contract_size = float(market.get("contractSize") or 1.0)
        raw_amount = notional_usdt / (last_price * contract_size)
        amount = float(self.exchange.amount_to_precision(symbol, raw_amount))
        min_amount = float((market.get("limits", {}).get("amount", {}) or {}).get("min") or 0)
        if amount < min_amount:
            amount = min_amount

        order_side = "buy" if signal_side == "long" else "sell"
        params = {
            "tdMode": "cross",
        }
        order = self.exchange.create_order(symbol, "market", order_side, amount, None, params)
        return {
            "symbol": raw_symbol,
            "ccxt_symbol": symbol,
            "signal_side": signal_side,
            "order_side": order_side,
            "amount": amount,
            "notional_usdt": notional_usdt,
            "reference_price": last_price,
            "order_id": order.get("id"),
            "status": order.get("status"),
            "raw": order,
        }

    def create_exit_order(self, raw_symbol: str, position_side: str, amount: float) -> dict[str, Any]:
        if amount <= 0:
            raise RuntimeError(f"Refusing to exit {raw_symbol}: tracked amount is missing or invalid")

        symbol = self.settings.ccxt_symbol(raw_symbol)
        order_side = "sell" if position_side == "long" else "buy"
        params = {
            "tdMode": "cross",
            "reduceOnly": True,
        }
        order = self.exchange.create_order(symbol, "market", order_side, amount, None, params)
        return {
            "symbol": raw_symbol,
            "ccxt_symbol": symbol,
            "position_side": position_side,
            "order_side": order_side,
            "amount": amount,
            "order_id": order.get("id"),
            "status": order.get("status"),
            "raw": order,
        }
