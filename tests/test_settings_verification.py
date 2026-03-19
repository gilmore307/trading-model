from pathlib import Path

from src.config.settings import Settings


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
        ]),
        encoding='utf-8',
    )
    settings = Settings.load(env)
    assert settings.verification_delays_seconds == [0.2, 0.4, 0.8]
    assert settings.verification_doublecheck_delay_seconds == 0.1
