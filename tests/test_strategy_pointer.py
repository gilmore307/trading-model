from src.runtime.strategy_pointer import load_active_strategy_snapshot


def test_load_active_strategy_snapshot_returns_versioned_snapshot():
    snapshot = load_active_strategy_snapshot()
    assert snapshot.version
    assert snapshot.updated_at
    assert snapshot.source
