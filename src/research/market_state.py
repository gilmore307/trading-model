from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev
from typing import Any
import json


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _rolling_mean(values: list[float], end: int, window: int) -> float | None:
    if end + 1 < window:
        return None
    chunk = values[end - window + 1 : end + 1]
    return mean(chunk)


def _rolling_std(values: list[float], end: int, window: int) -> float | None:
    if end + 1 < window:
        return None
    chunk = values[end - window + 1 : end + 1]
    if len(chunk) < 2:
        return 0.0
    return pstdev(chunk)


def _forward_return(closes: list[float], start: int, horizon: int) -> float | None:
    end = start + horizon
    if start < 0 or end >= len(closes):
        return None
    entry = closes[start]
    exit_ = closes[end]
    if entry <= 0:
        return None
    return (exit_ / entry) - 1.0


def build_market_state_rows(
    rows: list[dict[str, Any]],
    *,
    vol_window: int = 30,
    trend_window: int = 60,
    range_window: int = 30,
    burst_window: int = 30,
) -> list[dict[str, Any]]:
    closes = [_safe_float(row.get('close')) for row in rows]
    volumes = [_safe_float(row.get('volCcyQuote', row.get('volCcy', row.get('vol', row.get('volume'))))) for row in rows]
    highs = [_safe_float(row.get('high', row.get('close'))) for row in rows]
    lows = [_safe_float(row.get('low', row.get('close'))) for row in rows]
    out: list[dict[str, Any]] = []
    clean_closes = [0.0 if v is None else v for v in closes]
    clean_volumes = [0.0 if v is None else v for v in volumes]
    clean_highs = [clean_closes[i] if highs[i] is None else highs[i] for i in range(len(rows))]
    clean_lows = [clean_closes[i] if lows[i] is None else lows[i] for i in range(len(rows))]

    vol_hist: list[float] = []
    range_hist: list[float] = []
    burst_hist: list[float] = []

    for i, row in enumerate(rows):
        close = clean_closes[i]
        if close <= 0:
            continue
        ret_1m = _forward_return(clean_closes, i - 1, 1) if i >= 1 else None
        trend_anchor = clean_closes[i - trend_window] if i >= trend_window and clean_closes[i - trend_window] > 0 else None
        trend_return = None if trend_anchor is None else (close / trend_anchor) - 1.0
        intrarange_low = min(clean_lows[max(0, i - range_window + 1) : i + 1]) if i + 1 >= range_window else None
        intrarange_high = max(clean_highs[max(0, i - range_window + 1) : i + 1]) if i + 1 >= range_window else None
        range_width = None
        if intrarange_low is not None and intrarange_high is not None and close > 0:
            range_width = (intrarange_high - intrarange_low) / close
        vol_value = None
        if i >= vol_window:
            rets = []
            for j in range(i - vol_window + 1, i + 1):
                prev = clean_closes[j - 1]
                curr = clean_closes[j]
                if prev > 0 and curr > 0:
                    rets.append((curr / prev) - 1.0)
            if len(rets) >= max(5, vol_window // 3):
                vol_value = pstdev(rets)
                vol_hist.append(vol_value)
        volume_burst = None
        recent_vol_mean = _rolling_mean(clean_volumes, i, burst_window)
        recent_vol_std = _rolling_std(clean_volumes, i, burst_window)
        if recent_vol_mean is not None and recent_vol_std is not None and recent_vol_std >= 0:
            if recent_vol_std == 0:
                volume_burst = 0.0
            else:
                volume_burst = (clean_volumes[i] - recent_vol_mean) / recent_vol_std
                burst_hist.append(volume_burst)
        if range_width is not None:
            range_hist.append(range_width)

        volatility_bucket = 'unknown'
        if vol_value is not None and vol_hist:
            vol_avg = mean(vol_hist[-200:])
            if vol_value >= vol_avg * 1.5:
                volatility_bucket = 'high'
            elif vol_value <= vol_avg * 0.8:
                volatility_bucket = 'low'
            else:
                volatility_bucket = 'mid'

        market_state = classify_market_state(
            trend_return=trend_return,
            range_width=range_width,
            volatility=vol_value,
            volume_burst=volume_burst,
        )
        out.append({
            'ts': row.get('ts'),
            'timestamp': row.get('timestamp'),
            'close': close,
            'ret_1m': ret_1m,
            'trend_return_60': trend_return,
            'range_width_30': range_width,
            'realized_vol_30': vol_value,
            'volume_burst_z_30': volume_burst,
            'volatility_bucket': volatility_bucket,
            'market_state': market_state,
        })
    return out


def classify_market_state(*, trend_return: float | None, range_width: float | None, volatility: float | None, volume_burst: float | None) -> str:
    abs_trend = abs(trend_return) if trend_return is not None else None
    if volume_burst is not None and volume_burst >= 2.0 and volatility is not None and volatility >= 0.004:
        return 'shock'
    if range_width is not None and range_width <= 0.01 and volatility is not None and volatility <= 0.0015:
        return 'compression'
    if abs_trend is not None and abs_trend >= 0.03:
        return 'trend'
    if range_width is not None and range_width <= 0.02:
        return 'range'
    return 'transition'


def build_ma_performance_cube(
    state_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    *,
    family: str = 'moving_average',
    utility_field: str = 'utility_1h',
) -> dict[str, Any]:
    state_by_ts = {row.get('ts'): row for row in state_rows if row.get('ts') is not None}
    grouped: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    counts: dict[tuple[str, str, str], int] = defaultdict(int)
    for row in candidate_rows:
        ts = row.get('ts')
        state = state_by_ts.get(ts, {}).get('market_state')
        parameter_region = row.get('parameter_region')
        utility = row.get(utility_field)
        if state is None or parameter_region is None or utility is None:
            continue
        key = (state, family, parameter_region)
        grouped[key].append(float(utility))
        counts[key] += 1

    cube_rows = []
    for (state, family_name, parameter_region), values in sorted(grouped.items()):
        cube_rows.append({
            'market_state': state,
            'family': family_name,
            'parameter_region': parameter_region,
            'sample_count': counts[(state, family_name, parameter_region)],
            'avg_utility_1h': mean(values),
            'positive_rate': sum(1 for x in values if x > 0) / len(values),
        })

    return {
        'summary': {
            'state_count': len({row['market_state'] for row in cube_rows}),
            'family_count': len({row['family'] for row in cube_rows}),
            'parameter_region_count': len({row['parameter_region'] for row in cube_rows}),
            'cell_count': len(cube_rows),
            'utility_field': utility_field,
        },
        'rows': cube_rows,
    }


def load_jsonl_rows(path: str | Path) -> list[dict[str, Any]]:
    target = Path(path)
    rows: list[dict[str, Any]] = []
    with target.open('r', encoding='utf-8') as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def write_jsonl_rows(rows: list[dict[str, Any]], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('w', encoding='utf-8') as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + '\n')
    return target


def _series_asof_value(series: list[dict[str, Any]], ts: int, value_key: str, *, max_age_ms: int | None = None) -> tuple[Any, int | None]:
    if not series:
        return None, None
    lo = 0
    hi = len(series) - 1
    best = None
    while lo <= hi:
        mid = (lo + hi) // 2
        row_ts = int(series[mid]['ts'])
        if row_ts <= ts:
            best = series[mid]
            lo = mid + 1
        else:
            hi = mid - 1
    if best is None:
        return None, None
    age_ms = ts - int(best['ts'])
    if max_age_ms is not None and age_ms > max_age_ms:
        return None, age_ms
    return best.get(value_key), age_ms


def build_crypto_market_state_dataset(
    candles: list[dict[str, Any]],
    *,
    funding_rows: list[dict[str, Any]] | None = None,
    basis_rows: list[dict[str, Any]] | None = None,
    symbol: str = 'BTC-USDT-SWAP',
    dataset_version: str = 'crypto_market_state_dataset_v1',
) -> list[dict[str, Any]]:
    state_rows = build_market_state_rows(candles)
    state_by_ts = {int(row['ts']): row for row in state_rows if row.get('ts') is not None}
    funding_series = sorted((funding_rows or []), key=lambda row: int(row['ts']))
    basis_series = sorted((basis_rows or []), key=lambda row: int(row['ts']))
    closes = [_safe_float(row.get('close')) or 0.0 for row in candles]

    dataset: list[dict[str, Any]] = []
    for i, candle in enumerate(candles):
        ts = int(candle['ts'])
        state = state_by_ts.get(ts)
        if not state:
            continue
        funding_rate, funding_age_ms = _series_asof_value(funding_series, ts, 'fundingRate', max_age_ms=12 * 60 * 60 * 1000)
        basis_pct, basis_age_ms = _series_asof_value(basis_series, ts, 'basisPct', max_age_ms=15 * 60 * 1000)
        row = {
            'dataset_version': dataset_version,
            'layer': 'market_state_snapshot',
            'ts': ts,
            'timestamp': candle.get('timestamp'),
            'symbol': symbol,
            'close': _safe_float(candle.get('close')),
            'open': _safe_float(candle.get('open')),
            'high': _safe_float(candle.get('high')),
            'low': _safe_float(candle.get('low')),
            'volume': _safe_float(candle.get('vol')),
            'quote_volume': _safe_float(candle.get('volCcyQuote', candle.get('volCcy'))),
            'return_5m': _forward_return(closes, i - 5, 5) if i >= 5 else None,
            'return_15m': _forward_return(closes, i - 15, 15) if i >= 15 else None,
            'return_1h': _forward_return(closes, i - 60, 60) if i >= 60 else None,
            'ret_1m': state.get('ret_1m'),
            'trend_return_60': state.get('trend_return_60'),
            'range_width_30': state.get('range_width_30'),
            'realized_vol_30': state.get('realized_vol_30'),
            'volume_burst_z_30': state.get('volume_burst_z_30'),
            'volatility_bucket': state.get('volatility_bucket'),
            'market_state': state.get('market_state'),
            'funding_rate': funding_rate,
            'funding_age_min': None if funding_age_ms is None else round(funding_age_ms / 60_000, 3),
            'basis_pct': basis_pct,
            'basis_age_min': None if basis_age_ms is None else round(basis_age_ms / 60_000, 3),
        }
        dataset.append(row)
    return dataset


def build_ma_candidate_dataset(
    candles: list[dict[str, Any]],
    variants: list[dict[str, Any]],
    *,
    horizon_bars: int = 60,
) -> list[dict[str, Any]]:
    from src.research.ma_family import build_ma_baseline_signals

    closes = [_safe_float(row.get('close')) or 0.0 for row in candles]
    dataset: list[dict[str, Any]] = []
    for variant in variants:
        signals = build_ma_baseline_signals(
            candles,
            fast_window=int(variant['fast_window']),
            slow_window=int(variant['slow_window']),
            threshold_enter_pct=float(variant.get('threshold_enter_pct', variant.get('threshold_pct', 0.0))),
            threshold_exit_pct=float(variant.get('threshold_exit_pct', 0.0)),
            ma_type=str(variant.get('ma_type', 'SMA')),
            price_source=str(variant.get('price_source', 'close')),
        )
        for i, signal in enumerate(signals):
            forward_ret = _forward_return(closes, i, horizon_bars)
            if forward_ret is None:
                continue
            position = int(signal.get('position', 0) or 0)
            utility = forward_ret * position
            dataset.append({
                'ts': signal.get('ts'),
                'timestamp': signal.get('timestamp'),
                'family': 'moving_average',
                'variant_id': signal.get('variant'),
                'parameter_region': parameter_region_for_variant(signal.get('variant')),
                'position': position,
                'forward_return_1h': forward_ret,
                'utility_1h': utility,
                'fast_window': variant.get('fast_window'),
                'slow_window': variant.get('slow_window'),
                'threshold_enter_pct': variant.get('threshold_enter_pct', variant.get('threshold_pct', 0.0)),
                'threshold_exit_pct': variant.get('threshold_exit_pct', 0.0),
                'ma_type': variant.get('ma_type', 'SMA'),
                'price_source': variant.get('price_source', 'close'),
            })
    return dataset


def parameter_region_for_variant(variant_id: str | None) -> str:
    if not variant_id:
        return 'unknown'
    if '_te020_' in variant_id or '_te020_tx' in variant_id:
        threshold_band = 'wide_threshold'
    elif '_te010_' in variant_id or '_te010_tx' in variant_id:
        threshold_band = 'mid_threshold'
    else:
        threshold_band = 'tight_threshold'
    if '_50_200_' in variant_id or '_30_90_' in variant_id:
        speed_band = 'slow_windows'
    elif '_20_60_' in variant_id or '_10_30_' in variant_id:
        speed_band = 'mid_windows'
    else:
        speed_band = 'fast_windows'
    return f'{speed_band}__{threshold_band}'
