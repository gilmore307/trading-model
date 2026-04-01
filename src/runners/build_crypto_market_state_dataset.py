from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.research.market_state import classify_market_state
from src.research.monthly_jsonl import load_monthly_jsonl_rows

DEFAULT_OKX_CANDLES = 'data/raw/BTC-USDT-SWAP/candles'
DEFAULT_BITGET_FUNDING = 'data/raw/BTCUSDT/funding'
DEFAULT_BITGET_BASIS = 'data/raw/BTCUSDT/basis_proxy'
DEFAULT_OUT = 'data/intermediate/market_state/crypto_market_state_dataset_v1.jsonl'

VOL_WINDOW = 30
TREND_WINDOW = 60
RANGE_WINDOW = 30
BURST_WINDOW = 30
VOL_BUCKET_LOOKBACK = 200
FUNDING_MAX_AGE_MS = 12 * 60 * 60 * 1000
BASIS_MAX_AGE_MS = 15 * 60 * 1000


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _series_asof_value(series: list[dict[str, Any]], idx: int, ts: int, value_key: str, max_age_ms: int) -> tuple[Any, int | None, int]:
    while idx + 1 < len(series) and int(series[idx + 1]['ts']) <= ts:
        idx += 1
    if idx < 0 or idx >= len(series):
        return None, None, idx
    age_ms = ts - int(series[idx]['ts'])
    if age_ms < 0 or age_ms > max_age_ms:
        return None, age_ms, idx
    return series[idx].get(value_key), age_ms, idx


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Build crypto_market_state_dataset_v1 from OKX candles + Bitget funding + Bitget basis proxy.')
    parser.add_argument('--okx-candles', default=DEFAULT_OKX_CANDLES)
    parser.add_argument('--bitget-funding', default=DEFAULT_BITGET_FUNDING)
    parser.add_argument('--bitget-basis', default=DEFAULT_BITGET_BASIS)
    parser.add_argument('--out', default=DEFAULT_OUT)
    parser.add_argument('--symbol', default='BTC-USDT-SWAP')
    parser.add_argument('--progress-every', type=int, default=100000)
    parser.add_argument('--resume', action='store_true', help='Resume from the last written output row if the output file already exists.')
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()

    funding_rows = load_monthly_jsonl_rows(args.bitget_funding)
    basis_rows = load_monthly_jsonl_rows(args.bitget_basis)
    candle_rows = load_monthly_jsonl_rows(args.okx_candles)
    funding_idx = -1
    basis_idx = -1

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    close_hist: deque[float] = deque(maxlen=max(TREND_WINDOW + 1, 61))
    high_hist: deque[float] = deque(maxlen=RANGE_WINDOW)
    low_hist: deque[float] = deque(maxlen=RANGE_WINDOW)
    volume_hist: deque[float] = deque(maxlen=BURST_WINDOW)
    ret_hist: deque[float] = deque(maxlen=VOL_WINDOW)
    vol_hist: deque[float] = deque(maxlen=VOL_BUCKET_LOOKBACK)

    rows_written = 0
    funding_non_null_rows = 0
    basis_non_null_rows = 0
    start_ts = None
    end_ts = None
    resume_after_ts = None

    if args.resume and out_path.exists():
        with out_path.open('r', encoding='utf-8') as existing:
            for line in existing:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                ts = int(row['ts'])
                close = _safe_float(row.get('close'))
                high = _safe_float(row.get('high'))
                low = _safe_float(row.get('low'))
                quote_volume = _safe_float(row.get('quote_volume'))
                realized_vol_30 = _safe_float(row.get('realized_vol_30'))
                ret_1m = _safe_float(row.get('ret_1m'))

                if close is not None:
                    close_hist.append(close)
                    high_hist.append(close if high is None else high)
                    low_hist.append(close if low is None else low)
                volume_hist.append(0.0 if quote_volume is None else quote_volume)
                if ret_1m is not None:
                    ret_hist.append(ret_1m)
                if realized_vol_30 is not None:
                    vol_hist.append(realized_vol_30)
                if row.get('funding_rate') is not None:
                    funding_non_null_rows += 1
                if row.get('basis_pct') is not None:
                    basis_non_null_rows += 1
                rows_written += 1
                if start_ts is None:
                    start_ts = ts
                end_ts = ts
                resume_after_ts = ts

        if resume_after_ts is not None:
            while funding_idx + 1 < len(funding_rows) and int(funding_rows[funding_idx + 1]['ts']) <= resume_after_ts:
                funding_idx += 1
            while basis_idx + 1 < len(basis_rows) and int(basis_rows[basis_idx + 1]['ts']) <= resume_after_ts:
                basis_idx += 1
            print(json.dumps({
                'event': 'resume',
                'resume_after_ts': resume_after_ts,
                'rows_written': rows_written,
                'funding_non_null_rows': funding_non_null_rows,
                'basis_non_null_rows': basis_non_null_rows,
            }, ensure_ascii=False), flush=True)

    output_mode = 'a' if args.resume and out_path.exists() else 'w'

    with out_path.open(output_mode, encoding='utf-8') as out:
        for candle in candle_rows:
            ts = int(candle['ts'])
            if resume_after_ts is not None and ts <= resume_after_ts:
                continue
            close = _safe_float(candle.get('close'))
            open_ = _safe_float(candle.get('open'))
            high = _safe_float(candle.get('high'))
            low = _safe_float(candle.get('low'))
            volume = _safe_float(candle.get('vol'))
            quote_volume = _safe_float(candle.get('volCcyQuote', candle.get('volCcy')))
            if close is None or close <= 0:
                continue

            prev_close = close_hist[-1] if close_hist else None
            ret_1m = None if prev_close in (None, 0) else (close / prev_close) - 1.0
            if ret_1m is not None:
                ret_hist.append(ret_1m)

            close_hist.append(close)
            high_hist.append(close if high is None else high)
            low_hist.append(close if low is None else low)
            volume_hist.append(0.0 if quote_volume is None else quote_volume)

            trend_return_60 = None
            if len(close_hist) >= TREND_WINDOW + 1:
                trend_anchor = close_hist[-(TREND_WINDOW + 1)]
                if trend_anchor > 0:
                    trend_return_60 = (close / trend_anchor) - 1.0

            range_width_30 = None
            if len(high_hist) >= RANGE_WINDOW and len(low_hist) >= RANGE_WINDOW:
                intrarange_high = max(high_hist)
                intrarange_low = min(low_hist)
                range_width_30 = (intrarange_high - intrarange_low) / close if close > 0 else None

            realized_vol_30 = None
            if len(ret_hist) >= VOL_WINDOW:
                realized_vol_30 = pstdev(ret_hist)
                vol_hist.append(realized_vol_30)

            volume_burst_z_30 = None
            if len(volume_hist) >= BURST_WINDOW:
                vol_mean = mean(volume_hist)
                vol_std = pstdev(volume_hist) if len(volume_hist) >= 2 else 0.0
                if vol_std == 0:
                    volume_burst_z_30 = 0.0
                else:
                    volume_burst_z_30 = (volume_hist[-1] - vol_mean) / vol_std

            volatility_bucket = 'unknown'
            if realized_vol_30 is not None and len(vol_hist) > 0:
                vol_avg = mean(vol_hist)
                if realized_vol_30 >= vol_avg * 1.5:
                    volatility_bucket = 'high'
                elif realized_vol_30 <= vol_avg * 0.8:
                    volatility_bucket = 'low'
                else:
                    volatility_bucket = 'mid'

            market_state = classify_market_state(
                trend_return=trend_return_60,
                range_width=range_width_30,
                volatility=realized_vol_30,
                volume_burst=volume_burst_z_30,
            )

            funding_rate, funding_age_ms, funding_idx = _series_asof_value(funding_rows, funding_idx, ts, 'fundingRate', FUNDING_MAX_AGE_MS)
            basis_pct, basis_age_ms, basis_idx = _series_asof_value(basis_rows, basis_idx, ts, 'basisPct', BASIS_MAX_AGE_MS)

            if funding_rate is not None:
                funding_non_null_rows += 1
            if basis_pct is not None:
                basis_non_null_rows += 1

            row = {
                'dataset_version': 'crypto_market_state_dataset_v1',
                'layer': 'market_state_snapshot',
                'ts': ts,
                'timestamp': candle.get('timestamp'),
                'symbol': args.symbol,
                'close': close,
                'open': open_,
                'high': high,
                'low': low,
                'volume': volume,
                'quote_volume': quote_volume,
                'return_5m': (close / close_hist[-6]) - 1.0 if len(close_hist) >= 6 and close_hist[-6] > 0 else None,
                'return_15m': (close / close_hist[-16]) - 1.0 if len(close_hist) >= 16 and close_hist[-16] > 0 else None,
                'return_1h': (close / close_hist[-61]) - 1.0 if len(close_hist) >= 61 and close_hist[-61] > 0 else None,
                'ret_1m': ret_1m,
                'trend_return_60': trend_return_60,
                'range_width_30': range_width_30,
                'realized_vol_30': realized_vol_30,
                'volume_burst_z_30': volume_burst_z_30,
                'volatility_bucket': volatility_bucket,
                'market_state': market_state,
                'funding_rate': funding_rate,
                'funding_age_min': None if funding_age_ms is None else round(funding_age_ms / 60_000, 3),
                'basis_pct': basis_pct,
                'basis_age_min': None if basis_age_ms is None else round(basis_age_ms / 60_000, 3),
            }
            out.write(json.dumps(row, ensure_ascii=False) + '\n')

            rows_written += 1
            if start_ts is None:
                start_ts = ts
            end_ts = ts
            if rows_written % args.progress_every == 0:
                print(json.dumps({
                    'event': 'progress',
                    'rows_written': rows_written,
                    'start_ts': start_ts,
                    'end_ts': end_ts,
                    'funding_non_null_rows': funding_non_null_rows,
                    'basis_non_null_rows': basis_non_null_rows,
                }, ensure_ascii=False), flush=True)

    print(json.dumps({
        'output': str(out_path),
        'rows': rows_written,
        'symbol': args.symbol,
        'start_ts': start_ts,
        'end_ts': end_ts,
        'funding_non_null_rows': funding_non_null_rows,
        'basis_non_null_rows': basis_non_null_rows,
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
