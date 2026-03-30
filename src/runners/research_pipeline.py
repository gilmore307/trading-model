from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline.research_pipeline import PipelineFailure, load_config, run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Run the continuous research pipeline orchestrator.')
    parser.add_argument('--config', type=Path, default=ROOT / 'config' / 'research_pipeline.json')
    parser.add_argument('--only-step', action='append', default=[])
    parser.add_argument('--skip-step', action='append', default=[])
    parser.add_argument('--run-id', default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_config(args.config)
    try:
        manifest = run_pipeline(
            config,
            only_steps=args.only_step or None,
            skip_steps=args.skip_step or None,
            run_id=args.run_id,
        )
        print(json.dumps({'status': 'ok', 'run_id': manifest['run_id'], 'step_count': len(manifest['steps'])}, ensure_ascii=False, indent=2))
    except PipelineFailure as exc:
        print(json.dumps({'status': 'failed', 'error': str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
