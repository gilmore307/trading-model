from src.research.reporting import build_market_state_report, build_research_report


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
    assert report['strategy_ranking']['trend'][0]['strategy'] == 'trend'
    assert 'trend' in report['parameter_search_preview']
    assert len(report['parameter_search_preview']['trend']) > 0


def test_build_market_state_report_produces_cube_summary():
    candles = []
    base_ts = 1700000000000
    for i in range(140):
        close = 100 + i * 0.3
        candles.append({
            'ts': base_ts + i * 60_000,
            'timestamp': f'2024-01-01T00:{i:02d}:00+00:00',
            'open': close - 0.5,
            'high': close + 1.0,
            'low': close - 1.0,
            'close': close,
            'vol': 100 + i,
            'volCcyQuote': 100000 + i * 500,
        })
    report = build_market_state_report(
        candles,
        [
            {'fast_window': 5, 'slow_window': 20, 'threshold_enter_pct': 0.0005, 'threshold_exit_pct': 0.0, 'ma_type': 'EMA', 'price_source': 'close'},
            {'fast_window': 20, 'slow_window': 60, 'threshold_enter_pct': 0.001, 'threshold_exit_pct': 0.0005, 'ma_type': 'SMA', 'price_source': 'close'},
        ],
        horizon_bars=5,
    )
    assert report['summary']['state_row_count'] > 0
    assert report['summary']['candidate_row_count'] > 0
    assert report['performance_cube']['summary']['cell_count'] > 0
