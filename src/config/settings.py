from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field


DEFAULT_SYMBOLS = ["BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP"]
DEFAULT_STRATEGIES = ["breakout", "pullback", "meanrev"]
DEFAULT_STRATEGY_SYMBOLS = {
    "breakout": {
        "BTC-USDT-SWAP": "BTC/USDT:USDT",
        "ETH-USDT-SWAP": "ETH/USDT:USDT",
        "SOL-USDT-SWAP": "SOL/USDT:USDT",
    },
    "pullback": {
        "BTC-USDT-SWAP": "BTC/USDT:USDT",
        "ETH-USDT-SWAP": "ETH/USDT:USDT",
        "SOL-USDT-SWAP": "SOL/USDT:USDT",
    },
    "meanrev": {
        "BTC-USDT-SWAP": "BTC/USDT:USDT",
        "ETH-USDT-SWAP": "ETH/USDT:USDT",
        "SOL-USDT-SWAP": "SOL/USDT:USDT",
    },
}


class Settings(BaseModel):
    okx_api_key: str = Field(alias="OKX_API_KEY")
    okx_api_secret: str = Field(alias="OKX_API_SECRET")
    okx_api_passphrase: str = Field(alias="OKX_API_PASSPHRASE")
    okx_demo: bool = Field(alias="OKX_DEMO")
    discord_channel: str | None = Field(default=None, alias="OPENCLAW_DISCORD_CHANNEL")

    symbols: list[str] = DEFAULT_SYMBOLS.copy()
    strategies: list[str] = DEFAULT_STRATEGIES.copy()
    strategy_symbols: dict[str, dict[str, str]] = DEFAULT_STRATEGY_SYMBOLS.copy()
    timeframe: str = "5m"
    breakout_lookback: int = 20
    pullback_lookback: int = 20
    meanrev_lookback: int = 20
    meanrev_threshold: float = 0.015
    signal_cooldown_bars: int = 12
    bucket_initial_capital_usdt: float = 500.0
    buffer_capital_usdt: float = 500.0
    default_order_size_usdt: float = 100.0
    dry_run: bool = True
    confirm_real_trading: bool = False

    def ccxt_symbol(self, raw_symbol: str) -> str:
        if ":" in raw_symbol and "/" in raw_symbol:
            return raw_symbol
        if raw_symbol.endswith("-USDT-SWAP"):
            base = raw_symbol.removesuffix("-USDT-SWAP")
            return f"{base}/USDT:USDT"
        return raw_symbol

    def execution_symbol(self, strategy_name: str, symbol: str) -> str:
        mapped = self.strategy_symbols.get(strategy_name, {}).get(symbol, symbol)
        return self.ccxt_symbol(mapped)

    @classmethod
    def load(cls, env_path: str | Path | None = None) -> "Settings":
        path = Path(env_path or Path.home() / "openclaw-automation" / ".env")
        load_dotenv(path)

        symbols_raw = os.getenv("SYMBOLS", "")
        strategies_raw = os.getenv("STRATEGIES", "")
        symbols = [item.strip() for item in symbols_raw.split(",") if item.strip()]
        strategies = [item.strip() for item in strategies_raw.split(",") if item.strip()]

        data = {
            "OKX_API_KEY": os.getenv("OKX_API_KEY", ""),
            "OKX_API_SECRET": os.getenv("OKX_API_SECRET", ""),
            "OKX_API_PASSPHRASE": os.getenv("OKX_API_PASSPHRASE", ""),
            "OKX_DEMO": str(os.getenv("OKX_DEMO", "")).strip().lower() in {"1", "true", "yes", "on"},
            "OPENCLAW_DISCORD_CHANNEL": os.getenv("OPENCLAW_DISCORD_CHANNEL"),
            "symbols": symbols or DEFAULT_SYMBOLS.copy(),
            "strategies": strategies or DEFAULT_STRATEGIES.copy(),
            "strategy_symbols": DEFAULT_STRATEGY_SYMBOLS.copy(),
            "timeframe": os.getenv("TIMEFRAME", "5m"),
            "breakout_lookback": int(os.getenv("BREAKOUT_LOOKBACK", "20")),
            "pullback_lookback": int(os.getenv("PULLBACK_LOOKBACK", os.getenv("BREAKOUT_LOOKBACK", "20"))),
            "meanrev_lookback": int(os.getenv("MEANREV_LOOKBACK", os.getenv("BREAKOUT_LOOKBACK", "20"))),
            "meanrev_threshold": float(os.getenv("MEANREV_THRESHOLD", "0.015")),
            "signal_cooldown_bars": int(os.getenv("SIGNAL_COOLDOWN_BARS", "12")),
            "bucket_initial_capital_usdt": float(os.getenv("BUCKET_INITIAL_CAPITAL_USDT", "500")),
            "buffer_capital_usdt": float(os.getenv("BUFFER_CAPITAL_USDT", "500")),
            "default_order_size_usdt": float(os.getenv("DEFAULT_ORDER_SIZE_USDT", "100")),
            "dry_run": str(os.getenv("DRY_RUN", "true")).strip().lower() in {"1", "true", "yes", "on"},
            "confirm_real_trading": str(os.getenv("CONFIRM_REAL_TRADING", "false")).strip().lower() in {"1", "true", "yes", "on"},
        }
        return cls.model_validate(data)

    def ensure_demo_only(self) -> None:
        if not self.okx_demo:
            raise RuntimeError("Refusing to run: OKX_DEMO is not enabled. Demo-only safeguard is active.")
