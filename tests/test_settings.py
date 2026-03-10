from pathlib import Path

from src.config.settings import Settings


def test_settings_loads_strategy_account_aliases_and_credentials(tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text(
        "\n".join([
            "OKX_API_KEY=default-key",
            "OKX_API_SECRET=default-secret",
            "OKX_API_PASSPHRASE=default-pass",
            "OKX_ACCOUNT_LABEL=OpenClaw1",
            "OKX_DEMO=true",
            "BREAKOUT_ACCOUNT_ALIAS=default",
            "PULLBACK_ACCOUNT_ALIAS=openclaw2",
            "MEANREV_ACCOUNT_ALIAS=openclaw3",
            "OKX_OPENCLAW2_API_KEY=key-2",
            "OKX_OPENCLAW2_API_SECRET=secret-2",
            "OKX_OPENCLAW2_API_PASSPHRASE=pass-2",
            "OKX_OPENCLAW2_ACCOUNT_LABEL=OpenClaw2",
            "OKX_OPENCLAW3_API_KEY=key-3",
            "OKX_OPENCLAW3_API_SECRET=secret-3",
            "OKX_OPENCLAW3_API_PASSPHRASE=pass-3",
            "OKX_OPENCLAW3_ACCOUNT_LABEL=OpenClaw3",
        ])
    )

    settings = Settings.load(env)

    breakout = settings.account_for_strategy("breakout")
    pullback = settings.account_for_strategy("pullback")
    meanrev = settings.account_for_strategy("meanrev")

    assert breakout.alias == "default"
    assert breakout.api_key == "default-key"
    assert breakout.label == "OpenClaw1"

    assert pullback.alias == "openclaw2"
    assert pullback.api_key == "key-2"
    assert pullback.label == "OpenClaw2"

    assert meanrev.alias == "openclaw3"
    assert meanrev.api_key == "key-3"
    assert meanrev.label == "OpenClaw3"
