from src.research.export import render_research_report_markdown


def test_render_research_report_markdown_contains_quality_and_matrix_sections():
    report = {
        'summary': {'row_count': 2, 'forward_field': 'fwd_ret_15m', 'forward_fields': ['fwd_ret_15m']},
        'regime_quality': {
            'trend': {'sample_count': 2, 'avg_confidence': 0.8, 'avg_fwd_ret_15m': 0.01, 'positive_rate_fwd_ret_15m': 0.5},
        },
        'regime_separability': {
            'closest_pairs': [
                {'pair': 'range__vs__trend', 'distance': 0.42, 'comparable_feature_count': 5},
            ],
        },
        'strategy_regime_matrix': {
            'trend': {
                'trend': {'sample_count': 2, 'enter_rate': 1.0, 'arm_rate': 0.0, 'watch_rate': 0.0, 'hold_rate': 0.0, 'avg_score': 4.0, 'avg_forward_return': 0.01, 'avg_enter_forward_return': 0.01, 'avg_arm_forward_return': None, 'positive_forward_rate': 0.5},
            },
        },
    }
    md = render_research_report_markdown(report)
    assert '# Regime Research Report' in md
    assert '## Regime Quality' in md
    assert '### trend' in md
    assert '## Regime Separability' in md
    assert 'range__vs__trend' in md
    assert '## Strategy × Regime Matrix' in md
    assert '#### Strategy: trend' in md
