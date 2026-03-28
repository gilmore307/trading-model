from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.research.bollinger_family import backtest_bollinger_variant, build_bollinger_reversion_signals
from src.research.donchian_family import backtest_donchian_variant, build_donchian_breakout_signals
from src.research.family_registry import family_config, family_names
from src.research.jsonl_utils import load_jsonl_rows
from src.research.ma_family import backtest_ma_variant, build_ma_baseline_signals

DEFAULT_CANDLES = 'data/derived/BTC-USDT-SWAP_1m_recent120k.jsonl'
DEFAULT_STATE_DATASET = 'data/intermediate/market_state/crypto_market_state_dataset_v1.jsonl'
DEFAULT_SUMMARY_OUT = 'data/derived/family_backtest_summary_v1.json'
DEFAULT_CURVES_OUT = 'data/intermediate/dashboard_payloads/family_equity_curves_v1.jsonl'
DEFAULT_LEDGER_OUT = 'data/derived/family_trade_ledger_v1.jsonl'
DEFAULT_COMPOSITE_OUT = 'data/derived/composite_backtest_summary_v1.json'


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Build first-pass trading overview artifacts from recent historical candles.')
    parser.add_argument('--candles', default=DEFAULT_CANDLES)
    parser.add_argument('--state-dataset', default=DEFAULT_STATE_DATASET)
    parser.add_argument('--summary-out', default=DEFAULT_SUMMARY_OUT)
    parser.add_argument('--curves-out', default=DEFAULT_CURVES_OUT)
    parser.add_argument('--ledger-out', default=DEFAULT_LEDGER_OUT)
    parser.add_argument('--composite-out', default=DEFAULT_COMPOSITE_OUT)
    parser.add_argument('--max-variants-per-family', type=int, default=24)
    parser.add_argument('--initial-equity', type=float, default=1.0)
    return parser


def _load_state_by_ts(path: Path, target_ts: set[int]) -> dict[int, str]:
    out: dict[int, str] = {}
    with path.open('r', encoding='utf-8') as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = row.get('ts')
            state = row.get('market_state')
            if ts is None or state is None:
                continue
            ts_int = int(ts)
            if ts_int in target_ts:
                out[ts_int] = str(state)
    return out


def _trade_ledger_from_signals(signals: list[dict[str, Any]], state_by_ts: dict[int, str], *, family: str, variant_id: str) -> list[dict[str, Any]]:
    ledger = []
    open_trade: dict[str, Any] | None = None
    trade_id = 0
    for row in signals:
        position = int(row.get('position', 0) or 0)
        action = row.get('action')
        ts = int(row['ts'])
        if action in {'enter_long', 'enter_short'}:
            if open_trade is not None:
                open_trade['exit_ts'] = ts
                open_trade['exit_timestamp'] = row.get('timestamp')
                open_trade['exit_price'] = float(row['close'])
                open_trade['exit_state'] = state_by_ts.get(ts)
                open_trade['status'] = 'reversed'
                ledger.append(open_trade)
            trade_id += 1
            open_trade = {
                'trade_id': f'{family}_{trade_id:06d}',
                'family': family,
                'variant_id': variant_id,
                'side': 'long' if position > 0 else 'short',
                'entry_ts': ts,
                'entry_timestamp': row.get('timestamp'),
                'entry_price': float(row['close']),
                'entry_state': state_by_ts.get(ts),
                'status': 'open',
            }
        elif action == 'exit_to_flat' and open_trade is not None:
            open_trade['exit_ts'] = ts
            open_trade['exit_timestamp'] = row.get('timestamp')
            open_trade['exit_price'] = float(row['close'])
            open_trade['exit_state'] = state_by_ts.get(ts)
            open_trade['status'] = 'closed'
            entry = float(open_trade['entry_price'])
            exit_ = float(open_trade['exit_price'])
            pnl_pct = ((exit_ / entry) - 1.0) if open_trade['side'] == 'long' else ((entry / exit_) - 1.0)
            open_trade['pnl_pct'] = pnl_pct
            open_trade['holding_bars'] = max(0, (int(open_trade['exit_ts']) - int(open_trade['entry_ts'])) // 60000)
            ledger.append(open_trade)
            open_trade = None
    return ledger


def _curve_from_signals(signals: list[dict[str, Any]], *, family: str, variant_id: str, initial_equity: float) -> list[dict[str, Any]]:
    if not signals:
        return []
    equity = float(initial_equity)
    peak = equity
    position = 0
    curve = [{
        'family': family,
        'variant_id': variant_id,
        'ts': signals[0]['ts'],
        'timestamp': signals[0]['timestamp'],
        'equity': equity,
        'drawdown': 0.0,
        'position': 0,
        'close': float(signals[0]['close']),
    }]
    for i in range(1, len(signals)):
        prev = signals[i - 1]
        row = signals[i]
        prev_close = float(prev['close'])
        close = float(row['close'])
        if prev_close > 0 and position != 0:
            equity *= (1.0 + (((close / prev_close) - 1.0) * position))
        position = int(row.get('position', 0) or 0)
        peak = max(peak, equity)
        drawdown = 0.0 if peak <= 0 else (equity / peak) - 1.0
        curve.append({
            'family': family,
            'variant_id': variant_id,
            'ts': row['ts'],
            'timestamp': row['timestamp'],
            'equity': equity,
            'drawdown': drawdown,
            'position': position,
            'close': close,
        })
    return curve


def _family_signals_and_metrics(family: str, rows: list[dict[str, Any]], variant: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if family == 'moving_average':
        signals = build_ma_baseline_signals(
            rows,
            fast_window=int(variant['fast_window']),
            slow_window=int(variant['slow_window']),
            threshold_enter_pct=float(variant.get('threshold_enter_pct', variant.get('threshold_pct', 0.0))),
            threshold_exit_pct=float(variant.get('threshold_exit_pct', 0.0)),
            ma_type=str(variant.get('ma_type', 'SMA')),
            price_source=str(variant.get('price_source', 'close')),
        )
        metrics = backtest_ma_variant(
            rows,
            fast_window=int(variant['fast_window']),
            slow_window=int(variant['slow_window']),
            threshold_enter_pct=float(variant.get('threshold_enter_pct', variant.get('threshold_pct', 0.0))),
            threshold_exit_pct=float(variant.get('threshold_exit_pct', 0.0)),
            ma_type=str(variant.get('ma_type', 'SMA')),
            price_source=str(variant.get('price_source', 'close')),
        )
        return signals, metrics
    if family == 'donchian_breakout':
        signals = build_donchian_breakout_signals(
            rows,
            breakout_window=int(variant['breakout_window']),
            exit_window=int(variant['exit_window']),
            direction=str(variant.get('direction', 'both')),
            confirm_bars=int(variant.get('confirm_bars', 1)),
            price_source=str(variant.get('price_source', 'close')),
        )
        metrics = backtest_donchian_variant(
            rows,
            breakout_window=int(variant['breakout_window']),
            exit_window=int(variant['exit_window']),
            direction=str(variant.get('direction', 'both')),
            confirm_bars=int(variant.get('confirm_bars', 1)),
            price_source=str(variant.get('price_source', 'close')),
        )
        return signals, metrics
    if family == 'bollinger_reversion':
        signals = build_bollinger_reversion_signals(
            rows,
            window=int(variant['window']),
            std_mult=float(variant.get('std_mult', 2.0)),
            exit_z=float(variant.get('exit_z', 0.5)),
            direction=str(variant.get('direction', 'both')),
            price_source=str(variant.get('price_source', 'close')),
        )
        metrics = backtest_bollinger_variant(
            rows,
            window=int(variant['window']),
            std_mult=float(variant.get('std_mult', 2.0)),
            exit_z=float(variant.get('exit_z', 0.5)),
            direction=str(variant.get('direction', 'both')),
            price_source=str(variant.get('price_source', 'close')),
        )
        return signals, metrics
    raise ValueError(f'unsupported family: {family}')


def _choose_best_variant(family: str, rows: list[dict[str, Any]], max_variants: int) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    cfg = family_config(family)
    if cfg is None:
        raise ValueError(f'missing family config: {family}')
    variants = list(cfg['baseline_variants'])[:max_variants]
    best_variant = None
    best_metrics = None
    best_signals = None
    for variant in variants:
        signals, metrics = _family_signals_and_metrics(family, rows, variant)
        score = (float(metrics.get('total_return', -1e9)), float(metrics.get('win_rate') or -1.0))
        if best_metrics is None or score > (float(best_metrics.get('total_return', -1e9)), float(best_metrics.get('win_rate') or -1.0)):
            best_variant, best_metrics, best_signals = variant, metrics, signals
    assert best_variant is not None and best_metrics is not None and best_signals is not None
    return best_variant, best_metrics, best_signals


def _composite_curve(curves_by_family: dict[str, list[dict[str, Any]]], state_by_ts: dict[int, str], family_state_rank: dict[str, list[str]]) -> list[dict[str, Any]]:
    families = sorted(curves_by_family)
    if not families:
        return []
    base = curves_by_family[families[0]]
    idx_maps = {family: {int(row['ts']): row for row in curve} for family, curve in curves_by_family.items()}
    out = []
    equity = 1.0
    peak = equity
    prev_ts = None
    for row in base:
        ts = int(row['ts'])
        state = state_by_ts.get(ts)
        ranked = family_state_rank.get(state or '', families)
        chosen = next((fam for fam in ranked if ts in idx_maps.get(fam, {})), families[0])
        chosen_row = idx_maps[chosen][ts]

        step_return = 1.0
        if prev_ts is not None:
            prev_chosen_row = idx_maps.get(chosen, {}).get(prev_ts)
            if prev_chosen_row is not None:
                prev_equity = float(prev_chosen_row.get('equity', 1.0) or 1.0)
                curr_equity = float(chosen_row.get('equity', 1.0) or 1.0)
                if prev_equity > 0:
                    step_return = curr_equity / prev_equity
        equity *= step_return
        peak = max(peak, equity)
        drawdown = 0.0 if peak <= 0 else (equity / peak) - 1.0

        out.append({
            'ts': ts,
            'timestamp': row['timestamp'],
            'state': state,
            'selected_family': chosen,
            'equity': equity,
            'drawdown': drawdown,
            'close': chosen_row['close'],
        })
        prev_ts = ts
    return out


def main() -> None:
    args = build_arg_parser().parse_args()
    candles = load_jsonl_rows(Path(args.candles), skip_invalid=True)
    target_ts = {int(row['ts']) for row in candles if row.get('ts') is not None}
    state_by_ts = _load_state_by_ts(Path(args.state_dataset), target_ts)

    summaries = []
    all_curves = []
    all_ledger = []
    curves_by_family: dict[str, list[dict[str, Any]]] = {}
    family_state_perf: dict[str, dict[str, list[float]]] = {}

    for family in family_names():
        best_variant, metrics, signals = _choose_best_variant(family, candles, args.max_variants_per_family)
        variant_id = str(metrics['variant_id'])
        ledger = _trade_ledger_from_signals(signals, state_by_ts, family=family, variant_id=variant_id)
        curve = _curve_from_signals(signals, family=family, variant_id=variant_id, initial_equity=args.initial_equity)
        curves_by_family[family] = curve
        all_curves.extend(curve)
        all_ledger.extend(ledger)

        state_bucket: dict[str, list[float]] = {}
        for trade in ledger:
            state = trade.get('entry_state') or 'unknown'
            pnl_pct = trade.get('pnl_pct')
            if pnl_pct is None:
                continue
            state_bucket.setdefault(str(state), []).append(float(pnl_pct))
        family_state_perf[family] = state_bucket

        summaries.append({
            'family': family,
            'selected_variant_id': best_variant['variant_id'],
            'selected_variant': best_variant,
            **metrics,
            'ledger_trade_count': len(ledger),
            'equity_curve_points': len(curve),
            'state_breakdown': {
                state: {
                    'trade_count': len(values),
                    'avg_trade_return': sum(values) / len(values),
                    'positive_rate': sum(1 for x in values if x > 0) / len(values),
                }
                for state, values in sorted(state_bucket.items()) if values
            },
        })

    family_state_rank: dict[str, list[str]] = {}
    all_states = sorted({state for bucket in family_state_perf.values() for state in bucket})
    for state in all_states:
        ranked = sorted(
            summaries,
            key=lambda row: row['state_breakdown'].get(state, {}).get('avg_trade_return', float('-inf')),
            reverse=True,
        )
        family_state_rank[state] = [row['family'] for row in ranked]

    composite_curve = _composite_curve(curves_by_family, state_by_ts, family_state_rank)
    composite_summary = {
        'family_selection_by_state': {state: families[0] for state, families in family_state_rank.items() if families},
        'curve_points': len(composite_curve),
        'final_equity': None if not composite_curve else composite_curve[-1]['equity'],
        'max_drawdown': None if not composite_curve else min(float(row['drawdown']) for row in composite_curve),
    }

    Path(args.summary_out).write_text(json.dumps({'families': summaries}, ensure_ascii=False, indent=2), encoding='utf-8')
    with Path(args.curves_out).open('w', encoding='utf-8') as handle:
        for row in all_curves:
            handle.write(json.dumps(row, ensure_ascii=False) + '\n')
    with Path(args.ledger_out).open('w', encoding='utf-8') as handle:
        for row in all_ledger:
            handle.write(json.dumps(row, ensure_ascii=False) + '\n')
    Path(args.composite_out).write_text(json.dumps({'summary': composite_summary, 'curve': composite_curve}, ensure_ascii=False, indent=2), encoding='utf-8')

    print(json.dumps({
        'summary_out': args.summary_out,
        'curves_out': args.curves_out,
        'ledger_out': args.ledger_out,
        'composite_out': args.composite_out,
        'families': len(summaries),
        'curve_points': len(all_curves),
        'ledger_rows': len(all_ledger),
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
