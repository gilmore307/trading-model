from datetime import UTC, datetime

from src.review.framework import build_quarterly_window, build_weekly_window
from src.review.report import build_report_scaffold


def test_weekly_report_scaffold_includes_compare_sections():
    window = build_weekly_window(datetime(2026, 3, 15, 12, 0, tzinfo=UTC))
    compare_snapshot = {
        'accounts': [{'account': 'trend', 'label': 'Trend'}],
        'highlights': ['router_selected:trend'],
    }
    report = build_report_scaffold(window, compare_snapshot)
    section_keys = [section['key'] for section in report['sections']]
    assert 'account_comparison' in section_keys
    assert 'router_composite_review' in section_keys
    assert report['compare_snapshot']['highlights'] == ['router_selected:trend']
    assert report['parameter_candidates']['auto_candidate_params']


def test_quarterly_report_scaffold_includes_structural_review_section():
    window = build_quarterly_window(
        datetime(2026, 1, 4, 0, 0, tzinfo=UTC),
        datetime(2026, 4, 5, 0, 0, tzinfo=UTC),
    )
    report = build_report_scaffold(window)
    section_keys = [section['key'] for section in report['sections']]
    assert 'structural_review' in section_keys
    assert report['parameter_candidates']['structural_params']
