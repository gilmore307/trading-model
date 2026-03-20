from __future__ import annotations

from typing import Any


MA_FAMILY = {
    'family': 'moving_average',
    'phase_goal': 'dynamic_parameters',
    'baseline_variants': [
        {'variant_id': 'ma_5_20', 'fast_window': 5, 'slow_window': 20},
        {'variant_id': 'ma_8_24', 'fast_window': 8, 'slow_window': 24},
        {'variant_id': 'ma_10_30', 'fast_window': 10, 'slow_window': 30},
        {'variant_id': 'ma_20_60', 'fast_window': 20, 'slow_window': 60},
        {'variant_id': 'ma_30_90', 'fast_window': 30, 'slow_window': 90},
        {'variant_id': 'ma_50_200', 'fast_window': 50, 'slow_window': 200},
    ],
    'dynamic_parameter_targets': [
        'volatility_adaptive_windows',
        'trend_strength_adaptive_windows',
        'session_sensitive_windows',
    ],
}


FAMILY_REGISTRY: dict[str, dict[str, Any]] = {
    'moving_average': MA_FAMILY,
}


def family_config(name: str) -> dict[str, Any] | None:
    return FAMILY_REGISTRY.get(name)


def family_names() -> list[str]:
    return sorted(FAMILY_REGISTRY.keys())
