from src.state.route_registry import RouteRegistry


def test_route_registry_freeze_and_enable_cycle():
    r = RouteRegistry()
    assert r.is_enabled('trend', 'BTC-USDT-SWAP') is True
    state = r.freeze('trend', 'BTC-USDT-SWAP', 'mismatch')
    assert state.enabled is False
    assert state.frozen_reason == 'mismatch'
    assert r.is_enabled('trend', 'BTC-USDT-SWAP') is False
    state = r.enable('trend', 'BTC-USDT-SWAP')
    assert state.enabled is True
    assert state.frozen_reason is None
