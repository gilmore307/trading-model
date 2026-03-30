from src.research.export import render_market_state_report_markdown
from src.research.reporting import build_family_market_state_report


def test_build_family_market_state_report_compares_multiple_families():
    state_rows = [
        {'ts': 1, 'market_state': 'trend'},
        {'ts': 2, 'market_state': 'trend'},
        {'ts': 3, 'market_state': 'range'},
    ]
    utility_rows = [
        {'ts': 1, 'family': 'moving_average', 'parameter_region': 'fast_windows__tight_threshold', 'utility_1h': 0.01},
        {'ts': 2, 'family': 'donchian_breakout', 'parameter_region': 'fast_breakout__aggressive', 'utility_1h': 0.02},
        {'ts': 3, 'family': 'moving_average', 'parameter_region': 'fast_windows__wide_threshold', 'utility_1h': -0.01},
    ]
    report = build_family_market_state_report(state_rows, utility_rows)
    assert report['performance_cube']['summary']['family_count'] == 2
    assert report['family_state_summary']['trend'][0]['family'] == 'donchian_breakout'


def test_render_market_state_report_markdown_supports_family_summary():
    report = {
        'summary': {'state_row_count': 3, 'utility_row_count': 3},
        'state_counts': {'trend': 2, 'range': 1},
        'family_state_summary': {
            'trend': [
                {'family': 'donchian_breakout', 'sample_count': 1, 'avg_utility_1h': 0.02, 'positive_rate': 1.0},
                {'family': 'moving_average', 'sample_count': 1, 'avg_utility_1h': 0.01, 'positive_rate': 1.0},
            ]
        },
        'performance_cube': {
            'summary': {'cell_count': 2},
            'rows': [
                {'market_state': 'trend', 'family': 'moving_average', 'parameter_region': 'fast_windows__tight_threshold', 'sample_count': 1, 'avg_utility_1h': 0.01, 'positive_rate': 1.0},
                {'market_state': 'trend', 'family': 'donchian_breakout', 'parameter_region': 'fast_breakout__aggressive', 'sample_count': 1, 'avg_utility_1h': 0.02, 'positive_rate': 1.0},
            ],
        },
    }
    md = render_market_state_report_markdown(report)
    assert 'Family Summary by State' in md
    assert 'donchian_breakout' in md
