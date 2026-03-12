import json
from datetime import UTC, datetime
from pathlib import Path

from src.review.export import export_report_artifacts, render_report_markdown
from src.review.framework import build_weekly_window
from src.review.report import build_report_scaffold


def _sample_report():
    window = build_weekly_window(datetime(2026, 3, 15, 12, 0, tzinfo=UTC))
    return build_report_scaffold(
        window,
        metrics_by_account={
            'trend': {'pnl_usdt': 12.0, 'fee_usdt': 0.6, 'trade_count': 6, 'equity_change_usdt': 12.0, 'source': 'demo'},
            'meanrev': {'pnl_usdt': -2.0, 'fee_usdt': 0.1, 'trade_count': 7, 'equity_change_usdt': -2.0, 'source': 'demo'},
            'router_composite': {'pnl_usdt': 1.0, 'fee_usdt': 0.2, 'equity_change_usdt': 1.0, 'source': 'simulated'},
            'flat_compare': {'pnl_usdt': 3.0, 'fee_usdt': 0.0, 'equity_change_usdt': 3.0, 'source': 'baseline'},
        },
    )


def test_render_report_markdown_contains_core_sections():
    markdown = render_report_markdown(_sample_report())
    assert '# Trade Review - weekly:2026-03-08->2026-03-15' in markdown
    assert '## Executive Summary' in markdown
    assert '## Recommended Actions' in markdown
    assert '## Account Comparison' in markdown
    assert '## Parameter Review' in markdown


def test_export_report_artifacts_writes_json_and_markdown(tmp_path: Path):
    window = build_weekly_window(datetime(2026, 3, 15, 12, 0, tzinfo=UTC))
    exported = export_report_artifacts(
        window,
        metrics_by_account={
            'trend': {'pnl_usdt': 12.0, 'fee_usdt': 0.6, 'trade_count': 6, 'equity_change_usdt': 12.0, 'source': 'demo'},
            'meanrev': {'pnl_usdt': -2.0, 'fee_usdt': 0.1, 'trade_count': 7, 'equity_change_usdt': -2.0, 'source': 'demo'},
            'router_composite': {'pnl_usdt': 1.0, 'fee_usdt': 0.2, 'equity_change_usdt': 1.0, 'source': 'simulated'},
            'flat_compare': {'pnl_usdt': 3.0, 'fee_usdt': 0.0, 'equity_change_usdt': 3.0, 'source': 'baseline'},
        },
        out_dir=tmp_path,
        generated_at=datetime(2026, 3, 15, 12, 34, 56, tzinfo=UTC),
    )
    json_path = Path(exported['json_path'])
    md_path = Path(exported['markdown_path'])
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding='utf-8'))
    assert payload['executive_summary']['status'] == 'ready'
    markdown = md_path.read_text(encoding='utf-8')
    assert 'Review fee_burden_frequency_gate' in markdown


def test_export_report_artifacts_updates_latest_pointers_and_index(tmp_path: Path):
    window = build_weekly_window(datetime(2026, 3, 15, 12, 0, tzinfo=UTC))
    exported = export_report_artifacts(
        window,
        metrics_by_account={
            'trend': {'pnl_usdt': 12.0, 'fee_usdt': 0.6, 'trade_count': 6, 'equity_change_usdt': 12.0, 'source': 'demo'},
            'router_composite': {'pnl_usdt': 1.0, 'fee_usdt': 0.2, 'equity_change_usdt': 1.0, 'source': 'simulated'},
            'flat_compare': {'pnl_usdt': 3.0, 'fee_usdt': 0.0, 'equity_change_usdt': 3.0, 'source': 'baseline'},
        },
        out_dir=tmp_path,
        generated_at=datetime(2026, 3, 15, 12, 34, 56, tzinfo=UTC),
    )
    latest_json = Path(exported['latest_json_path'])
    latest_md = Path(exported['latest_markdown_path'])
    index_path = Path(exported['index_path'])
    assert latest_json.exists()
    assert latest_md.exists()
    assert index_path.exists()
    latest_payload = json.loads(latest_json.read_text(encoding='utf-8'))
    assert latest_payload['meta']['cadence'] == 'weekly'
    index_payload = json.loads(index_path.read_text(encoding='utf-8'))
    assert index_payload['latest_by_cadence']['weekly']['json_path'] == exported['json_path']
    assert index_payload['reports'][-1]['markdown_path'] == exported['markdown_path']
