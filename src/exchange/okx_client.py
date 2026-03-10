from __future__ import annotations

from typing import Any
import time
from datetime import datetime, UTC

import ccxt

from src.config.settings import Settings, StrategyAccountConfig


def extract_order_fee(order: dict[str, Any] | None) -> float | None:
    if not order:
        return None
    fee = order.get('fee')
    if isinstance(fee, dict):
        cost = fee.get('cost')
        if cost is not None:
            try:
                return float(cost)
            except Exception:
                pass
    fees = order.get('fees')
    if isinstance(fees, list) and fees:
        total = 0.0
        found = False
        for item in fees:
            if not isinstance(item, dict):
                continue
            cost = item.get('cost')
            if cost is None:
                continue
            try:
                total += float(cost)
                found = True
            except Exception:
                continue
        if found:
            return total
    info = order.get('info') if isinstance(order.get('info'), dict) else {}
    for key in ['fee', 'fillFee', 'fill_fee', 'execFee']:
        if info.get(key) is not None:
            try:
                return abs(float(info.get(key)))
            except Exception:
                continue
    return None


def exit_order_side(position_side: str) -> str:
    if position_side == "long":
        return "sell"
    if position_side == "short":
        return "buy"
    raise ValueError(f"Unsupported position side for exit order: {position_side}")


def normalize_contract_amount(exchange: Any, execution_symbol: str, amount: float) -> float:
    normalized = float(exchange.amount_to_precision(execution_symbol, amount))
    market = exchange.market(execution_symbol)
    min_amount = float((market.get("limits", {}).get("amount", {}) or {}).get("min") or 0)
    if normalized < min_amount:
        raise RuntimeError(
            f"Refusing to submit {execution_symbol}: normalized amount {normalized} is below minimum {min_amount}"
        )
    return normalized


def live_position_snapshot(exchange: Any, execution_symbol: str) -> dict[str, Any] | None:
    positions = exchange.fetch_positions([execution_symbol])
    for position in positions:
        info = position.get('info') or {}
        if info.get('instType') != 'SWAP':
            continue
        if position.get('symbol') != execution_symbol:
            continue
        contracts = float(position.get('contracts') or 0.0)
        if contracts == 0:
            continue
        return {
            'symbol': position.get('symbol'),
            'side': position.get('side'),
            'contracts': abs(contracts),
            'hedged': bool(position.get('hedged')),
            'pos_side': info.get('posSide'),
            'raw_pos': info.get('pos'),
        }
    return None


def amount_close_enough(expected: float, actual: float, tolerance_ratio: float = 0.15, tolerance_abs: float = 2.0) -> bool:
    try:
        expected = float(expected)
        actual = float(actual)
    except Exception:
        return False
    if expected <= 0 or actual <= 0:
        return False
    diff = abs(actual - expected)
    return diff <= max(tolerance_abs, expected * tolerance_ratio)


def fee_summary_from_trades(trades: list[dict]) -> dict[str, Any] | None:
    if not trades:
        return None
    total_fee = 0.0
    found_fee = False
    fee_ccys = []
    fee_rates = []
    fill_ids = []
    for trade in trades:
        fee = trade.get('fee')
        if isinstance(fee, dict):
            cost = fee.get('cost')
            if cost is not None:
                try:
                    total_fee += abs(float(cost))
                    found_fee = True
                except Exception:
                    pass
            currency = fee.get('currency')
            if currency:
                fee_ccys.append(str(currency))
        elif fee is not None:
            try:
                total_fee += abs(float(fee))
                found_fee = True
            except Exception:
                pass
        fee_ccy = trade.get('feeCurrency') or trade.get('feeCcy')
        if fee_ccy:
            fee_ccys.append(str(fee_ccy))
        fee_rate = trade.get('feeRate')
        if fee_rate is not None:
            fee_rates.append(str(fee_rate))
        tid = trade.get('id') or trade.get('tradeId')
        if tid:
            fill_ids.append(str(tid))
    return {
        'fee_usdt': total_fee if found_fee else None,
        'fee_ccy': sorted(set(fee_ccys)) if fee_ccys else None,
        'fee_rate': sorted(set(fee_rates)) if fee_rates else None,
        'fill_ids': fill_ids or None,
        'fill_count': len(trades),
    }


class OkxClient:
    def __init__(self, settings: Settings, account: StrategyAccountConfig | None = None):
        self.settings = settings
        self.account = account or settings.account_for_strategy("breakout")
        self.account_alias = self.account.alias
        self.account_label = self.account.label or self.account.alias
        base_config = {
            "apiKey": self.account.api_key,
            "secret": self.account.api_secret,
            "password": self.account.api_passphrase,
            "enableRateLimit": True,
        }
        self.exchange = ccxt.okx({
            **base_config,
            "options": {
                "defaultType": "swap",
            },
        })
        self.spot_exchange = ccxt.okx({
            **base_config,
            "options": {
                "defaultType": "spot",
            },
        })
        self.exchange.set_sandbox_mode(settings.okx_demo)
        self.spot_exchange.set_sandbox_mode(settings.okx_demo)

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
            "account_alias": self.account_alias,
            "account_label": self.account_label,
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

    def current_live_position(self, symbol: str) -> dict[str, Any] | None:
        self.ensure_markets_loaded()
        execution_symbol = self.settings.ccxt_symbol(symbol)
        return live_position_snapshot(self.exchange, execution_symbol)

    def fetch_order_fees(
        self,
        execution_symbol: str,
        order_id: str | None,
        since_ms: int | None = None,
        side: str | None = None,
        amount: float | None = None,
    ) -> dict[str, Any] | None:
        if not order_id:
            return None
        try:
            trades = self.exchange.fetch_my_trades(execution_symbol, since=since_ms, limit=100)
        except Exception:
            trades = []
        exact = []
        fallback = []
        for trade in trades:
            info = trade.get('info') or {}
            trade_order_id = str(trade.get('order') or info.get('ordId') or '')
            if trade_order_id == str(order_id):
                exact.append(trade)
                continue
            if side and str(trade.get('side')) != str(side):
                continue
            if amount is not None:
                try:
                    trade_amount = float(trade.get('amount') or 0.0)
                except Exception:
                    trade_amount = 0.0
                if trade_amount <= 0 or not amount_close_enough(float(amount), trade_amount, tolerance_ratio=0.35, tolerance_abs=5.0):
                    continue
            fallback.append(trade)
        return fee_summary_from_trades(exact or fallback[:5])

    def create_entry_order(self, symbol: str, signal_side: str, notional_usdt: float, current_open_amount: float = 0.0) -> dict[str, Any]:
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
        fee_usdt = extract_order_fee(order)
        fee_meta = self.fetch_order_fees(
            execution_symbol,
            order.get('id'),
            since_ms=int(datetime.now(UTC).timestamp() * 1000) - 300000,
            side=order_side,
            amount=amount,
        )
        if fee_meta and fee_meta.get('fee_usdt') is not None:
            fee_usdt = fee_meta.get('fee_usdt')

        verified_entry = False
        live_contracts = 0.0
        live_side = None
        verification = []
        for attempt in range(1, 4):
            time.sleep(1.0)
            live = live_position_snapshot(self.exchange, execution_symbol)
            verification.append({'attempt': attempt, 'live': live})
            if live is None:
                continue
            live_contracts = float(live.get('contracts') or 0.0)
            live_side = live.get('side')
            target_amount = float(current_open_amount or 0.0) + float(amount)
            if live_side == signal_side and amount_close_enough(target_amount, live_contracts):
                verified_entry = True
                break

        return {
            "symbol": symbol,
            "ccxt_symbol": execution_symbol,
            "signal_side": signal_side,
            "order_side": order_side,
            "amount": amount,
            "notional_usdt": notional_usdt,
            "reference_price": last_price,
            "fee_usdt": fee_usdt,
            "fee_ccy": None if fee_meta is None else fee_meta.get('fee_ccy'),
            "fee_rate": None if fee_meta is None else fee_meta.get('fee_rate'),
            "fill_ids": None if fee_meta is None else fee_meta.get('fill_ids'),
            "fill_count": None if fee_meta is None else fee_meta.get('fill_count'),
            "verified_entry": verified_entry,
            "live_contracts": live_contracts,
            "live_side": live_side,
            "verification_attempts": verification,
            "order_id": order.get("id"),
            "status": order.get("status"),
            "account_alias": self.account_alias,
            "account_label": self.account_label,
            "raw": order,
        }

    def create_exit_order(self, symbol: str, position_side: str, amount: float) -> dict[str, Any]:
        if amount <= 0:
            raise RuntimeError(f"Refusing to exit {symbol}: tracked amount is missing or invalid")

        self.ensure_markets_loaded()
        execution_symbol = self.settings.ccxt_symbol(symbol)
        ticker = self.exchange.fetch_ticker(execution_symbol)
        last_price = float(ticker.get("last") or ticker.get("bid") or ticker.get("ask") or 0)
        order_side = exit_order_side(position_side)
        params = {
            "tdMode": "cross",
            "reduceOnly": True,
        }

        orders = []
        verification = []
        total_fee_usdt = 0.0
        fee_found = False
        verified_flat = False
        remaining_contracts = float(amount)
        remaining_side = position_side

        current_amount = float(amount)
        for attempt in range(1, 4):
            normalized_amount = normalize_contract_amount(self.exchange, execution_symbol, current_amount)
            order = self.exchange.create_order(execution_symbol, "market", order_side, normalized_amount, None, params)
            fee_usdt = extract_order_fee(order)
            fee_meta = self.fetch_order_fees(
                execution_symbol,
                order.get('id'),
                since_ms=int(datetime.now(UTC).timestamp() * 1000) - 300000,
                side=order_side,
                amount=normalized_amount,
            )
            if fee_meta and fee_meta.get('fee_usdt') is not None:
                fee_usdt = fee_meta.get('fee_usdt')
            if fee_usdt is not None:
                total_fee_usdt += fee_usdt
                fee_found = True
            orders.append({
                'attempt': attempt,
                'order_id': order.get('id'),
                'status': order.get('status'),
                'amount': normalized_amount,
                'fee_usdt': fee_usdt,
                'fee_ccy': None if fee_meta is None else fee_meta.get('fee_ccy'),
                'fee_rate': None if fee_meta is None else fee_meta.get('fee_rate'),
                'fill_ids': None if fee_meta is None else fee_meta.get('fill_ids'),
                'fill_count': None if fee_meta is None else fee_meta.get('fill_count'),
            })

            time.sleep(1.0)
            live = live_position_snapshot(self.exchange, execution_symbol)
            trade_confirmed = bool(fee_meta and fee_meta.get('fill_count'))
            verification.append({'attempt': attempt, 'live': live, 'trade_confirmed': trade_confirmed})
            if live is None:
                verified_flat = True
                remaining_contracts = 0.0
                remaining_side = None
                break
            if trade_confirmed and attempt == 1:
                time.sleep(2.0)
                live_retry = live_position_snapshot(self.exchange, execution_symbol)
                verification.append({'attempt': f'{attempt}-retry', 'live': live_retry, 'trade_confirmed': trade_confirmed})
                if live_retry is None:
                    verified_flat = True
                    remaining_contracts = 0.0
                    remaining_side = None
                    break
                live = live_retry

            verified_flat = False
            remaining_contracts = float(live.get('contracts') or 0.0)
            remaining_side = live.get('side')
            current_amount = remaining_contracts
            if remaining_contracts <= 0:
                break

        final_order = orders[-1] if orders else {}
        return {
            "symbol": symbol,
            "ccxt_symbol": execution_symbol,
            "position_side": position_side,
            "order_side": order_side,
            "amount": final_order.get('amount'),
            "requested_amount": amount,
            "reference_price": last_price if last_price > 0 else None,
            "fee_usdt": total_fee_usdt if fee_found else None,
            "fee_ccy": sorted({ccy for row in orders for ccy in (row.get('fee_ccy') or [])}) or None,
            "fee_rate": sorted({rate for row in orders for rate in (row.get('fee_rate') or [])}) or None,
            "fill_ids": [fid for row in orders for fid in (row.get('fill_ids') or [])] or None,
            "fill_count": sum(int(row.get('fill_count') or 0) for row in orders) or None,
            "verified_flat": verified_flat,
            "remaining_contracts": remaining_contracts,
            "remaining_side": remaining_side,
            "verification_attempts": verification,
            "order_attempts": orders,
            "order_id": final_order.get("order_id"),
            "status": final_order.get("status"),
            "account_alias": self.account_alias,
            "account_label": self.account_label,
            "raw": final_order,
        }

    def convert_asset_to_usdt(self, asset: str, amount: float) -> dict[str, Any]:
        if asset == 'USDT':
            return {'asset': asset, 'skipped': True, 'reason': 'already_usdt'}
        if amount <= 0:
            return {'asset': asset, 'skipped': True, 'reason': 'non_positive_amount'}

        if not getattr(self.spot_exchange, 'markets', None):
            self.spot_exchange.load_markets()
        symbol = f'{asset}/USDT'
        market = self.spot_exchange.market(symbol)
        min_amount = float((market.get('limits', {}).get('amount', {}) or {}).get('min') or 0)
        sell_amount = float(self.spot_exchange.amount_to_precision(symbol, amount))
        if sell_amount < min_amount:
            return {
                'asset': asset,
                'skipped': True,
                'reason': f'amount_below_min:{sell_amount}<{min_amount}',
                'symbol': symbol,
            }
        order = self.spot_exchange.create_order(symbol, 'market', 'sell', sell_amount, None, {'tdMode': 'cash'})
        return {
            'asset': asset,
            'symbol': symbol,
            'side': 'sell',
            'amount': sell_amount,
            'order_id': order.get('id'),
            'status': order.get('status'),
            'account_alias': self.account_alias,
            'account_label': self.account_label,
            'raw': order,
        }


class OkxClientRegistry:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._clients: dict[str, OkxClient] = {}

    def for_strategy(self, strategy_name: str) -> OkxClient:
        account = self.settings.account_for_strategy(strategy_name)
        if account.alias not in self._clients:
            self._clients[account.alias] = OkxClient(self.settings, account)
        return self._clients[account.alias]

    def accounts_by_strategy(self) -> dict[str, str]:
        return {strategy: self.settings.account_for_strategy(strategy).alias for strategy in self.settings.strategies}
