from pathlib import Path

from src.config.settings import Settings
from src.execution.pipeline import ExecutionPipeline


def test_settings_loads_verification_schedule_from_env(tmp_path: Path):
    env = tmp_path / '.env'
    env.write_text(
        '\n'.join([
            'OKX_API_KEY=k',
            'OKX_API_SECRET=s',
            'OKX_API_PASSPHRASE=p',
            'OKX_DEMO=true',
            'VERIFICATION_DELAYS_SECONDS=0.2,0.4,0.8',
            'VERIFICATION_DOUBLECHECK_DELAY_SECONDS=0.1',
            'VERIFICATION_CYCLE_TIMEOUT=5',
        ]),
        encoding='utf-8',
    )
    settings = Settings.load(env)
    assert settings.verification_delays_seconds == [0.2, 0.4, 0.8]
    assert settings.verification_doublecheck_delay_seconds == 0.1
    assert settings.verification_cycle_timeout == 5


def test_settings_prefers_new_strategy_alias_env_names_but_keeps_legacy_fallbacks(tmp_path: Path):
    env = tmp_path / '.env'
    env.write_text(
        '\n'.join([
            'OKX_API_KEY=k',
            'OKX_API_SECRET=s',
            'OKX_API_PASSPHRASE=p',
            'OKX_DEMO=true',
            'TREND_ACCOUNT_ALIAS=trend-new',
            'BREAKOUT_ACCOUNT_ALIAS=trend-legacy',
            'CROWDED_ACCOUNT_ALIAS=crowded-new',
            'PULLBACK_ACCOUNT_ALIAS=crowded-legacy',
        ]),
        encoding='utf-8',
    )
    settings = Settings.load(env)
    assert settings.strategy_account_aliases['trend'] == 'trend-new'
    assert settings.strategy_account_aliases['crowded'] == 'crowded-new'


def test_execution_pipeline_injects_verification_cycle_timeout_from_settings(tmp_path: Path):
    env = tmp_path / '.env'
    env.write_text(
        '\n'.join([
            'OKX_API_KEY=k',
            'OKX_API_SECRET=s',
            'OKX_API_PASSPHRASE=p',
            'OKX_DEMO=true',
            'VERIFICATION_CYCLE_TIMEOUT=7',
        ]),
        encoding='utf-8',
    )
    settings = Settings.load(env)
    pipeline = ExecutionPipeline(settings=settings)
    assert pipeline.controller.verification_cycle_timeout == 7
