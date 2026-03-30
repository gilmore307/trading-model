import json
from pathlib import Path

root = Path('/root/.openclaw/workspace/projects/crypto-trading/data/derived')

curves_by_family = {}
with (root / 'family_equity_curves_v1.jsonl').open('r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        curves_by_family.setdefault(row['family'], []).append(row)

families = sorted(curves_by_family)
base = curves_by_family[families[0]]
target_ts = {int(r['ts']) for r in base}

state_by_ts = {}
with (root / 'crypto_market_state_dataset_v1.jsonl').open('r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        ts = row.get('ts')
        st = row.get('market_state')
        if ts is not None and st is not None:
            ts = int(ts)
            if ts in target_ts:
                state_by_ts[ts] = str(st)

families_summary = json.loads((root / 'family_backtest_summary_v1.json').read_text(encoding='utf-8'))['families']
all_states = sorted({state for fam in families_summary for state in (fam.get('state_breakdown') or {})})
family_state_rank = {}
for state in all_states:
    ranked = sorted(
        families_summary,
        key=lambda row: row.get('state_breakdown', {}).get(state, {}).get('avg_trade_return', float('-inf')),
        reverse=True,
    )
    family_state_rank[state] = [row['family'] for row in ranked]

idx_maps = {family: {int(r['ts']): r for r in curve} for family, curve in curves_by_family.items()}
out = []
equity = 1.0
peak = 1.0
prev_ts = None
for row in base:
    ts = int(row['ts'])
    state = state_by_ts.get(ts)
    ranked = family_state_rank.get(state or '', families)
    chosen = next((fam for fam in ranked if ts in idx_maps.get(fam, {})), families[0])
    chosen_row = idx_maps[chosen][ts]

    step_return = 1.0
    if prev_ts is not None:
        prev_chosen = idx_maps.get(chosen, {}).get(prev_ts)
        if prev_chosen is not None:
            prev_equity = float(prev_chosen.get('equity', 1.0) or 1.0)
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

comp_path = root / 'composite_backtest_summary_v1.json'
obj = json.loads(comp_path.read_text(encoding='utf-8'))
obj['curve'] = out
obj['summary']['curve_points'] = len(out)
obj['summary']['final_equity'] = out[-1]['equity'] if out else None
obj['summary']['max_drawdown'] = min(float(r['drawdown']) for r in out) if out else None
comp_path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({
    'points': len(out),
    'min_equity': min(r['equity'] for r in out) if out else None,
    'max_equity': max(r['equity'] for r in out) if out else None,
    'final_equity': obj['summary']['final_equity'],
    'max_drawdown': obj['summary']['max_drawdown'],
}, ensure_ascii=False))
