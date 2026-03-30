from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = ROOT / 'config' / 'research_pipeline.json'


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def evaluate_rules(config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = config or load_json(DEFAULT_CONFIG_PATH)
    artifacts = cfg.get('artifacts', {})
    alerts: list[dict[str, Any]] = []

    labels_summary = load_json(artifacts['labels_summary']) if Path(artifacts['labels_summary']).exists() else None
    evaluation = load_json(artifacts['unsupervised_evaluation']) if Path(artifacts['unsupervised_evaluation']).exists() else None

    if labels_summary:
        counts = labels_summary.get('cluster_counts') or []
        total = sum(int(row.get('row_count', 0)) for row in counts)
        if total > 0 and counts:
            largest = max(counts, key=lambda row: int(row.get('row_count', 0)))
            dominance = int(largest.get('row_count', 0)) / total
            if dominance >= 0.80:
                alerts.append({
                    'severity': 'warn',
                    'rule': 'cluster_dominance_high',
                    'message': f"largest cluster dominance too high: {dominance:.2%}",
                    'cluster_id': largest.get('cluster_id'),
                    'dominance': dominance,
                })

    if evaluation:
        summary = evaluation.get('summary') or {}
        weighted_spread = float(summary.get('weighted_avg_cluster_spread', 0.0) or 0.0)
        if weighted_spread <= 2e-05:
            alerts.append({
                'severity': 'warn',
                'rule': 'weighted_spread_low',
                'message': f"weighted average cluster spread is low: {weighted_spread:.8f}",
                'weighted_avg_cluster_spread': weighted_spread,
            })
        if int(summary.get('cluster_count', 0) or 0) < 3:
            alerts.append({
                'severity': 'error',
                'rule': 'cluster_count_too_low',
                'message': 'cluster count below minimum useful threshold',
                'cluster_count': summary.get('cluster_count'),
            })

    return {
        'status': 'alert' if alerts else 'ok',
        'alert_count': len(alerts),
        'alerts': alerts,
    }
