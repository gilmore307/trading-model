from __future__ import annotations

from typing import Any


DEFAULT_PARAMETER_SPACES: dict[str, dict[str, list[Any]]] = {
    'trend': {
        'trend_bg_adx_min': [22.0, 25.0, 28.0],
        'trend_primary_adx_min': [18.0, 22.0, 26.0],
        'trend_trade_burst_min': [0.3, 0.4, 0.5],
        'trend_follow_through_enter_min': [2.0, 3.0, 4.0],
    },
    'range': {
        'range_primary_adx_max': [15.0, 18.0, 21.0],
        'range_trade_burst_max': [0.4, 0.5, 0.6],
        'range_reversion_enter_min': [2.0, 3.0, 4.0],
    },
    'compression': {
        'compression_bandwidth_max': [0.012, 0.015, 0.02],
        'compression_trade_burst_min': [0.4, 0.5, 0.6],
        'compression_launch_bias_enter_min': [2.0, 3.0, 4.0],
    },
    'crowded': {
        'crowded_extreme_min': [0.8, 0.85, 0.9],
        'crowded_oi_accel_min': [0.1, 0.15, 0.2],
        'crowded_rejection_enter_min': [3.0, 4.0, 5.0],
    },
    'shock': {
        'shock_trade_burst_min': [0.4, 0.5, 0.6],
        'shock_liq_min': [0.3, 0.4, 0.5],
        'shock_event_enter_min': [3.0, 4.0, 5.0],
    },
}


def parameter_space_for(strategy: str) -> dict[str, list[Any]]:
    return DEFAULT_PARAMETER_SPACES.get(strategy, {})
