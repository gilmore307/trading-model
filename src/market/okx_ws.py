from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable, Iterable

import websockets

from src.market.hub import MarketDataHub
from src.market.streaming import ShockStreamAdapter


OKX_PUBLIC_WS_URL = 'wss://ws.okx.com:8443/ws/v5/public'


@dataclass(slots=True)
class OkxWsSubscription:
    channel: str
    inst_id: str

    def to_arg(self) -> dict[str, str]:
        return {'channel': self.channel, 'instId': self.inst_id}


class OkxPublicWsClient:
    """Minimal OKX public websocket client for shock ingestion.

    Phase 1 target channels:
    - trades
    - bbo-tbt (fallback to tickers if needed by caller)
    - liquidations (if exchange emits them on the chosen endpoint/account permissions)
    """

    def __init__(self, hub: MarketDataHub, symbol: str = 'BTC-USDT-SWAP', url: str = OKX_PUBLIC_WS_URL):
        self.hub = hub
        self.symbol = symbol
        self.url = url
        self.adapter = ShockStreamAdapter()
        self._stop = asyncio.Event()

    def default_subscriptions(self) -> list[OkxWsSubscription]:
        return [
            OkxWsSubscription(channel='trades', inst_id=self.symbol),
            OkxWsSubscription(channel='bbo-tbt', inst_id=self.symbol),
            OkxWsSubscription(channel='liquidation-orders', inst_id=self.symbol),
        ]

    async def subscribe(self, ws, subs: Iterable[OkxWsSubscription]) -> None:
        payload = {'op': 'subscribe', 'args': [x.to_arg() for x in subs]}
        await ws.send(json.dumps(payload))

    def _parse_ts(self, raw) -> datetime:
        if raw is None:
            return datetime.now(UTC)
        try:
            return datetime.fromtimestamp(int(raw) / 1000, tz=UTC)
        except Exception:
            return datetime.now(UTC)

    def handle_message(self, raw_text: str) -> None:
        try:
            msg = json.loads(raw_text)
        except Exception:
            return
        arg = msg.get('arg') or {}
        channel = arg.get('channel')
        data = msg.get('data') or []
        if not channel or not isinstance(data, list):
            return

        if channel == 'trades':
            trades = []
            for row in data:
                price = row.get('px')
                size = row.get('sz')
                side = row.get('side')
                if price is None or size is None:
                    continue
                trade = self.adapter.normalize_trade(price=float(price), size=float(size), side=side)
                trade.ts = self._parse_ts(row.get('ts'))
                trades.append(trade)
            if trades:
                self.hub.ingest_realtime_batch(self.symbol, trades=trades)
            return

        if channel == 'bbo-tbt':
            if not data:
                return
            row = data[-1]
            bids = row.get('bids') or []
            asks = row.get('asks') or []
            if not bids or not asks:
                return
            bid = bids[0]
            ask = asks[0]
            top = self.adapter.normalize_top(
                bid_price=float(bid[0]),
                bid_size=float(bid[1]),
                ask_price=float(ask[0]),
                ask_size=float(ask[1]),
            )
            top.ts = self._parse_ts(row.get('ts'))
            self.hub.ingest_realtime_batch(self.symbol, top=top)
            return

        if channel == 'liquidation-orders':
            events = []
            for row in data:
                details = row.get('details') or []
                if details:
                    for d in details:
                        side = d.get('side')
                        price = d.get('bkPx') or d.get('px')
                        size = d.get('sz')
                        notional = None
                        try:
                            if price is not None and size is not None:
                                notional = float(price) * float(size)
                        except Exception:
                            notional = None
                        event = self.adapter.normalize_liquidation(
                            side=side,
                            price=None if price is None else float(price),
                            size=None if size is None else float(size),
                            notional=notional,
                        )
                        event.ts = self._parse_ts(d.get('ts') or row.get('ts'))
                        events.append(event)
                else:
                    side = row.get('side')
                    price = row.get('bkPx') or row.get('px')
                    size = row.get('sz')
                    notional = None
                    try:
                        if price is not None and size is not None:
                            notional = float(price) * float(size)
                    except Exception:
                        notional = None
                    event = self.adapter.normalize_liquidation(
                        side=side,
                        price=None if price is None else float(price),
                        size=None if size is None else float(size),
                        notional=notional,
                    )
                    event.ts = self._parse_ts(row.get('ts'))
                    events.append(event)
            if events:
                self.hub.ingest_realtime_batch(self.symbol, liquidations=events)
            return

    async def run_forever(self) -> None:
        while not self._stop.is_set():
            try:
                async with websockets.connect(self.url, ping_interval=20, ping_timeout=20) as ws:
                    await self.subscribe(ws, self.default_subscriptions())
                    while not self._stop.is_set():
                        msg = await ws.recv()
                        self.handle_message(msg)
            except Exception:
                await asyncio.sleep(2)

    def stop(self) -> None:
        self._stop.set()
