from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
import asyncio
import json

from src.config.settings import Settings
from src.market.hub import MarketDataHub
from src.market.ingestion import BtcPollingIngestor
from src.market.okx_ws import OkxPublicWsClient
from src.regimes.layered_classifier import LayeredRegimeClassifier
from src.routing.router import summarize_decision, route_regime


OUT_DIR = Path('/root/.openclaw/workspace/projects/crypto-trading/logs/runtime')
OUT_DIR.mkdir(parents=True, exist_ok=True)
LATEST_PATH = OUT_DIR / 'latest-regime.json'


@dataclass(slots=True)
class RegimeRunnerOutput:
    observed_at: datetime
    symbol: str
    background_4h: dict
    primary_15m: dict
    override_1m: dict | None
    background_features: dict
    primary_features: dict
    override_features: dict
    final_decision: dict
    route_decision: dict
    decision_summary: dict = field(default_factory=dict)


class BtcRegimeRunner:
    def __init__(self, settings: Settings | None = None, symbol: str = 'BTC-USDT-SWAP'):
        self.settings = settings or Settings.load()
        self.symbol = symbol
        self.hub = MarketDataHub()
        self.ingestor = BtcPollingIngestor(self.settings, self.hub, symbol=symbol)
        self.ws = OkxPublicWsClient(self.hub, symbol=symbol)
        self.layered = LayeredRegimeClassifier()

    def _decision_dict(self, decision):
        if decision is None:
            return None
        return {
            'primary': decision.primary.value,
            'confidence': decision.confidence,
            'reasons': decision.reasons,
            'secondary': [x.value for x in decision.secondary],
            'tradable': decision.tradable,
        }

    def _build_output(self) -> RegimeRunnerOutput:
        snapshot = self.hub.snapshot(self.symbol)
        layered = self.layered.classify(snapshot)
        route = route_regime(layered.final.primary)
        summary = summarize_decision(layered.final, route)
        payload = RegimeRunnerOutput(
            observed_at=datetime.now(UTC),
            symbol=self.symbol,
            background_4h=self._decision_dict(layered.background_4h),
            primary_15m=self._decision_dict(layered.primary_15m),
            override_1m=self._decision_dict(layered.override_1m),
            background_features=asdict(layered.background_features),
            primary_features=asdict(layered.primary_features),
            override_features=asdict(layered.override_features),
            final_decision=self._decision_dict(layered.final),
            route_decision=asdict(route),
            decision_summary=asdict(summary),
        )
        LATEST_PATH.write_text(json.dumps(asdict(payload), indent=2, default=str, ensure_ascii=False))
        return payload

    def run_once(self) -> RegimeRunnerOutput:
        self.ingestor.poll()
        return self._build_output()

    async def run_with_shock_window(self, seconds: int = 10) -> RegimeRunnerOutput:
        self.ingestor.poll()
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
        return self._build_output()


async def amain() -> None:
    runner = BtcRegimeRunner()
    payload = await runner.run_with_shock_window(seconds=10)
    print(json.dumps(asdict(payload), indent=2, default=str, ensure_ascii=False))


def main() -> None:
    asyncio.run(amain())


if __name__ == '__main__':
    main()
