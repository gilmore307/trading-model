from datetime import UTC, datetime
from pathlib import Path

from src.research.dataset_builder import build_research_row, write_jsonl
from src.runners.regime_runner import RegimeRunnerOutput


def make_output() -> RegimeRunnerOutput:
    return RegimeRunnerOutput(
        observed_at=datetime(2026, 3, 19, 12, 0, tzinfo=UTC),
        symbol='BTC-USDT-SWAP',
        background_4h={'primary': 'trend', 'confidence': 0.8, 'reasons': [], 'secondary': [], 'scores': {'trend': 4.0}, 'tradable': True},
        primary_15m={'primary': 'trend', 'confidence': 0.75, 'reasons': [], 'secondary': [], 'scores': {'trend': 3.0}, 'tradable': True},
        override_1m={'primary': 'shock', 'confidence': 0.4, 'reasons': [], 'secondary': [], 'scores': {'shock': 2.0}, 'tradable': True},
        background_features={'adx': 28.0, 'ema20_slope': 1.2, 'ema50_slope': 0.9},
        primary_features={'adx': 24.0, 'vwap_deviation_z': 1.1},
        override_features={'trade_burst_score': 0.7, 'vwap_deviation_z': 1.3},
        final_decision={'primary': 'trend', 'confidence': 0.8, 'reasons': [], 'secondary': [], 'scores': {'trend': 4.0}, 'tradable': True},
        route_decision={'regime': 'trend', 'account': 'trend', 'strategy_family': 'trend', 'trade_enabled': True, 'allow_reason': 'route_to_trend', 'block_reason': None},
        decision_summary={'regime': 'trend', 'confidence': 0.8, 'tradable': True, 'account': 'trend', 'strategy_family': 'trend', 'trade_enabled': True, 'allow_reason': 'route_to_trend', 'block_reason': None, 'reasons': [], 'secondary': [], 'diagnostics': []},
        settings=None,
    )


def test_build_research_row_includes_shadow_plans_and_forward_labels():
    row = build_research_row(output=make_output(), prices=[100.0, 101.0, 102.0, 103.0, 104.0], index=0, horizons={'fwd_ret_15m': 1})
    assert row['final_regime'] == 'trend'
    assert row['executor_action'] in {'enter', 'arm', 'watch'}
    assert 'trend' in row['shadow_plans']
    assert 'score' in row['shadow_plans']['trend']
    assert row['fwd_ret_15m'] == 0.01


def test_write_jsonl_writes_rows(tmp_path: Path):
    path = write_jsonl([{'a': 1}, {'a': 2}], tmp_path / 'dataset.jsonl')
    lines = path.read_text(encoding='utf-8').splitlines()
    assert len(lines) == 2
