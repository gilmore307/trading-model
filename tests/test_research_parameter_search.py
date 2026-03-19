from src.research.grid_search import build_parameter_search_plan, generate_parameter_combinations
from src.research.parameter_spaces import parameter_space_for


def test_generate_parameter_combinations_builds_cartesian_product():
    combos = generate_parameter_combinations({'a': [1, 2], 'b': ['x', 'y']})
    assert len(combos) == 4
    assert {'a': 1, 'b': 'x'} in combos
    assert {'a': 2, 'b': 'y'} in combos


def test_build_parameter_search_plan_scopes_to_regime_and_strategy_space():
    rows = [
        {'final_regime': 'trend'},
        {'final_regime': 'trend'},
        {'final_regime': 'range'},
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
