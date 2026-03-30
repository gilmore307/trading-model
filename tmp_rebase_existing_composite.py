import json
from pathlib import Path

root = Path('/root/.openclaw/workspace/projects/crypto-trading/data/derived')
comp_path = root / 'composite_backtest_summary_v1.json'
curves_path = root / 'family_equity_curves_v1.jsonl'

comp = json.loads(comp_path.read_text(encoding='utf-8'))
existing = comp.get('curve') or []

idx_maps = {}
with curves_path.open('r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        idx_maps.setdefault(row['family'], {})[int(row['ts'])] = row

out = []
equity = 1.0
peak = 1.0
prev_ts = None
for row in existing:
    ts = int(row['ts'])
    chosen = row['selected_family']
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
        'state': row.get('state'),
        'selected_family': chosen,
        'equity': equity,
        'drawdown': drawdown,
        'close': chosen_row['close'],
    })
    prev_ts = ts

comp['curve'] = out
comp['summary']['curve_points'] = len(out)
comp['summary']['final_equity'] = out[-1]['equity'] if out else None
comp['summary']['max_drawdown'] = min(float(r['drawdown']) for r in out) if out else None
comp_path.write_text(json.dumps(comp, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({
    'points': len(out),
    'min_equity': min(r['equity'] for r in out) if out else None,
    'max_equity': max(r['equity'] for r in out) if out else None,
    'final_equity': comp['summary']['final_equity'],
    'max_drawdown': comp['summary']['max_drawdown'],
}, ensure_ascii=False))
