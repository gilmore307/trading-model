from __future__ import annotations

import argparse
from dataclasses import asdict
import json

from src.config.settings import Settings
from src.runtime.workflows import OkxWorkflowHooks, run_calibrate_event


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Run calibrate event workflow for crypto-trading.')
    parser.add_argument('--destructive', action='store_true', help='Also clear analysis history after reset helpers.')
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    settings = Settings.load()
    settings.ensure_demo_only()
    result = run_calibrate_event(hooks=OkxWorkflowHooks(settings), destructive=args.destructive)
    print(json.dumps(asdict(result), ensure_ascii=False, default=str, indent=2))


if __name__ == '__main__':
    main()
