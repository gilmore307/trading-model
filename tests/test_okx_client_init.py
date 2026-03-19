from src.exchange.okx_client import OkxClient


class DummySettings:
    okx_demo = True


class DummyAccount:
    alias = 'trend'
    label = 'Trend'
    api_key = 'k'
    api_secret = 's'
    api_passphrase = 'p'


def test_okx_client_requires_explicit_account():
    try:
        OkxClient(DummySettings())
    except ValueError as exc:
        assert 'explicit StrategyAccountConfig' in str(exc)
    else:
        raise AssertionError('expected ValueError when account is omitted')
