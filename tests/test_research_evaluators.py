from src.research.evaluators import build_regime_quality_summary, build_strategy_regime_matrix


def test_build_regime_quality_summary_aggregates_confidence_and_forward_returns():
    rows = [
        {'final_regime': 'trend', 'final_confidence': 0.8, 'fwd_ret_15m': 0.01, 'fwd_ret_1h': 0.02, 'fwd_ret_4h': 0.03},
        {'final_regime': 'trend', 'final_confidence': 0.6, 'fwd_ret_15m': -0.01, 'fwd_ret_1h': -0.02, 'fwd_ret_4h': 0.01},
        {'final_regime': 'range', 'final_confidence': 0.7, 'fwd_ret_15m': 0.0, 'fwd_ret_1h': 0.01, 'fwd_ret_4h': -0.01},
    ]
    summary = build_regime_quality_summary(rows)
    assert summary['trend']['sample_count'] == 2
    assert summary['trend']['avg_confidence'] == 0.7
    assert summary['trend']['avg_fwd_ret_1h'] == 0.0
    assert summary['trend']['positive_rate_fwd_ret_1h'] == 0.5
    assert summary['range']['sample_count'] == 1
    assert summary['range']['avg_fwd_ret_4h'] == -0.01


def test_build_strategy_regime_matrix_aggregates_shadow_plan_behavior():
    rows = [
        {
            'final_regime': 'trend',
            'fwd_ret_1h': 0.02,
            'shadow_plans': {
                'trend': {'action': 'enter', 'score': 4.0},
                'range': {'action': 'watch', 'score': 1.0},
            },
        },
        {
            'final_regime': 'trend',
            'fwd_ret_1h': -0.01,
            'shadow_plans': {
                'trend': {'action': 'arm', 'score': 2.0},
                'range': {'action': 'watch', 'score': 0.5},
            },
        },
        {
            'final_regime': 'range',
            'fwd_ret_1h': 0.03,
            'shadow_plans': {
                'trend': {'action': 'watch', 'score': 1.0},
                'range': {'action': 'enter', 'score': 3.0},
            },
        },
    ]
    matrix = build_strategy_regime_matrix(rows, forward_field='fwd_ret_1h')
    assert matrix['trend']['trend']['sample_count'] == 2
    assert matrix['trend']['trend']['enter_rate'] == 0.5
    assert matrix['trend']['trend']['arm_rate'] == 0.5
    assert matrix['trend']['trend']['avg_score'] == 3.0
    assert matrix['trend']['trend']['avg_forward_return'] == 0.005
    assert matrix['trend']['trend']['avg_enter_forward_return'] == 0.02
    assert matrix['trend']['trend']['avg_arm_forward_return'] == -0.01
    assert matrix['trend']['trend']['positive_forward_rate'] == 0.5
    assert matrix['range']['range']['enter_rate'] == 1.0
    assert matrix['range']['range']['avg_forward_return'] == 0.03
    assert matrix['range']['range']['avg_enter_forward_return'] == 0.03
