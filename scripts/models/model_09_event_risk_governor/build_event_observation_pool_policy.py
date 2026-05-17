#!/usr/bin/env python3
"""Build EventRiskGovernor observation-pool and promotion policy artifacts."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from models.model_09_event_risk_governor.event_observation_pool_policy import (
    DEFAULT_OUTPUT_DIR,
    build_event_observation_pool_policy,
    write_event_observation_pool_policy_artifacts,
    write_policy,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--print-json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    policy = build_event_observation_pool_policy()
    write_event_observation_pool_policy_artifacts(policy, args.output_dir)
    if args.print_json:
        write_policy(policy, output=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
