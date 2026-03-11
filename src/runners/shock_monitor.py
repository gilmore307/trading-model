from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from src.config.settings import Settings
from src.features.engine import FeatureEngine
from src.market.hub import MarketDataHub
from src.market.ingestion import BtcPollingIngestor
from src.market.okx_ws import OkxPublicWsClient


OUT_DIR = Path('/root/.openclaw/workspace/projects/crypto-trading/logs/runtime')
OUT_DIR.mkdir(parents=True, exist_ok=True)
SHOCK_PATH = OUT_DIR / 'latest-shock.json'


@dataclass(slots=True)
class ShockMonitorOutput:
    observed_at: datetime
    symbol: str
    features: dict


class ShockMonitor:
    def __init__(self, settings: Settings | None = None, symbol: str = 'BTC-USDT-SWAP'):
        self.settings = settings or Settings.load()
        self.symbol = symbol
        self.hub = MarketDataHub()
        self.polling = BtcPollingIngestor(self.settings, self.hub, symbol=symbol)
        self.ws = OkxPublicWsClient(self.hub, symbol=symbol)
        self.feature_engine = FeatureEngine(trend_timeframe='15m', range_timeframe='15m', event_timeframe='1m', layer_name='event_1m')

    async def run(self, seconds: int = 20) -> ShockMonitorOutput:
        self.polling.poll()
        task = asyncio.create_task(self.ws.run_forever())
        try:
            await asyncio.sleep(seconds)
        finally:
            self.ws.stop()
            await asyncio.sleep(0.2)
            task.cancel()
            try:
                await task
            except Exception:
                pass
        snap = self.hub.snapshot(self.symbol)
        features = self.feature_engine.build(snap)
        out = ShockMonitorOutput(observed_at=datetime.now(UTC), symbol=self.symbol, features=asdict(features))
        SHOCK_PATH.write_text(json.dumps(asdict(out), indent=2, default=str, ensure_ascii=False))
        return out


async def amain() -> None:
    monitor = ShockMonitor()
    out = await monitor.run(seconds=20)
    print(json.dumps(asdict(out), indent=2, default=str, ensure_ascii=False))


def main() -> None:
    asyncio.run(amain())


if __name__ == '__main__':
    main()
