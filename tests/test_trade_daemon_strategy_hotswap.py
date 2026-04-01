from datetime import UTC, datetime

from src.runtime.strategy_pointer import ActiveStrategySnapshot


def test_active_strategy_snapshot_metadata_shape():
    snapshot = ActiveStrategySnapshot(
        version='v2',
        updated_at=datetime.now(UTC).isoformat(),
        source='test',
        metadata={
            'family': 'trend',
            'config_path': 'configs/strategy-v2.json',
            'promoted_at': datetime.now(UTC).isoformat(),
            'promotion_note': 'weekly promotion',
        },
    )
    assert snapshot.metadata['family'] == 'trend'
    assert 'config_path' in snapshot.metadata
    assert 'promoted_at' in snapshot.metadata
    assert 'promotion_note' in snapshot.metadata
