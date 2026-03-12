import json
from datetime import UTC, datetime
from pathlib import Path

from src.runners.weekly_review import run_weekly_review


def test_run_weekly_review_exports_artifacts_from_history(tmp_path: Path):
    history = tmp_path / 'execution-cycles.jsonl'
    history.write_text(
        json.dumps({
            'summary': {
                'plan_account': 'trend',
                'plan_action': 'enter',
                'receipt_accepted': True,
                'composite_position_owner': 'trend',
                'composite_plan_action': 'enter',
                'account_metrics': {
                    'trend': {'pnl_usdt': 5.0, 'equity_usdt': 1005.0, 'fee_usdt': 0.1},
                    'router_composite': {'pnl_usdt': 4.0, 'fee_usdt': 0.05},
                    'flat_compare': {'pnl_usdt': 1.0},
                },
            },
            'compare_snapshot': {
                'accounts': [{'account': 'trend', 'has_position': True}],
                'highlights': ['router_selected:trend'],
            },
        }) + '\n',
        encoding='utf-8',
    )

    exported = run_weekly_review(
        now=datetime(2026, 3, 15, 12, 0, tzinfo=UTC),
        history_path=history,
        out_dir=tmp_path / 'reports',
    )
    assert Path(exported['json_path']).exists()
    assert Path(exported['markdown_path']).exists()
    payload = json.loads(Path(exported['json_path']).read_text(encoding='utf-8'))
    assert payload['meta']['label'] == 'weekly:2026-03-08->2026-03-15'
    assert payload['metrics']['performance']['status'] == 'ready'
    assert payload['recommended_actions']
