from __future__ import annotations

from typing import Any


def _ma_variants() -> list[dict[str, Any]]:
    windows = [
        (5, 20),
        (8, 24),
        (10, 30),
        (20, 60),
        (30, 90),
        (50, 200),
    ]
    thresholds = [0.0005, 0.0010, 0.0020]
    ma_types = ['SMA', 'EMA', 'WMA', 'HMA']
    price_sources = ['close', 'hl2', 'hlc3', 'ohlc4', 'open']
    variants: list[dict[str, Any]] = []
    for fast_window, slow_window in windows:
        for threshold in thresholds:
            threshold_bps = int(round(threshold * 10_000))
            for ma_type in ma_types:
                for price_source in price_sources:
                    variants.append({
                        'variant_id': f'{ma_type.lower()}_{price_source}_{fast_window}_{slow_window}_t{threshold_bps:03d}',
                        'fast_window': fast_window,
                        'slow_window': slow_window,
                        'threshold_pct': threshold,
                        'ma_type': ma_type,
                        'price_source': price_source,
                    })
    return variants


def _donchian_variants() -> list[dict[str, Any]]:
    breakout_windows = [20, 30, 50, 80]
    exit_windows = [10, 15, 20]
    directions = ['both', 'long']
    confirm_bars = [1, 2]
    price_sources = ['close', 'hl2', 'hlc3']
    variants: list[dict[str, Any]] = []
    for breakout_window in breakout_windows:
        for exit_window in exit_windows:
            if exit_window >= breakout_window:
                continue
            for direction in directions:
                for confirm_bar in confirm_bars:
                    for price_source in price_sources:
                        variants.append({
                            'variant_id': f'donchian_{direction}_{price_source}_bw{breakout_window:03d}_ew{exit_window:03d}_cb{confirm_bar:02d}',
                            'breakout_window': breakout_window,
                            'exit_window': exit_window,
                            'direction': direction,
                            'confirm_bars': confirm_bar,
                            'price_source': price_source,
                        })
    return variants


MA_FAMILY = {
    'family': 'moving_average',
    'phase_goal': 'dynamic_parameters',
    'baseline_variants': _ma_variants(),
    'dynamic_parameter_targets': [
        'volatility_adaptive_windows',
        'trend_strength_adaptive_windows',
        'session_sensitive_windows',
        'spread_threshold_adaptive_entry_exit',
        'ma_type_selection_by_market_state',
        'price_source_selection_by_market_state',
    ],
}

def _bollinger_variants() -> list[dict[str, Any]]:
    windows = [20, 30, 50]
    std_mults = [2.0, 2.5]
    exit_zs = [0.0, 0.5, 1.0]
    directions = ['both', 'long']
    price_sources = ['close', 'hlc3']
    variants: list[dict[str, Any]] = []
    for window in windows:
        for std_mult in std_mults:
            for exit_z in exit_zs:
                for direction in directions:
                    for price_source in price_sources:
                        mult_tag = int(round(std_mult * 10))
                        exit_tag = int(round(exit_z * 10))
                        variants.append({
                            'variant_id': f'bollinger_{direction}_{price_source}_w{window:03d}_m{mult_tag:02d}_e{exit_tag:02d}',
                            'window': window,
                            'std_mult': std_mult,
                            'exit_z': exit_z,
                            'direction': direction,
                            'price_source': price_source,
                        })
    return variants


DONCHIAN_FAMILY = {
    'family': 'donchian_breakout',
    'phase_goal': 'dynamic_parameters',
    'baseline_variants': _donchian_variants(),
    'dynamic_parameter_targets': [
        'state_adaptive_breakout_window',
        'state_adaptive_exit_window',
        'volatility_filtered_breakout',
        'direction_selection_by_market_state',
    ],
}

BOLLINGER_FAMILY = {
    'family': 'bollinger_reversion',
    'phase_goal': 'dynamic_parameters',
    'baseline_variants': _bollinger_variants(),
    'dynamic_parameter_targets': [
        'state_adaptive_band_width',
        'state_adaptive_exit_threshold',
        'trend_filtered_mean_reversion',
        'volatility_conditioned_width',
    ],
}


FAMILY_REGISTRY: dict[str, dict[str, Any]] = {
    'moving_average': MA_FAMILY,
    'donchian_breakout': DONCHIAN_FAMILY,
    'bollinger_reversion': BOLLINGER_FAMILY,
}


def family_config(name: str) -> dict[str, Any] | None:
    return FAMILY_REGISTRY.get(name)


def family_names() -> list[str]:
    return sorted(FAMILY_REGISTRY.keys())
