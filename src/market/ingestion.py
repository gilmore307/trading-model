from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Iterable

from src.config.settings import Settings
from src.exchange.okx_client import OkxClient
from src.market.hub import MarketDataHub
from src.market.models import Bar, DerivativesSnapshot, TickerSnapshot


DEFAULT_TIMEFRAMES: tuple[str, ...] = ("1m", "5m", "15m", "1h", "4h")


@dataclass(slots=True)
class PollingIngestResult:
    symbol: str
    timeframes: tuple[str, ...]
    bars_loaded: dict[str, int]
    ticker_loaded: bool
    derivatives_loaded: bool
    observed_at: datetime


class BtcPollingIngestor:
    """Phase-1 BTC-only polling ingestor.

    This is intentionally conservative: public REST snapshots first, streaming later.
    """

    def __init__(self, settings: Settings, hub: MarketDataHub, symbol: str = "BTC-USDT-SWAP"):
        self.settings = settings
        self.hub = hub
        self.symbol = symbol
        self.client = OkxClient(settings, settings.account_for_strategy("trend"))
        self._bootstrapped_derivatives = False

    def _bars_from_rows(self, rows: Iterable[list[float]]) -> list[Bar]:
        out: list[Bar] = []
        for row in rows:
            if len(row) < 6:
                continue
            ts = datetime.fromtimestamp(int(row[0]) / 1000, tz=UTC)
            out.append(
                Bar(
                    ts=ts,
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5]),
                )
            )
        return out

    def _fetch_derivatives(self) -> DerivativesSnapshot | None:
        exchange = self.client.exchange
        symbol = self.settings.ccxt_symbol(self.symbol)
        observed_at = datetime.now(UTC)

        funding_rate = None
        next_funding_time = None
        open_interest = None
        basis_pct = None
        mark = None
        index = None

        try:
            funding = exchange.fetch_funding_rate(symbol)
            funding_rate = funding.get("fundingRate")
            next_ts = funding.get("nextFundingTimestamp") or funding.get("nextFundingTime")
            if next_ts:
                next_funding_time = datetime.fromtimestamp(int(next_ts) / 1000, tz=UTC)
            mark = funding.get("markPrice") or mark
            index = funding.get("indexPrice") or index
        except Exception:
            pass

        try:
            oi = exchange.fetch_open_interest(symbol)
            open_interest = oi.get("openInterestAmount") or oi.get("openInterestValue") or oi.get("openInterest")
            open_interest = None if open_interest is None else float(open_interest)
        except Exception:
            pass

        if mark is not None and index not in (None, 0):
            try:
                basis_pct = (float(mark) - float(index)) / float(index)
            except Exception:
                basis_pct = None

        if basis_pct is None:
            try:
                mark_rows = exchange.fetch_mark_ohlcv(symbol, timeframe='1m', limit=1)
                index_rows = exchange.fetch_index_ohlcv(symbol, timeframe='1m', limit=1)
                if mark_rows and index_rows and len(mark_rows[0]) >= 5 and len(index_rows[0]) >= 5:
                    mark_close = float(mark_rows[-1][4])
                    index_close = float(index_rows[-1][4])
                    if index_close:
                        basis_pct = (mark_close - index_close) / index_close
            except Exception:
                pass

        if all(v is None for v in [funding_rate, next_funding_time, open_interest, basis_pct]):
            return None

        return DerivativesSnapshot(
            ts=observed_at,
            funding_rate=None if funding_rate is None else float(funding_rate),
            next_funding_time=next_funding_time,
            open_interest=open_interest,
            basis_pct=basis_pct,
        )

    def bootstrap_derivatives_history(self, limit: int = 60) -> int:
        exchange = self.client.exchange
        symbol = self.settings.ccxt_symbol(self.symbol)
        inserted = 0

        funding_by_ts: dict[int, dict] = {}
        oi_by_ts: dict[int, dict] = {}
        basis_by_ts: dict[int, float] = {}

        try:
            rows = exchange.fetch_funding_rate_history(symbol, limit=limit)
            for row in rows or []:
                ts = row.get('timestamp') or row.get('fundingTimestamp') or row.get('nextFundingTimestamp')
                if ts is None:
                    continue
                funding_by_ts[int(ts)] = row
        except Exception:
            pass

        try:
            rows = exchange.fetch_open_interest_history(symbol, timeframe='5m', limit=limit)
            for row in rows or []:
                ts = row.get('timestamp') or row.get('ts') or row.get('time')
                if ts is None:
                    continue
                oi_by_ts[int(ts)] = row
        except Exception:
            pass

        try:
            mark_rows = exchange.fetch_mark_ohlcv(symbol, timeframe='5m', limit=limit)
            index_rows = exchange.fetch_index_ohlcv(symbol, timeframe='5m', limit=limit)
            index_map = {int(r[0]): r for r in (index_rows or []) if len(r) >= 5}
            for row in mark_rows or []:
                if len(row) < 5:
                    continue
                ts = int(row[0])
                idx = index_map.get(ts)
                if not idx:
                    continue
                mark_close = float(row[4])
                index_close = float(idx[4])
                if index_close:
                    basis_by_ts[ts] = (mark_close - index_close) / index_close
        except Exception:
            pass

        all_ts = sorted(set(funding_by_ts) | set(oi_by_ts) | set(basis_by_ts))
        for ts in all_ts:
            funding = funding_by_ts.get(ts) or {}
            oi = oi_by_ts.get(ts) or {}
            oi_value = oi.get('openInterestAmount')
            if oi_value is None:
                oi_value = oi.get('openInterestValue')
            if oi_value is None:
                oi_value = oi.get('openInterest')
            if oi_value is None and isinstance(oi.get('info'), (list, tuple)) and len(oi.get('info')) >= 2:
                oi_value = oi.get('info')[1]

            snap = DerivativesSnapshot(
                ts=datetime.fromtimestamp(ts / 1000, tz=UTC),
                funding_rate=None if funding.get('fundingRate') is None else float(funding.get('fundingRate')),
                next_funding_time=None,
                open_interest=None if oi_value is None else float(oi_value),
                basis_pct=basis_by_ts.get(ts),
            )
            if all(v is None for v in [snap.funding_rate, snap.open_interest, snap.basis_pct]):
                continue
            self.hub.ingest_derivatives(self.symbol, snap)
            inserted += 1

        self._bootstrapped_derivatives = True
        return inserted

    def poll(self, timeframes: tuple[str, ...] = DEFAULT_TIMEFRAMES, limit: int = 300) -> PollingIngestResult:
        if not self._bootstrapped_derivatives:
            self.bootstrap_derivatives_history(limit=60)
        bars_loaded: dict[str, int] = {}
        for timeframe in timeframes:
            rows = self.client.fetch_ohlcv(self.symbol, timeframe, limit=limit)
            bars = self._bars_from_rows(rows)
            for bar in bars:
                self.hub.ingest_bar(self.symbol, timeframe, bar)
            bars_loaded[timeframe] = len(bars)

        ticker_loaded = False
        try:
            ticker = self.client.exchange.fetch_ticker(self.settings.ccxt_symbol(self.symbol))
            ts = ticker.get("timestamp")
            observed_at = datetime.fromtimestamp(int(ts) / 1000, tz=UTC) if ts else datetime.now(UTC)
            self.hub.ingest_ticker(
                self.symbol,
                TickerSnapshot(
                    ts=observed_at,
                    last=None if ticker.get("last") is None else float(ticker.get("last")),
                    bid=None if ticker.get("bid") is None else float(ticker.get("bid")),
                    ask=None if ticker.get("ask") is None else float(ticker.get("ask")),
                ),
            )
            ticker_loaded = True
        except Exception:
            pass

        derivatives_loaded = False
        derivatives = self._fetch_derivatives()
        if derivatives is not None:
            self.hub.ingest_derivatives(self.symbol, derivatives)
            if ticker_loaded:
                current = self.hub.snapshot(self.symbol).ticker
                if current is not None and derivatives.basis_pct is not None and current.last is not None:
                    current.mark = current.last * (1 + derivatives.basis_pct)
            derivatives_loaded = True

        return PollingIngestResult(
            symbol=self.symbol,
            timeframes=timeframes,
            bars_loaded=bars_loaded,
            ticker_loaded=ticker_loaded,
            derivatives_loaded=derivatives_loaded,
            observed_at=datetime.now(UTC),
        )
