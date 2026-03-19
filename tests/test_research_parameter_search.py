from src.research.grid_search import build_parameter_search_plan, generate_parameter_combinations, rank_parameter_candidates, score_strategy_configuration
from src.research.parameter_spaces import parameter_space_for


def test_generate_parameter_combinations_builds_cartesian_product():
    combos = generate_parameter_combinations({'a': [1, 2], 'b': ['x', 'y']})
    assert len(combos) == 4
    assert {'a': 1, 'b': 'x'} in combos
    assert {'a': 2, 'b': 'y'} in combos


def test_score_strategy_configuration_builds_simple_objective_from_matrix_stats():
    rows = [
        {
            'final_regime': 'trend',
            'fwd_ret_1h': 0.02,
            'shadow_plans': {'trend': {'action': 'enter', 'score': 4.0}},
        },
        {
            'final_regime': 'trend',
            'fwd_ret_1h': -0.01,
            'shadow_plans': {'trend': {'action': 'arm', 'score': 2.0}},
        },
    ]
    result = score_strategy_configuration(rows=rows, regime='trend', strategy='trend')
    assert result['stats']['avg_enter_forward_return'] == 0.02
    assert result['stats']['enter_rate'] == 0.5
    assert result['objective_score'] > 0


def test_rank_parameter_candidates_returns_sorted_preview():
    rows = [
        {'final_regime': 'trend', 'fwd_ret_1h': 0.02, 'shadow_plans': {'trend': {'action': 'enter', 'score': 4.0}}},
        {'final_regime': 'trend', 'fwd_ret_1h': -0.01, 'shadow_plans': {'trend': {'action': 'arm', 'score': 2.0}}},
    ]
    ranked = rank_parameter_candidates(
        regime='trend',
        strategy='trend',
        space={'x': [1, 2, 3]},
        rows=rows,
        limit=3,
    )
    assert len(ranked) == 3
    assert ranked[0]['candidate_objective_score'] >= ranked[-1]['candidate_objective_score']
    assert 'candidate_stats' in ranked[0]


def test_build_parameter_search_plan_scopes_to_regime_and_strategy_space():
    rows = [
        {'final_regime': 'trend', 'fwd_ret_1h': 0.02, 'shadow_plans': {'trend': {'action': 'enter', 'score': 4.0}}},
        {'final_regime': 'trend', 'fwd_ret_1h': -0.01, 'shadow_plans': {'trend': {'action': 'arm', 'score': 2.0}}},
        {'final_regime': 'range', 'fwd_ret_1h': 0.01, 'shadow_plans': {'trend': {'action': 'watch', 'score': 1.0}}},
    ]
    plan = build_parameter_search_plan(
        regime='trend',
        strategy='trend',
        space=parameter_space_for('trend'),
        rows=rows,
    )
    assert plan['regime'] == 'trend'
    assert plan['strategy'] == 'trend'
    assert plan['sample_count'] == 2
    assert plan['combination_count'] > 0
    assert 'trend_bg_adx_min' in plan['parameters']
    assert plan['baseline_score']['stats']['avg_enter_forward_return'] == 0.02
    assert len(plan['candidate_ranking_preview']) > 0
