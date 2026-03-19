from pathlib import Path

from src.research.replay import build_dataset_from_snapshot_rows, load_snapshot_jsonl


SAMPLE_ROW = {
    'timestamp': '2026-03-19T12:00:00+00:00',
    'symbol': 'BTC-USDT-SWAP',
    'background_4h': {'primary': 'trend', 'confidence': 0.8, 'reasons': [], 'secondary': [], 'scores': {'trend': 4.0}, 'tradable': True},
    'primary_15m': {'primary': 'trend', 'confidence': 0.75, 'reasons': [], 'secondary': [], 'scores': {'trend': 3.0}, 'tradable': True},
    'override_1m': {'primary': 'shock', 'confidence': 0.4, 'reasons': [], 'secondary': [], 'scores': {'shock': 2.0}, 'tradable': True},
    'background_features': {'adx': 28.0, 'ema20_slope': 1.2, 'ema50_slope': 0.9},
    'primary_features': {'adx': 24.0, 'vwap_deviation_z': 1.1},
    'override_features': {'trade_burst_score': 0.7, 'vwap_deviation_z': 1.3},
    'final_decision': {'primary': 'trend', 'confidence': 0.8, 'reasons': [], 'secondary': [], 'scores': {'trend': 4.0}, 'tradable': True},
    'route_decision': {'regime': 'trend', 'account': 'trend', 'strategy_family': 'trend', 'trade_enabled': True, 'allow_reason': 'route_to_trend', 'block_reason': None},
    'decision_summary': {'regime': 'trend', 'confidence': 0.8, 'tradable': True, 'account': 'trend', 'strategy_family': 'trend', 'trade_enabled': True, 'allow_reason': 'route_to_trend', 'block_reason': None, 'reasons': [], 'secondary': [], 'diagnostics': []},
}


def test_load_snapshot_jsonl_and_build_dataset(tmp_path: Path):
    src = tmp_path / 'snapshots.jsonl'
    src.write_text('\n'.join([
        '{"timestamp":"2026-03-19T12:00:00+00:00","symbol":"BTC-USDT-SWAP","background_4h":{"primary":"trend","confidence":0.8,"reasons":[],"secondary":[],"scores":{"trend":4.0},"tradable":true},"primary_15m":{"primary":"trend","confidence":0.75,"reasons":[],"secondary":[],"scores":{"trend":3.0},"tradable":true},"override_1m":{"primary":"shock","confidence":0.4,"reasons":[],"secondary":[],"scores":{"shock":2.0},"tradable":true},"background_features":{"adx":28.0,"ema20_slope":1.2,"ema50_slope":0.9},"primary_features":{"adx":24.0,"vwap_deviation_z":1.1},"override_features":{"trade_burst_score":0.7,"vwap_deviation_z":1.3},"final_decision":{"primary":"trend","confidence":0.8,"reasons":[],"secondary":[],"scores":{"trend":4.0},"tradable":true},"route_decision":{"regime":"trend","account":"trend","strategy_family":"trend","trade_enabled":true,"allow_reason":"route_to_trend","block_reason":null},"decision_summary":{"regime":"trend","confidence":0.8,"tradable":true,"account":"trend","strategy_family":"trend","trade_enabled":true,"allow_reason":"route_to_trend","block_reason":null,"reasons":[],"secondary":[],"diagnostics":[]}}'
    ]), encoding='utf-8')
    rows = load_snapshot_jsonl(src)
    assert len(rows) == 1
    dataset = build_dataset_from_snapshot_rows(rows, close_prices=[100.0, 101.0, 102.0, 103.0])
    assert len(dataset) == 1
    assert dataset[0]['final_regime'] == 'trend'
    assert dataset[0]['shadow_plans']['trend']['action'] in {'enter', 'arm', 'watch'}
