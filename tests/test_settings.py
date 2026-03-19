from pathlib import Path

from src.config.settings import Settings


def test_settings_loads_strategy_account_aliases_and_credentials(tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text(
        "\n".join([
            "OKX_API_KEY=default-key",
            "OKX_API_SECRET=default-secret",
            "OKX_API_PASSPHRASE=default-pass",
            "OKX_ACCOUNT_LABEL=Trend",
            "OKX_DEMO=true",
            "TREND_ACCOUNT_ALIAS=trend",
            "CROWDED_ACCOUNT_ALIAS=crowded",
            "MEANREV_ACCOUNT_ALIAS=meanrev",
            "OKX_TREND_API_KEY=default-key",
            "OKX_TREND_API_SECRET=default-secret",
            "OKX_TREND_API_PASSPHRASE=default-pass",
            "OKX_TREND_ACCOUNT_LABEL=Trend",
            "OKX_CROWDED_API_KEY=key-2",
            "OKX_CROWDED_API_SECRET=secret-2",
            "OKX_CROWDED_API_PASSPHRASE=pass-2",
            "OKX_CROWDED_ACCOUNT_LABEL=Crowded",
            "OKX_MEANREV_API_KEY=key-3",
            "OKX_MEANREV_API_SECRET=secret-3",
            "OKX_MEANREV_API_PASSPHRASE=pass-3",
            "OKX_MEANREV_ACCOUNT_LABEL=Meanrev",
        ])
    )

    settings = Settings.load(env)

    trend = settings.account_for_strategy("trend")
    crowded = settings.account_for_strategy("crowded")
    meanrev = settings.account_for_strategy("meanrev")

    assert trend.alias == "trend"
    assert trend.api_key == "default-key"
    assert trend.label == "Trend"

    assert crowded.alias == "crowded"
    assert crowded.api_key == "key-2"
    assert crowded.label == "Crowded"

    assert meanrev.alias == "meanrev"
    assert meanrev.api_key == "key-3"
    assert meanrev.label == "Meanrev"
    assert settings.bucket_initial_capital_usdt == 20000.0
    assert settings.reset_equity_threshold_usdt == 66000.0
    assert settings.test_symbols == ['XRP-USDT-SWAP']
    assert settings.test_strategy == 'trend'
    assert settings.test_account_alias == 'trend'
    assert settings.test_duration_minutes == 10
