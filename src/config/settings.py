from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field


DEFAULT_SYMBOLS = ["BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP"]
DEFAULT_STRATEGIES = ["trend", "crowded", "meanrev", "compression", "realtime"]
DEFAULT_STRATEGY_SYMBOLS = {
    "trend": {
        "BTC-USDT-SWAP": "BTC/USDT:USDT",
        "ETH-USDT-SWAP": "ETH/USDT:USDT",
        "SOL-USDT-SWAP": "SOL/USDT:USDT",
    },
    "crowded": {
        "BTC-USDT-SWAP": "BTC/USDT:USDT",
        "ETH-USDT-SWAP": "ETH/USDT:USDT",
        "SOL-USDT-SWAP": "SOL/USDT:USDT",
    },
    "meanrev": {
        "BTC-USDT-SWAP": "BTC/USDT:USDT",
        "ETH-USDT-SWAP": "ETH/USDT:USDT",
        "SOL-USDT-SWAP": "SOL/USDT:USDT",
    },
    "compression": {
        "BTC-USDT-SWAP": "BTC/USDT:USDT",
        "ETH-USDT-SWAP": "ETH/USDT:USDT",
        "SOL-USDT-SWAP": "SOL/USDT:USDT",
    },
    "realtime": {
        "BTC-USDT-SWAP": "BTC/USDT:USDT",
        "ETH-USDT-SWAP": "ETH/USDT:USDT",
        "SOL-USDT-SWAP": "SOL/USDT:USDT",
    },
}
DEFAULT_STRATEGY_ACCOUNT_ALIASES = {
    "trend": "trend",
    "crowded": "crowded",
    "meanrev": "meanrev",
    "compression": "compression",
    "realtime": "realtime",
}


class StrategyAccountConfig(BaseModel):
    alias: str
    api_key: str
    api_secret: str
    api_passphrase: str
    label: str | None = None


class Settings(BaseModel):
    okx_api_key: str = Field(alias="OKX_API_KEY")
    okx_api_secret: str = Field(alias="OKX_API_SECRET")
    okx_api_passphrase: str = Field(alias="OKX_API_PASSPHRASE")
    okx_demo: bool = Field(alias="OKX_DEMO")
    discord_channel: str | None = Field(default=None, alias="OPENCLAW_DISCORD_CHANNEL")
    discord_bot_token: str | None = Field(default=None, alias="DISCORD_BOT_TOKEN")
    discord_webhook_url: str | None = Field(default=None, alias="DISCORD_WEBHOOK_URL")
    notify_runtime_warnings: bool = Field(default=False, alias="NOTIFY_RUNTIME_WARNINGS")

    symbols: list[str] = DEFAULT_SYMBOLS.copy()
    strategies: list[str] = DEFAULT_STRATEGIES.copy()
    strategy_symbols: dict[str, dict[str, str]] = DEFAULT_STRATEGY_SYMBOLS.copy()
    strategy_account_aliases: dict[str, str] = DEFAULT_STRATEGY_ACCOUNT_ALIASES.copy()
    strategy_accounts: dict[str, StrategyAccountConfig] = {}
    timeframe: str = "5m"
    breakout_lookback: int = 20
    pullback_lookback: int = 20
    meanrev_lookback: int = 20
    meanrev_threshold: float = 0.015
    signal_cooldown_bars: int = 12
    risk_per_trade_fraction: float = 0.01
    min_stop_distance_ratio: float = 0.003
    atr_lookback: int = 14
    stop_atr_multiple: float = 1.5
    bucket_initial_capital_usdt: float = 20000.0
    buffer_capital_usdt: float = 500.0
    reset_equity_threshold_usdt: float = 66000.0
    default_order_size_usdt: float = 100.0
    test_symbols: list[str] = ["XRP-USDT-SWAP"]
    test_strategy: str = "trend"
    test_account_alias: str = "trend"
    test_duration_minutes: int = 10
    test_action_interval_seconds: float = 2.0
    test_entry_usdt: float = 120.0
    test_add_usdt: float = 180.0
    test_add_count: int = 3
    test_cycles: int = 6
    test_reverse_signal: bool = True
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

    def account_for_strategy(self, strategy_name: str) -> StrategyAccountConfig:
        alias = self.strategy_account_aliases.get(strategy_name, "default")
        if alias not in self.strategy_accounts:
            raise KeyError(f"No strategy account configured for strategy={strategy_name}, alias={alias}")
        return self.strategy_accounts[alias]

    def strategy_for_account_alias(self, account_alias: str | None) -> str | None:
        if not account_alias:
            return None
        for strategy, alias in self.strategy_account_aliases.items():
            if alias == account_alias:
                return strategy
        return None

    def display_name_for_account_alias(self, account_alias: str | None) -> str:
        strategy = self.strategy_for_account_alias(account_alias)
        if strategy:
            return strategy
        return account_alias or "unknown"

    @classmethod
    def load(cls, env_path: str | Path | None = None) -> "Settings":
        path = Path(env_path or Path('/root/.openclaw/workspace/projects/crypto-trading/.env'))
        load_dotenv(path, override=True)

        symbols_raw = os.getenv("SYMBOLS", "")
        strategies_raw = os.getenv("STRATEGIES", "")
        symbols = [item.strip() for item in symbols_raw.split(",") if item.strip()]
        strategies = [item.strip() for item in strategies_raw.split(",") if item.strip()]

        default_account = {
            "alias": "trend",
            "api_key": os.getenv("OKX_TREND_API_KEY", os.getenv("OKX_BREAKOUT_API_KEY", os.getenv("OKX_API_KEY", ""))),
            "api_secret": os.getenv("OKX_TREND_API_SECRET", os.getenv("OKX_BREAKOUT_API_SECRET", os.getenv("OKX_API_SECRET", ""))),
            "api_passphrase": os.getenv("OKX_TREND_API_PASSPHRASE", os.getenv("OKX_BREAKOUT_API_PASSPHRASE", os.getenv("OKX_API_PASSPHRASE", ""))),
            "label": os.getenv("OKX_TREND_ACCOUNT_LABEL", os.getenv("OKX_ACCOUNT_LABEL", "Trend")),
        }
        strategy_account_aliases = {
            "trend": os.getenv("BREAKOUT_ACCOUNT_ALIAS", "trend"),
            "crowded": os.getenv("PULLBACK_ACCOUNT_ALIAS", "crowded"),
            "meanrev": os.getenv("MEANREV_ACCOUNT_ALIAS", "meanrev"),
            "compression": os.getenv("COMPRESSION_ACCOUNT_ALIAS", "compression"),
            "realtime": os.getenv("REALTIME_ACCOUNT_ALIAS", "realtime"),
        }
        strategy_accounts = {
            "trend": default_account,
        }
        for alias in sorted(set(strategy_account_aliases.values())):
            if alias == "trend":
                continue
            prefix = alias.upper()
            strategy_accounts[alias] = {
                "alias": alias,
                "api_key": os.getenv(f"OKX_{prefix}_API_KEY", ""),
                "api_secret": os.getenv(f"OKX_{prefix}_API_SECRET", ""),
                "api_passphrase": os.getenv(f"OKX_{prefix}_API_PASSPHRASE", ""),
                "label": os.getenv(f"OKX_{prefix}_ACCOUNT_LABEL", alias),
            }

        data = {
            "OKX_API_KEY": os.getenv("OKX_API_KEY", ""),
            "OKX_API_SECRET": os.getenv("OKX_API_SECRET", ""),
            "OKX_API_PASSPHRASE": os.getenv("OKX_API_PASSPHRASE", ""),
            "OKX_DEMO": str(os.getenv("OKX_DEMO", "")).strip().lower() in {"1", "true", "yes", "on"},
            "OPENCLAW_DISCORD_CHANNEL": os.getenv("OPENCLAW_DISCORD_CHANNEL"),
            "DISCORD_BOT_TOKEN": os.getenv("DISCORD_BOT_TOKEN", os.getenv("CHANNELS_DISCORD_TOKEN")),
            "DISCORD_WEBHOOK_URL": os.getenv("DISCORD_WEBHOOK_URL"),
            "NOTIFY_RUNTIME_WARNINGS": str(os.getenv("NOTIFY_RUNTIME_WARNINGS", "false")).strip().lower() in {"1", "true", "yes", "on"},
            "symbols": symbols or DEFAULT_SYMBOLS.copy(),
            "strategies": strategies or DEFAULT_STRATEGIES.copy(),
            "strategy_symbols": DEFAULT_STRATEGY_SYMBOLS.copy(),
            "strategy_account_aliases": strategy_account_aliases,
            "strategy_accounts": strategy_accounts,
            "timeframe": os.getenv("TIMEFRAME", "5m"),
            "breakout_lookback": int(os.getenv("BREAKOUT_LOOKBACK", "20")),
            "pullback_lookback": int(os.getenv("PULLBACK_LOOKBACK", os.getenv("BREAKOUT_LOOKBACK", "20"))),
            "meanrev_lookback": int(os.getenv("MEANREV_LOOKBACK", os.getenv("BREAKOUT_LOOKBACK", "20"))),
            "meanrev_threshold": float(os.getenv("MEANREV_THRESHOLD", "0.015")),
            "signal_cooldown_bars": int(os.getenv("SIGNAL_COOLDOWN_BARS", "12")),
            "risk_per_trade_fraction": float(os.getenv("RISK_PER_TRADE_FRACTION", "0.01")),
            "min_stop_distance_ratio": float(os.getenv("MIN_STOP_DISTANCE_RATIO", "0.003")),
            "atr_lookback": int(os.getenv("ATR_LOOKBACK", "14")),
            "stop_atr_multiple": float(os.getenv("STOP_ATR_MULTIPLE", "1.5")),
            "bucket_initial_capital_usdt": float(os.getenv("BUCKET_INITIAL_CAPITAL_USDT", "20000")),
            "buffer_capital_usdt": float(os.getenv("BUFFER_CAPITAL_USDT", "500")),
            "reset_equity_threshold_usdt": float(os.getenv("RESET_EQUITY_THRESHOLD_USDT", "66000")),
            "default_order_size_usdt": float(os.getenv("DEFAULT_ORDER_SIZE_USDT", "100")),
            "test_symbols": [item.strip() for item in os.getenv("TEST_SYMBOLS", "XRP-USDT-SWAP").split(",") if item.strip()],
            "test_strategy": os.getenv("TEST_STRATEGY", "trend"),
            "test_account_alias": os.getenv("TEST_ACCOUNT_ALIAS", "trend"),
            "test_duration_minutes": int(os.getenv("TEST_DURATION_MINUTES", "10")),
            "test_action_interval_seconds": float(os.getenv("TEST_ACTION_INTERVAL_SECONDS", "2")),
            "test_entry_usdt": float(os.getenv("TEST_ENTRY_USDT", "120")),
            "test_add_usdt": float(os.getenv("TEST_ADD_USDT", "180")),
            "test_add_count": int(os.getenv("TEST_ADD_COUNT", "3")),
            "test_cycles": int(os.getenv("TEST_CYCLES", "6")),
            "test_reverse_signal": str(os.getenv("TEST_REVERSE_SIGNAL", "true")).strip().lower() in {"1", "true", "yes", "on"},
            "dry_run": str(os.getenv("DRY_RUN", "true")).strip().lower() in {"1", "true", "yes", "on"},
            "confirm_real_trading": str(os.getenv("CONFIRM_REAL_TRADING", "false")).strip().lower() in {"1", "true", "yes", "on"},
        }
        return cls.model_validate(data)

    def ensure_demo_only(self) -> None:
        if not self.okx_demo:
            raise RuntimeError("Refusing to run: OKX_DEMO is not enabled. Demo-only safeguard is active.")
