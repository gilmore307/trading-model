from pathlib import Path


def test_strategy_handover_marker_path_name():
    path = Path('/root/.openclaw/workspace/projects/crypto-trading/logs/runtime/latest-strategy-handover-marker.json')
    assert path.name == 'latest-strategy-handover-marker.json'
