from src.review.reset_orchestrator import equity_report


class FakeSpotExchange:
    def __init__(self, balance, tickers):
        self._balance = balance
        self._tickers = tickers

    def fetch_balance(self):
        return self._balance

    def fetch_ticker(self, symbol):
        return self._tickers[symbol]


class FakeClient:
    def __init__(self, alias, label, balance, tickers):
        self.account_alias = alias
        self.account_label = label
        self.spot_exchange = FakeSpotExchange(balance, tickers)


class FakeSettings:
    strategies = ['breakout', 'pullback', 'meanrev']
    reset_equity_threshold_usdt = 66000.0


class FakeRegistry:
    def __init__(self, settings):
        self._clients = {
            'breakout': FakeClient('default', 'OpenClaw1', {'total': {'USDT': 70000.0}}, {}),
            'pullback': FakeClient('openclaw2', 'OpenClaw2', {'total': {'USDT': 65000.0}}, {}),
            'meanrev': FakeClient('openclaw3', 'OpenClaw3', {'total': {'BTC': 1.0, 'USDT': 1000.0}}, {'BTC/USDT': {'last': 68000.0}}),
        }

    def for_strategy(self, strategy):
        return self._clients[strategy]


def test_equity_report_flags_accounts_below_threshold(monkeypatch):
    monkeypatch.setattr('src.review.reset_orchestrator.OkxClientRegistry', FakeRegistry)
    report = equity_report(FakeSettings())

    assert report['all_accounts_ok'] is False
    below = {row['account_alias'] for row in report['below_threshold_accounts']}
    assert below == {'openclaw2'}


def test_equity_report_marks_all_ok_when_each_account_meets_threshold(monkeypatch):
    class RegistryAllOk(FakeRegistry):
        def __init__(self, settings):
            self._clients = {
                'breakout': FakeClient('default', 'OpenClaw1', {'total': {'USDT': 70000.0}}, {}),
                'pullback': FakeClient('openclaw2', 'OpenClaw2', {'total': {'USDT': 66000.0}}, {}),
                'meanrev': FakeClient('openclaw3', 'OpenClaw3', {'total': {'BTC': 1.0}}, {'BTC/USDT': {'last': 70000.0}}),
            }

    monkeypatch.setattr('src.review.reset_orchestrator.OkxClientRegistry', RegistryAllOk)
    report = equity_report(FakeSettings())

    assert report['all_accounts_ok'] is True
    assert report['below_threshold_accounts'] == []
