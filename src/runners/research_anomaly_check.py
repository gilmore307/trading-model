from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline.anomaly_rules import evaluate_rules, load_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Run rule-based anomaly checks for the research pipeline.')
    parser.add_argument('--config', type=Path, default=ROOT / 'config' / 'research_pipeline.json')
    parser.add_argument('--out', type=Path, default=ROOT / 'logs' / 'pipeline' / 'state' / 'latest_anomalies.json')
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_json(args.config)
    result = evaluate_rules(config)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result['status'] != 'ok':
        raise SystemExit(2)


if __name__ == '__main__':
    main()
