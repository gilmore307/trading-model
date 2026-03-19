from src.research.reporting import build_research_report


def test_build_research_report_combines_regime_quality_and_strategy_matrix():
    rows = [
        {
            'final_regime': 'trend',
            'final_confidence': 0.8,
            'fwd_ret_15m': 0.01,
            'fwd_ret_1h': 0.02,
            'fwd_ret_4h': 0.03,
            'shadow_plans': {
                'trend': {'action': 'enter', 'score': 4.0},
                'range': {'action': 'watch', 'score': 1.0},
            },
        },
        {
            'final_regime': 'range',
            'final_confidence': 0.7,
            'fwd_ret_15m': 0.0,
            'fwd_ret_1h': -0.01,
            'fwd_ret_4h': 0.01,
            'shadow_plans': {
                'trend': {'action': 'watch', 'score': 1.0},
                'range': {'action': 'enter', 'score': 3.0},
            },
        },
    ]
    report = build_research_report(rows, forward_field='fwd_ret_1h')
    assert report['summary']['row_count'] == 2
    assert report['regime_quality']['trend']['sample_count'] == 1
    assert report['strategy_regime_matrix']['trend']['trend']['enter_rate'] == 1.0
    assert report['strategy_regime_matrix']['range']['range']['avg_enter_forward_return'] == -0.01
