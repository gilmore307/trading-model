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


def extract_realized_pnl(payload: dict[str, Any] | None) -> float | None:
    if not isinstance(payload, dict):
        return None
    candidates = [payload]
    info = payload.get('info') if isinstance(payload.get('info'), dict) else None
    if info is not None:
        candidates.append(info)
    for row in candidates:
        for key in ('realizedPnl', 'realized_pnl', 'realized_pnl_usdt', 'fillPnl', 'fill_pnl', 'closedPnl', 'closed_pnl', 'pnl'):
            value = row.get(key)
            if value is None:
                continue
            try:
                return float(value)
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


def _normalize_live_position_row(position: dict[str, Any], *, expected_symbol: str | None = None) -> dict[str, Any] | None:
    info = position.get('info') or {}
    if info.get('instType') != 'SWAP':
        return None
    symbol = position.get('symbol')
    if expected_symbol is not None and symbol != expected_symbol:
        return None
    contracts = float(position.get('contracts') or 0.0)
    if contracts == 0:
        return None
    return {
        'symbol': symbol,
        'side': position.get('side'),
        'contracts': abs(contracts),
        'hedged': bool(position.get('hedged')),
        'pos_side': info.get('posSide'),
        'raw_pos': info.get('pos'),
    }


def live_position_snapshot(exchange: Any, execution_symbol: str) -> dict[str, Any] | None:
    positions = exchange.fetch_positions([execution_symbol])
    for position in positions:
        normalized = _normalize_live_position_row(position, expected_symbol=execution_symbol)
        if normalized is not None:
            return normalized
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
    realized_pnl_total = 0.0
    found_realized_pnl = False
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
        realized_pnl = extract_realized_pnl(trade)
        if realized_pnl is not None:
            realized_pnl_total += realized_pnl
            found_realized_pnl = True
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
        'realized_pnl_usdt': realized_pnl_total if found_realized_pnl else None,
        'fee_ccy': sorted(set(fee_ccys)) if fee_ccys else None,
        'fee_rate': sorted(set(fee_rates)) if fee_rates else None,
        'fill_ids': fill_ids or None,
        'fill_count': len(trades),
    }


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def account_balance_summary(balance: dict[str, Any] | None, *, account_alias: str | None = None, account_label: str | None = None) -> dict[str, Any]:
    balance = balance or {}
    info = balance.get('info') if isinstance(balance.get('info'), dict) else {}

    equity = None
    unrealized_pnl = None
    usdt_available = None
    assets: list[dict[str, Any]] = []

    details = info.get('details')
    if isinstance(details, list):
        for row in details:
            if not isinstance(row, dict):
                continue
            ccy = str(row.get('ccy') or '').upper()
            if not ccy:
                continue
            eq = _safe_float(row.get('eq'))
            eq_usd = _safe_float(row.get('eqUsd'))
            avail = _safe_float(row.get('availEq') or row.get('availBal') or row.get('cashBal'))
            upl = _safe_float(row.get('upl'))
            liab = _safe_float(row.get('liab'))
            cross_liab = _safe_float(row.get('crossLiab'))
            iso_liab = _safe_float(row.get('isoLiab'))
            interest = _safe_float(row.get('interest'))
            upl_liab = _safe_float(row.get('uplLiab'))
            notional_lever = _safe_float(row.get('notionalLever'))
            assets.append({
                'asset': ccy,
                'equity': eq,
                'equity_usdt': eq_usd,
                'available': avail,
                'unrealized_pnl_usdt': upl,
                'liability': liab,
                'cross_liability': cross_liab,
                'isolated_liability': iso_liab,
                'interest': interest,
                'upl_liability': upl_liab,
                'notional_leverage': notional_lever,
                'margin_ratio': row.get('mgnRatio'),
            })
            if ccy == 'USDT':
                equity = eq_usd if eq_usd is not None else eq
                usdt_available = avail if avail is not None else eq
                unrealized_pnl = upl

    if equity is None:
        equity = _safe_float(info.get('totalEq'))
    if unrealized_pnl is None:
        unrealized_pnl = _safe_float(info.get('upl'))

    free_map = balance.get('free') if isinstance(balance.get('free'), dict) else {}
    total_map = balance.get('total') if isinstance(balance.get('total'), dict) else {}
    if usdt_available is None and 'USDT' in free_map:
        usdt_available = _safe_float(free_map.get('USDT'))
    if not assets:
        for asset in sorted({*(free_map.keys()), *(total_map.keys())}):
            total = _safe_float(total_map.get(asset))
            free = _safe_float(free_map.get(asset))
            if (total or 0.0) <= 0 and (free or 0.0) <= 0:
                continue
            assets.append({
                'asset': str(asset).upper(),
                'equity': total,
                'equity_usdt': None,
                'available': free,
                'unrealized_pnl_usdt': None,
            })

    return {
        'account_alias': account_alias,
        'account_label': account_label,
        'equity_end_usdt': equity,
        'equity_usdt': equity,
        'usdt_available': usdt_available,
        'unrealized_pnl_usdt': unrealized_pnl,
        'pnl_usdt': unrealized_pnl,
        'assets': assets,
    }


VERIFICATION_DELAYS_SECONDS = (5.0, 10.0, 20.0)
DOUBLECHECK_DELAY_SECONDS = 1.5


def verify_position_with_delays(
    exchange: Any,
    execution_symbol: str,
    *,
    delays: tuple[float, ...] = VERIFICATION_DELAYS_SECONDS,
    predicate,
    include_doublecheck: bool = False,
    doublecheck_delay: float = DOUBLECHECK_DELAY_SECONDS,
    meta_factory=None,
) -> tuple[bool, dict[str, Any] | None, list[dict[str, Any]]]:
    verification: list[dict[str, Any]] = []
    last_live = None
    for attempt, delay in enumerate(delays, start=1):
        time.sleep(delay)
        live = live_position_snapshot(exchange, execution_symbol)
        last_live = live
        matched = bool(predicate(live))
        meta = {} if meta_factory is None else dict(meta_factory(attempt, live) or {})
        verification.append({
            'attempt': attempt,
            'delay_seconds': delay,
            'live': live,
            'matched': matched,
            **meta,
        })
        if matched:
            return True, live, verification
        if include_doublecheck:
            time.sleep(doublecheck_delay)
            live_retry = live_position_snapshot(exchange, execution_symbol)
            last_live = live_retry
            matched_retry = bool(predicate(live_retry))
            retry_meta = {} if meta_factory is None else dict(meta_factory(f'{attempt}-doublecheck', live_retry) or {})
            verification.append({
                'attempt': f'{attempt}-doublecheck',
                'delay_seconds': doublecheck_delay,
                'live': live_retry,
                'matched': matched_retry,
                **retry_meta,
            })
            if matched_retry:
                return True, live_retry, verification
    return False, last_live, verification


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

    def account_balance_summary(self) -> dict[str, Any]:
        balance = self.exchange.fetch_balance()
        return account_balance_summary(balance, account_alias=self.account_alias, account_label=self.account_label)

    def trading_free_balances(self) -> dict[str, float]:
        balance = self.spot_exchange.fetch_balance()
        free_map = balance.get('free') if isinstance(balance, dict) else None
        if not isinstance(free_map, dict):
            return {}
        result: dict[str, float] = {}
        for asset, value in free_map.items():
            numeric = _safe_float(value)
            if numeric is None:
                continue
            result[str(asset).upper()] = numeric
        return result

    def non_usdt_assets(self) -> list[dict[str, Any]]:
        free_balances = OkxClient.trading_free_balances(self)
        rows = []
        for asset, amount in free_balances.items():
            if not asset or asset == 'USDT' or amount <= 0:
                continue
            rows.append({
                'asset': asset,
                'amount': amount,
                'account_alias': self.account_alias,
                'account_label': self.account_label,
            })
        if rows:
            return rows
        summary = self.account_balance_summary()
        assets = summary.get('assets') or []
        rows = []
        for row in assets:
            asset = str(row.get('asset') or '').upper()
            if not asset or asset == 'USDT':
                continue
            amount = _safe_float(row.get('available'))
            if amount is None or amount <= 0:
                amount = _safe_float(row.get('equity'))
            if amount is None or amount <= 0:
                continue
            rows.append({
                'asset': asset,
                'amount': amount,
                'account_alias': self.account_alias,
                'account_label': self.account_label,
            })
        return rows

    def margin_exposure_summary(self) -> list[dict[str, Any]]:
        summary = self.account_balance_summary()
        assets = summary.get('assets') or []
        rows = []
        for row in assets:
            asset = str(row.get('asset') or '').upper()
            if not asset:
                continue
            liability = _safe_float(row.get('liability')) or 0.0
            cross_liability = _safe_float(row.get('cross_liability')) or 0.0
            isolated_liability = _safe_float(row.get('isolated_liability')) or 0.0
            interest = _safe_float(row.get('interest')) or 0.0
            leverage = _safe_float(row.get('notional_leverage')) or 0.0
            available = _safe_float(row.get('available')) or 0.0
            equity = _safe_float(row.get('equity')) or 0.0
            if max(abs(liability), abs(cross_liability), abs(isolated_liability), abs(interest), abs(leverage)) <= 0:
                continue
            rows.append({
                'asset': asset,
                'available': available,
                'equity': equity,
                'liability': liability,
                'cross_liability': cross_liability,
                'isolated_liability': isolated_liability,
                'interest': interest,
                'notional_leverage': leverage,
                'margin_ratio': row.get('margin_ratio'),
                'account_alias': self.account_alias,
                'account_label': self.account_label,
            })
        return rows

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

    def all_live_positions(self) -> list[dict[str, Any]]:
        self.ensure_markets_loaded()
        positions = self.exchange.fetch_positions()
        rows: list[dict[str, Any]] = []
        for position in positions:
            normalized = _normalize_live_position_row(position)
            if normalized is not None:
                rows.append(normalized)
        return rows

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
            "posSide": "net",
        }
        order = self.exchange.create_order(execution_symbol, "market", order_side, amount, None, params)
        fee_usdt = extract_order_fee(order)
        realized_pnl_usdt = extract_realized_pnl(order)
        fee_meta = self.fetch_order_fees(
            execution_symbol,
            order.get('id'),
            since_ms=int(datetime.now(UTC).timestamp() * 1000) - 300000,
            side=order_side,
            amount=amount,
        )
        if fee_meta and fee_meta.get('fee_usdt') is not None:
            fee_usdt = fee_meta.get('fee_usdt')
        if fee_meta and fee_meta.get('realized_pnl_usdt') is not None:
            realized_pnl_usdt = fee_meta.get('realized_pnl_usdt')

        target_amount = float(current_open_amount or 0.0) + float(amount)
        verified_entry, live, verification = verify_position_with_delays(
            self.exchange,
            execution_symbol,
            predicate=lambda snapshot: snapshot is not None and snapshot.get('side') == signal_side and amount_close_enough(target_amount, float(snapshot.get('contracts') or 0.0)),
        )
        live_contracts = 0.0 if live is None else float(live.get('contracts') or 0.0)
        live_side = None if live is None else live.get('side')

        return {
            "symbol": symbol,
            "ccxt_symbol": execution_symbol,
            "signal_side": signal_side,
            "order_side": order_side,
            "amount": amount,
            "notional_usdt": notional_usdt,
            "reference_price": last_price,
            "fee_usdt": fee_usdt,
            "realized_pnl_usdt": realized_pnl_usdt,
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
            "posSide": "net",
            "reduceOnly": True,
        }

        orders = []
        verification = []
        total_fee_usdt = 0.0
        realized_pnl_usdt = 0.0
        fee_found = False
        realized_pnl_found = False
        verified_flat = False
        remaining_contracts = float(amount)
        remaining_side = position_side

        current_amount = float(amount)
        for attempt in range(1, 4):
            normalized_amount = normalize_contract_amount(self.exchange, execution_symbol, current_amount)
            order = self.exchange.create_order(execution_symbol, "market", order_side, normalized_amount, None, params)
            fee_usdt = extract_order_fee(order)
            order_realized_pnl_usdt = extract_realized_pnl(order)
            fee_meta = self.fetch_order_fees(
                execution_symbol,
                order.get('id'),
                since_ms=int(datetime.now(UTC).timestamp() * 1000) - 300000,
                side=order_side,
                amount=normalized_amount,
            )
            if fee_meta and fee_meta.get('fee_usdt') is not None:
                fee_usdt = fee_meta.get('fee_usdt')
            if fee_meta and fee_meta.get('realized_pnl_usdt') is not None:
                order_realized_pnl_usdt = fee_meta.get('realized_pnl_usdt')
            if fee_usdt is not None:
                total_fee_usdt += fee_usdt
                fee_found = True
            if order_realized_pnl_usdt is not None:
                realized_pnl_usdt += order_realized_pnl_usdt
                realized_pnl_found = True
            orders.append({
                'attempt': attempt,
                'order_id': order.get('id'),
                'status': order.get('status'),
                'amount': normalized_amount,
                'fee_usdt': fee_usdt,
                'realized_pnl_usdt': order_realized_pnl_usdt,
                'fee_ccy': None if fee_meta is None else fee_meta.get('fee_ccy'),
                'fee_rate': None if fee_meta is None else fee_meta.get('fee_rate'),
                'fill_ids': None if fee_meta is None else fee_meta.get('fill_ids'),
                'fill_count': None if fee_meta is None else fee_meta.get('fill_count'),
            })

            trade_confirmed = bool(fee_meta and fee_meta.get('fill_count'))
            verified_flat, live, verification_attempts = verify_position_with_delays(
                self.exchange,
                execution_symbol,
                predicate=lambda snapshot: snapshot is None,
                include_doublecheck=trade_confirmed,
                meta_factory=lambda verify_attempt, _live: {'trade_confirmed': trade_confirmed, 'order_attempt': attempt},
            )
            verification.extend(verification_attempts)
            if verified_flat:
                remaining_contracts = 0.0
                remaining_side = None
                break

            remaining_contracts = 0.0 if live is None else float(live.get('contracts') or 0.0)
            remaining_side = None if live is None else live.get('side')
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
            "realized_pnl_usdt": realized_pnl_usdt if realized_pnl_found else None,
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

        amount_str = str(amount)
        convert_error = None
        try:
            quote = self.spot_exchange.privatePostAssetConvertEstimateQuote({
                'baseCcy': asset,
                'quoteCcy': 'USDT',
                'side': 'sell',
                'rfqSz': amount_str,
                'rfqSzCcy': asset,
            })
            quote_row = ((quote or {}).get('data') or [None])[0]
            if isinstance(quote_row, dict) and quote_row.get('quoteId'):
                trade = self.spot_exchange.privatePostAssetConvertTrade({
                    'baseCcy': asset,
                    'quoteCcy': 'USDT',
                    'side': 'sell',
                    'sz': quote_row.get('rfqSz') or amount_str,
                    'szCcy': quote_row.get('rfqSzCcy') or asset,
                    'quoteId': quote_row.get('quoteId'),
                })
                trade_row = ((trade or {}).get('data') or [None])[0]
                return {
                    'asset': asset,
                    'symbol': f'{asset}/USDT',
                    'side': 'sell',
                    'amount': amount,
                    'convert': True,
                    'quote_id': quote_row.get('quoteId'),
                    'order_id': None if not isinstance(trade_row, dict) else trade_row.get('tradeId') or trade_row.get('fillId') or trade_row.get('orderId'),
                    'status': None if not isinstance(trade_row, dict) else trade_row.get('state') or trade_row.get('status'),
                    'account_alias': self.account_alias,
                    'account_label': self.account_label,
                    'raw': trade,
                }
        except Exception as exc:
            convert_error = str(exc)

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
                'convert_error': convert_error,
            }
        order = self.spot_exchange.create_order(symbol, 'market', 'sell', sell_amount, None, {'tdMode': 'cash'})
        return {
            'asset': asset,
            'symbol': symbol,
            'side': 'sell',
            'amount': sell_amount,
            'convert': False,
            'convert_error': convert_error,
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
