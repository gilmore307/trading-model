from datetime import UTC, datetime

from src.runtime.strategy_pointer import ActiveStrategySnapshot


def test_active_strategy_snapshot_can_carry_promotion_metadata():
    now = datetime.now(UTC).isoformat()
    snapshot = ActiveStrategySnapshot(
        version='v3',
        updated_at=now,
        source='manual_promotion',
        metadata={
            'family': 'breakout',
            'config_path': 'artifacts/strategy-v3.json',
            'promoted_at': now,
            'promotion_note': 'promote breakout v3',
        },
    )
    assert snapshot.version == 'v3'
    assert snapshot.metadata['family'] == 'breakout'
    assert snapshot.metadata['config_path'].endswith('strategy-v3.json')
