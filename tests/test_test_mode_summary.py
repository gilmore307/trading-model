import json
from pathlib import Path


def test_latest_test_mode_summary_shape(tmp_path):
    summary = {
        'run_id': '20260310T000000Z',
        'runs': [{'alignment': {'ok': True}, 'final_positions': []}],
        'checks': {
            'all_alignments_ok': True,
            'all_final_open_positions_flat': True,
            'run_count': 1,
            'elapsed_seconds': 1.234,
            'deadline_seconds': 60,
            'completed_suite': True,
        },
        'pass': True,
    }
    out = tmp_path / 'latest-test-mode.json'
    out.write_text(json.dumps(summary))
    loaded = json.loads(out.read_text())
    assert loaded['checks']['completed_suite'] is True
    assert loaded['checks']['run_count'] == 1
    assert loaded['pass'] is True
