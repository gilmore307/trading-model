from src.research.evaluators import build_strategy_regime_matrix


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
    assert matrix['range']['range']['enter_rate'] == 1.0
    assert matrix['range']['range']['avg_forward_return'] == 0.03
