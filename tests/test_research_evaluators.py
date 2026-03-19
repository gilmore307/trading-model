from src.research.evaluators import build_regime_quality_summary, build_regime_separability_summary, build_strategy_ranking_summary, build_strategy_regime_matrix


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


def test_build_regime_separability_summary_reports_feature_means_and_closest_pairs():
    rows = [
        {
            'final_regime': 'trend',
            'background_features': {'adx': 30.0, 'ema20_slope': 1.0, 'ema50_slope': 0.8},
            'primary_features': {'adx': 25.0, 'vwap_deviation_z': 1.0, 'bollinger_bandwidth_pct': 0.1, 'realized_vol_pct': 0.5, 'funding_pctile': 0.6, 'oi_accel': 0.1, 'basis_deviation_pct': 0.01},
            'override_features': {'vwap_deviation_z': 1.2, 'trade_burst_score': 0.7, 'liquidation_spike_score': 0.1, 'orderbook_imbalance': 0.2, 'realized_vol_pct': 0.6},
        },
        {
            'final_regime': 'range',
            'background_features': {'adx': 15.0, 'ema20_slope': 0.1, 'ema50_slope': 0.05},
            'primary_features': {'adx': 12.0, 'vwap_deviation_z': -0.8, 'bollinger_bandwidth_pct': 0.15, 'realized_vol_pct': 0.3, 'funding_pctile': 0.5, 'oi_accel': 0.0, 'basis_deviation_pct': 0.0},
            'override_features': {'vwap_deviation_z': -0.5, 'trade_burst_score': 0.2, 'liquidation_spike_score': 0.0, 'orderbook_imbalance': 0.05, 'realized_vol_pct': 0.31},
        },
    ]
    summary = build_regime_separability_summary(rows)
    assert summary['feature_means_by_regime']['trend']['background_features.adx'] == 30.0
    assert summary['feature_means_by_regime']['range']['primary_features.adx'] == 12.0
    assert summary['closest_pairs'][0]['pair'] == 'range__vs__trend'
    assert summary['closest_pairs'][0]['comparable_feature_count'] > 0


def test_build_strategy_ranking_summary_prefers_higher_enter_forward_return_then_score():
    matrix = {
        'trend': {
            'trend': {'avg_enter_forward_return': 0.02, 'enter_rate': 0.5, 'avg_score': 3.0},
            'range': {'avg_enter_forward_return': None, 'enter_rate': 0.0, 'avg_score': 4.0},
            'compression': {'avg_enter_forward_return': 0.01, 'enter_rate': 0.7, 'avg_score': 2.0},
        },
    }
    ranking = build_strategy_ranking_summary(matrix)
    assert [row['strategy'] for row in ranking['trend']] == ['trend', 'compression', 'range']


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
