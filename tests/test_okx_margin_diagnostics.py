from src.exchange.okx_client import OkxClient


class FakeClient:
    account_alias = 'trend'
    account_label = 'Trend'

    def account_balance_summary(self):
        return {
            'assets': [
                {
                    'asset': 'USDT',
                    'available': 1000.0,
                    'equity': 1000.0,
                    'liability': None,
                    'cross_liability': None,
                    'isolated_liability': None,
                    'interest': None,
                    'notional_leverage': None,
                    'margin_ratio': None,
                },
                {
                    'asset': 'BTC',
                    'available': 0.01,
                    'equity': 0.02,
                    'liability': 0.005,
                    'cross_liability': 0.004,
                    'isolated_liability': 0.0,
                    'interest': 0.0001,
                    'notional_leverage': 5.0,
                    'margin_ratio': '9.5',
                },
            ]
        }


def test_margin_exposure_summary_detects_liability_rows():
    rows = OkxClient.margin_exposure_summary(FakeClient())
    assert len(rows) == 1
    row = rows[0]
    assert row['asset'] == 'BTC'
    assert row['liability'] == 0.005
    assert row['cross_liability'] == 0.004
    assert row['notional_leverage'] == 5.0
