from src.runner.test_mode import _require_test_symbols, opposite_side


def test_require_test_symbols_rejects_prod_symbols():
    try:
        _require_test_symbols(['BTC-USDT-SWAP'])
    except RuntimeError as exc:
        assert 'disallows production symbols' in str(exc)
    else:
        raise AssertionError('expected RuntimeError')


def test_require_test_symbols_accepts_non_prod_symbols():
    assert _require_test_symbols(['XRP-USDT-SWAP', 'DOGE-USDT-SWAP']) == ['XRP-USDT-SWAP', 'DOGE-USDT-SWAP']


def test_opposite_side_flips():
    assert opposite_side('long') == 'short'
    assert opposite_side('short') == 'long'
