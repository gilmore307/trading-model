from pathlib import Path

from src.config.settings import Settings


def _clear_lookback_env(monkeypatch):
    for key in ['TREND_LOOKBACK', 'CROWDED_LOOKBACK', 'MEANREV_LOOKBACK', 'BREAKOUT_LOOKBACK', 'PULLBACK_LOOKBACK']:
        monkeypatch.delenv(key, raising=False)


def test_settings_prefers_new_lookback_env_names_but_keeps_legacy_fallbacks(tmp_path: Path, monkeypatch):
    _clear_lookback_env(monkeypatch)
    env = tmp_path / '.env'
    env.write_text(
        '\n'.join([
            'OKX_API_KEY=k',
            'OKX_API_SECRET=s',
            'OKX_API_PASSPHRASE=p',
            'OKX_DEMO=true',
            'TREND_LOOKBACK=31',
            'BREAKOUT_LOOKBACK=19',
            'CROWDED_LOOKBACK=27',
            'PULLBACK_LOOKBACK=17',
            'MEANREV_LOOKBACK=23',
        ]),
        encoding='utf-8',
    )
    settings = Settings.load(env)
    assert settings.trend_lookback == 31
    assert settings.crowded_lookback == 27
    assert settings.meanrev_lookback == 23


def test_settings_uses_legacy_lookback_names_when_new_ones_absent(tmp_path: Path, monkeypatch):
    _clear_lookback_env(monkeypatch)
    env = tmp_path / '.env'
    env.write_text(
        '\n'.join([
            'OKX_API_KEY=k',
            'OKX_API_SECRET=s',
            'OKX_API_PASSPHRASE=p',
            'OKX_DEMO=true',
            'BREAKOUT_LOOKBACK=21',
            'PULLBACK_LOOKBACK=18',
        ]),
        encoding='utf-8',
    )
    settings = Settings.load(env)
    assert settings.trend_lookback == 21
    assert settings.crowded_lookback == 18
    assert settings.meanrev_lookback == 21
