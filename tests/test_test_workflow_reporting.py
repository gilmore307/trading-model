import json
from pathlib import Path

from src.runtime.workflows import TEST_REPORT_JSON, TEST_REPORT_MD


def test_test_workflow_report_paths_are_runtime_logs():
    assert TEST_REPORT_JSON.name == 'latest-test-summary.json'
    assert TEST_REPORT_MD.name == 'latest-test-summary.md'
    assert 'logs/runtime' in str(TEST_REPORT_JSON)
    assert 'logs/runtime' in str(TEST_REPORT_MD)


def test_test_workflow_markdown_shape(tmp_path: Path):
    payload = {
        'generated_at': '2026-03-19T00:00:00+00:00',
        'account_alias': 'trend',
        'symbol': 'XRP-USDT-SWAP',
        'test_cycles': 2,
        'entry_count': 2,
        'add_count': 4,
        'exit_count': 2,
        'cycles': [
            {'cycle': 1, 'side': 'long', 'entry': {'order_id': 'e1'}, 'exit': {'order_id': 'x1'}},
            {'cycle': 2, 'side': 'short', 'entry': {'order_id': 'e2'}, 'exit': {'skipped': True}},
        ],
    }
    p = tmp_path / 'latest-test-summary.json'
    p.write_text(json.dumps(payload), encoding='utf-8')
    loaded = json.loads(p.read_text(encoding='utf-8'))
    assert loaded['entry_count'] == 2
    assert loaded['add_count'] == 4
    assert loaded['cycles'][1]['side'] == 'short'
