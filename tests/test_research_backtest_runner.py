import json
from pathlib import Path

from src.research.export import render_research_report_markdown
from src.research.replay import build_dataset_from_snapshot_rows, load_snapshot_jsonl
from src.research.reporting import build_research_report


def test_offline_backtest_pipeline_builds_dataset_and_report_from_historical_snapshots(tmp_path: Path):
    src = tmp_path / 'snapshots.jsonl'
    src.write_text(
        '\n'.join([
            '{"artifact_type":"regime_local_cycle","recorded_at":"2026-03-19T12:00:00+00:00","symbol":"BTC-USDT-SWAP","final_regime":"trend","final_confidence":0.8,"background_regime":"trend","primary_regime":"trend","override_regime":null,"route_strategy_family":"trend","route_account":"trend","route_trade_enabled":true,"feature_snapshot":{"background_4h":{"regime":"trend","confidence":0.8,"scores":{"trend":4.0},"tradable":true,"adx":30.0,"last_price":100.0,"ema20_slope":1.0,"ema50_slope":0.8},"primary_15m":{"regime":"trend","confidence":0.75,"scores":{"trend":3.0},"tradable":true,"adx":26.0,"last_price":100.0,"vwap_deviation_z":1.0,"bollinger_bandwidth_pct":0.1,"realized_vol_pct":0.5,"funding_pctile":0.6,"oi_accel":0.1,"basis_deviation_pct":0.001},"override_1m":{"regime":null,"confidence":null,"scores":null,"tradable":null,"last_price":100.0,"vwap_deviation_z":1.1,"trade_burst_score":0.5,"liquidation_spike_score":0.0,"orderbook_imbalance":0.1,"realized_vol_pct":0.6}},"shadow_plans":{}}',
            '{"artifact_type":"regime_local_cycle","recorded_at":"2026-03-19T12:05:00+00:00","symbol":"BTC-USDT-SWAP","final_regime":"trend","final_confidence":0.82,"background_regime":"trend","primary_regime":"trend","override_regime":null,"route_strategy_family":"trend","route_account":"trend","route_trade_enabled":true,"feature_snapshot":{"background_4h":{"regime":"trend","confidence":0.82,"scores":{"trend":4.1},"tradable":true,"adx":31.0,"last_price":102.0,"ema20_slope":1.1,"ema50_slope":0.9},"primary_15m":{"regime":"trend","confidence":0.77,"scores":{"trend":3.1},"tradable":true,"adx":27.0,"last_price":102.0,"vwap_deviation_z":1.2,"bollinger_bandwidth_pct":0.11,"realized_vol_pct":0.5,"funding_pctile":0.62,"oi_accel":0.12,"basis_deviation_pct":0.0012},"override_1m":{"regime":null,"confidence":null,"scores":null,"tradable":null,"last_price":102.0,"vwap_deviation_z":1.3,"trade_burst_score":0.55,"liquidation_spike_score":0.0,"orderbook_imbalance":0.12,"realized_vol_pct":0.62}},"shadow_plans":{}}'
        ]),
        encoding='utf-8',
    )
    rows = load_snapshot_jsonl(src)
    dataset = build_dataset_from_snapshot_rows(rows, horizons={'fwd_ret_15m': 1})
    report = build_research_report(dataset, forward_field='fwd_ret_15m', forward_fields=['fwd_ret_15m'])
    md = render_research_report_markdown(report)
    assert len(dataset) == 2
    assert dataset[0]['fwd_ret_15m'] == 0.02
    assert report['summary']['row_count'] == 2
    assert report['regime_quality']['trend']['avg_fwd_ret_15m'] == 0.02
    assert '## Strategy Ranking Summary' in md
