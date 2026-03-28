from __future__ import annotations

import json
from pathlib import Path

STATE_DATASET = Path('data/intermediate/market_state/crypto_market_state_dataset_v1.jsonl')
UNSUPERVISED = Path('data/derived/unsupervised_market_state_baseline_v1.json')
LABELS = Path('data/intermediate/market_state/unsupervised_market_state_labels_v1.jsonl')
OUT = Path('data/derived/market_discovery_btc_v1.json')
PARAMETER_CHANGE_LOG = Path('data/derived/parameter_change_log.json')
SYMBOL = 'BTC-USDT-SWAP'
LIMIT = 4000


def main() -> None:
    rows = []
    with STATE_DATASET.open('r', encoding='utf-8') as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get('symbol') != SYMBOL:
                continue
            rows.append({
                'ts': row.get('ts'),
                'timestamp': row.get('timestamp'),
                'open': row.get('open'),
                'high': row.get('high'),
                'low': row.get('low'),
                'close': row.get('close'),
                'volume': row.get('volume'),
                'manualState': row.get('market_state'),
                'return5m': row.get('return_5m'),
                'return15m': row.get('return_15m'),
                'return1h': row.get('return_1h'),
                'rangeWidth30': row.get('range_width_30'),
                'realizedVol30': row.get('realized_vol_30'),
                'volumeBurstZ30': row.get('volume_burst_z_30'),
                'fundingRate': row.get('funding_rate'),
                'basisPct': row.get('basis_pct'),
            })
    if LIMIT and len(rows) > LIMIT:
        rows = rows[-LIMIT:]

    baseline = json.loads(UNSUPERVISED.read_text(encoding='utf-8')) if UNSUPERVISED.exists() else {}
    clusters = baseline.get('cluster_summary') or []
    cluster_ids = [int(row.get('cluster_id', 0)) for row in clusters if row.get('cluster_id') is not None]
    cluster_count = max(cluster_ids) + 1 if cluster_ids else 5

    cluster_by_ts = {}
    if LABELS.exists():
        with LABELS.open('r', encoding='utf-8') as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                label_row = json.loads(line)
                if label_row.get('symbol') != SYMBOL:
                    continue
                ts = label_row.get('ts')
                cluster_id = label_row.get('cluster_id')
                if ts is None or cluster_id is None:
                    continue
                cluster_by_ts[int(ts)] = int(cluster_id)

    for idx, row in enumerate(rows):
        ts = row.get('ts')
        if ts is not None and int(ts) in cluster_by_ts:
            row['clusterId'] = cluster_by_ts[int(ts)]
        else:
            row['clusterId'] = idx % cluster_count

    parameter_change_log = []
    if PARAMETER_CHANGE_LOG.exists():
        parameter_change_log = (json.loads(PARAMETER_CHANGE_LOG.read_text(encoding='utf-8')) or {}).get('events') or []

    payload = {
        'symbol': SYMBOL,
        'generatedAt': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
        'rows': rows,
        'clusterCount': cluster_count,
        'clusterSummary': clusters,
        'parameterChangeLog': parameter_change_log,
        'note': 'Uses persisted timestamp-level unsupervised labels when available; falls back to approximate placeholder cluster overlay only for missing timestamps.',
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'output': str(OUT), 'rows': len(rows), 'clusterCount': cluster_count}, ensure_ascii=False))


if __name__ == '__main__':
    main()
