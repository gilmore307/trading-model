from __future__ import annotations

from typing import Any


def regime_local_artifact_to_snapshot_row(row: dict[str, Any]) -> dict[str, Any]:
    feature_snapshot = row.get('feature_snapshot') or {}
    bg = feature_snapshot.get('background_4h') or {}
    primary = feature_snapshot.get('primary_15m') or {}
    override = feature_snapshot.get('override_1m') or {}

    background_4h = {
        'primary': row.get('background_regime') or bg.get('regime'),
        'confidence': bg.get('confidence'),
        'reasons': bg.get('reasons') or [],
        'secondary': bg.get('secondary') or [],
        'scores': bg.get('scores'),
        'tradable': bg.get('tradable'),
    }
    primary_15m = {
        'primary': row.get('primary_regime') or primary.get('regime'),
        'confidence': primary.get('confidence'),
        'reasons': primary.get('reasons') or [],
        'secondary': primary.get('secondary') or [],
        'scores': primary.get('scores'),
        'tradable': primary.get('tradable'),
    }
    override_1m = None
    if row.get('override_regime') is not None or override:
        override_1m = {
            'primary': row.get('override_regime') if row.get('override_regime') is not None else override.get('regime'),
            'confidence': override.get('confidence'),
            'reasons': override.get('reasons') or [],
            'secondary': override.get('secondary') or [],
            'scores': override.get('scores'),
            'tradable': override.get('tradable'),
        }

    return {
        'timestamp': row.get('recorded_at'),
        'symbol': row.get('symbol'),
        'background_4h': background_4h,
        'primary_15m': primary_15m,
        'override_1m': override_1m,
        'background_features': {
            'adx': bg.get('adx'),
            'ema20_slope': bg.get('ema20_slope'),
            'ema50_slope': bg.get('ema50_slope'),
        },
        'primary_features': {
            'adx': primary.get('adx'),
            'vwap_deviation_z': primary.get('vwap_deviation_z'),
            'bollinger_bandwidth_pct': primary.get('bollinger_bandwidth_pct'),
            'realized_vol_pct': primary.get('realized_vol_pct'),
            'funding_pctile': primary.get('funding_pctile'),
            'oi_accel': primary.get('oi_accel'),
            'basis_deviation_pct': primary.get('basis_deviation_pct'),
        },
        'override_features': {
            'vwap_deviation_z': override.get('vwap_deviation_z'),
            'trade_burst_score': override.get('trade_burst_score'),
            'liquidation_spike_score': override.get('liquidation_spike_score'),
            'orderbook_imbalance': override.get('orderbook_imbalance'),
            'realized_vol_pct': override.get('realized_vol_pct'),
        },
        'final_decision': {
            'primary': row.get('final_regime'),
            'confidence': row.get('final_confidence'),
            'reasons': [],
            'secondary': [],
            'scores': None,
            'tradable': row.get('route_trade_enabled'),
        },
        'route_decision': {
            'regime': row.get('final_regime'),
            'account': row.get('route_account'),
            'strategy_family': row.get('route_strategy_family'),
            'trade_enabled': row.get('route_trade_enabled'),
            'allow_reason': None,
            'block_reason': None,
        },
        'decision_summary': {
            'regime': row.get('final_regime'),
            'confidence': row.get('final_confidence'),
            'tradable': row.get('route_trade_enabled'),
            'account': row.get('route_account'),
            'strategy_family': row.get('route_strategy_family'),
            'trade_enabled': row.get('route_trade_enabled'),
            'allow_reason': None,
            'block_reason': None,
            'reasons': [],
            'secondary': [],
            'diagnostics': [],
        },
    }
