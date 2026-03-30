from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.research.family_registry import family_config
from src.research.jsonl_utils import load_jsonl_rows
from src.runners.build_trading_overview_backtest import (
    _curve_from_signals,
    _family_signals_and_metrics,
    _trade_ledger_from_signals,
)

DEFAULT_CANDLES = 'data/derived/BTC-USDT-SWAP_1m_recent120k.jsonl'
DEFAULT_STATE_DATASET = 'data/intermediate/market_state/crypto_market_state_dataset_v1.jsonl'
DEFAULT_CLUSTER_LABELS = 'data/intermediate/market_state/unsupervised_market_state_labels_v1.jsonl'
DEFAULT_OUT_DIR = 'data/intermediate/dashboard_payloads/family_variant_dashboard'
DEFAULT_EXISTING_COMPOSITE = 'data/derived/composite_backtest_summary_v1.json'


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Build per-family all-variant dashboard artifacts.')
    parser.add_argument('--family', required=True)
    parser.add_argument('--candles', default=DEFAULT_CANDLES)
    parser.add_argument('--state-dataset', default=DEFAULT_STATE_DATASET)
    parser.add_argument('--cluster-labels', default=DEFAULT_CLUSTER_LABELS)
    parser.add_argument('--out-dir', default=DEFAULT_OUT_DIR)
    parser.add_argument('--existing-composite', default=DEFAULT_EXISTING_COMPOSITE)
    parser.add_argument('--initial-equity', type=float, default=1.0)
    parser.add_argument('--limit-variants', type=int, default=0)
    parser.add_argument('--resume', action='store_true', help='Resume from already-split variant files if present.')
    return parser


def _load_state_by_ts_fast(path: Path, target_ts: set[int]) -> dict[int, str]:
    out: dict[int, str] = {}
    remaining = len(target_ts)
    if remaining == 0:
        return out
    with path.open('r', encoding='utf-8') as handle:
        for line in handle:
            if remaining <= 0:
                break
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
            if ts_int in target_ts and ts_int not in out:
                out[ts_int] = str(state)
                remaining -= 1
    return out


def _load_state_by_ts_from_existing_composite(path: Path, target_ts: set[int]) -> dict[int, str]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}
    out: dict[int, str] = {}
    for row in obj.get('curve') or []:
        ts = row.get('ts')
        state = row.get('state')
        if ts is None or state is None:
            continue
        ts_int = int(ts)
        if ts_int in target_ts:
            out[ts_int] = str(state)
    return out


def _load_cluster_by_ts(path: Path, target_ts: set[int]) -> dict[int, int]:
    out: dict[int, int] = {}
    remaining = len(target_ts)
    if remaining == 0 or not path.exists():
        return out
    with path.open('r', encoding='utf-8') as handle:
        for line in handle:
            if remaining <= 0:
                break
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = row.get('ts')
            cluster_id = row.get('cluster_id')
            if ts is None or cluster_id is None:
                continue
            ts_int = int(ts)
            if ts_int in target_ts and ts_int not in out:
                out[ts_int] = int(cluster_id)
                remaining -= 1
    return out


def _composite_variant_curve(curves_by_variant: dict[str, list[dict[str, Any]]], state_by_ts: dict[int, str], variant_state_rank: dict[str, list[str]], cluster_by_ts: dict[int, int]) -> list[dict[str, Any]]:
    variants = sorted(curves_by_variant)
    if not variants:
        return []
    base = curves_by_variant[variants[0]]
    idx_maps = {variant: {int(row['ts']): row for row in curve} for variant, curve in curves_by_variant.items()}
    out = []
    equity = 1.0
    peak = equity
    prev_ts = None
    for row in base:
        ts = int(row['ts'])
        state = state_by_ts.get(ts)
        ranked = variant_state_rank.get(state or '', variants)
        chosen = next((variant for variant in ranked if ts in idx_maps.get(variant, {})), variants[0])
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
            'cluster_id': cluster_by_ts.get(ts),
            'selected_variant_id': chosen,
            'equity': equity,
            'drawdown': drawdown,
            'close': chosen_row['close'],
        })
        prev_ts = ts
    return out


def main() -> None:
    args = build_arg_parser().parse_args()
    cfg = family_config(args.family)
    if cfg is None:
        raise SystemExit(f'unknown family: {args.family}')

    candles = load_jsonl_rows(Path(args.candles), skip_invalid=True)
    print(json.dumps({'stage': 'candles_loaded', 'rows': len(candles)}, ensure_ascii=False), flush=True)
    target_ts = {int(row['ts']) for row in candles if row.get('ts') is not None}
    state_by_ts = _load_state_by_ts_from_existing_composite(Path(args.existing_composite), target_ts)
    state_source = 'existing_composite'
    if len(state_by_ts) < len(target_ts):
        fallback = _load_state_by_ts_fast(Path(args.state_dataset), target_ts - set(state_by_ts))
        state_by_ts.update(fallback)
        state_source = 'existing_composite+state_dataset'
    print(json.dumps({'stage': 'state_loaded', 'matched_ts': len(state_by_ts), 'source': state_source}, ensure_ascii=False), flush=True)
    cluster_by_ts = _load_cluster_by_ts(Path(args.cluster_labels), target_ts)
    print(json.dumps({'stage': 'cluster_loaded', 'matched_ts': len(cluster_by_ts)}, ensure_ascii=False), flush=True)

    variants = list(cfg['baseline_variants'])
    if args.limit_variants and args.limit_variants > 0:
        variants = variants[: args.limit_variants]

    out_dir = Path(args.out_dir)
    family_dir = out_dir / args.family
    variants_dir = family_dir / 'variants'
    variants_dir.mkdir(parents=True, exist_ok=True)

    summaries = []
    curves_by_variant: dict[str, list[dict[str, Any]]] = {}
    variant_payloads: dict[str, dict[str, Any]] = {}
    variant_state_perf: dict[str, dict[str, list[float]]] = {}

    for idx, variant in enumerate(variants, start=1):
        variant_id = str(variant['variant_id'])
        safe_variant = ''.join(ch for ch in variant_id if ch.isalnum() or ch in {'_', '-'})
        variant_path = variants_dir / f'{safe_variant}.json'
        print(json.dumps({'stage': 'variant_start', 'idx': idx, 'total': len(variants), 'variant_id': variant_id}, ensure_ascii=False), flush=True)

        payload = None
        if args.resume and variant_path.exists():
            try:
                payload = json.loads(variant_path.read_text(encoding='utf-8'))
            except Exception:
                payload = None
            if payload is not None:
                print(json.dumps({'stage': 'variant_resume_skip', 'idx': idx, 'total': len(variants), 'variant_id': variant_id, 'path': str(variant_path)}, ensure_ascii=False), flush=True)

        if payload is None:
            signals, metrics = _family_signals_and_metrics(args.family, candles, variant)
            ledger = _trade_ledger_from_signals(signals, state_by_ts, family=args.family, variant_id=variant_id)
            curve = _curve_from_signals(signals, family=args.family, variant_id=variant_id, initial_equity=args.initial_equity)

            state_bucket: dict[str, list[float]] = {}
            for trade in ledger:
                state = str(trade.get('entry_state') or 'unknown')
                pnl_pct = trade.get('pnl_pct')
                if pnl_pct is None:
                    continue
                state_bucket.setdefault(state, []).append(float(pnl_pct))

            summary_row = {
                'family': args.family,
                'variant_id': variant_id,
                'variant': variant,
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
            }
            payload = {
                'family': args.family,
                'variant_id': variant_id,
                'summary': summary_row,
                'curve': curve,
                'ledger': ledger,
            }
            variant_path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
            print(json.dumps({'stage': 'variant_done', 'idx': idx, 'total': len(variants), 'variant_id': variant_id, 'trades': len(ledger), 'curve_points': len(curve)}, ensure_ascii=False), flush=True)

        summary_row = payload['summary']
        curve = payload.get('curve') or []
        curves_by_variant[variant_id] = curve
        summaries.append(summary_row)
        variant_payloads[variant_id] = payload

    variant_state_rank: dict[str, list[str]] = {}
    all_states = sorted({state for row in summaries for state in (row.get('state_breakdown') or {})})
    for state in all_states:
        ranked = sorted(
            summaries,
            key=lambda row: (row.get('state_breakdown') or {}).get(state, {}).get('avg_trade_return', float('-inf')),
            reverse=True,
        )
        variant_state_rank[state] = [row['variant_id'] for row in ranked]

    composite_curve = _composite_variant_curve(curves_by_variant, state_by_ts, variant_state_rank, cluster_by_ts)
    composite_summary = {
        'selected_variant_by_state': {state: ranked_variants[0] for state, ranked_variants in variant_state_rank.items() if ranked_variants},
        'curve_points': len(composite_curve),
        'final_equity': None if not composite_curve else composite_curve[-1]['equity'],
        'max_drawdown': None if not composite_curve else min(float(row['drawdown']) for row in composite_curve),
    }

    out_dir = Path(args.out_dir)
    family_dir = out_dir / args.family
    variants_dir = family_dir / 'variants'
    variants_dir.mkdir(parents=True, exist_ok=True)

    summary_payload = {
        'family': args.family,
        'variant_count': len(summaries),
        'summary': summaries,
    }
    composite_payload = {
        'family': args.family,
        'summary': composite_summary,
        'curve': composite_curve,
    }

    (family_dir / 'summary.json').write_text(json.dumps(summary_payload, ensure_ascii=False), encoding='utf-8')
    (family_dir / 'composite.json').write_text(json.dumps(composite_payload, ensure_ascii=False), encoding='utf-8')
    for variant_id, payload in variant_payloads.items():
        safe_variant = ''.join(ch for ch in variant_id if ch.isalnum() or ch in {'_', '-'})
        (variants_dir / f'{safe_variant}.json').write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')

    # compatibility monolith for current consumers during migration
    compat_path = out_dir / f'{args.family}.json'
    compat_path.write_text(json.dumps({
        'family': args.family,
        'summary': summaries,
        'curves': [row for payload in variant_payloads.values() for row in payload['curve']],
        'ledger': [row for payload in variant_payloads.values() for row in payload['ledger']],
        'composite': {
            'summary': composite_summary,
            'curve': composite_curve,
        },
    }, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'family': args.family, 'variants': len(summaries), 'out_dir': str(family_dir), 'compat_out': str(compat_path)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
