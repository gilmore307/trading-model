#!/usr/bin/env python3
"""Plan realtime decision handoff into the historical model stack."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from models.realtime_decision_handoff import build_realtime_decision_route_plan


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build model_realtime_decision_route_plan_v1 from execution_model_decision_input_snapshot_v1."
    )
    parser.add_argument("decision_input_snapshot", help="Path to execution_model_decision_input_snapshot_v1 JSON.")
    parser.add_argument("--handoff-mode", choices=("fixture_replay", "shadow_monitoring"), default="shadow_monitoring")
    parser.add_argument("--route-plan-id")
    args = parser.parse_args()

    snapshot = json.loads(Path(args.decision_input_snapshot).read_text(encoding="utf-8"))
    payload = {
        "decision_input_snapshot": snapshot,
        "handoff_mode": args.handoff_mode,
    }
    if args.route_plan_id:
        payload["route_plan_id"] = args.route_plan_id
    print(json.dumps(build_realtime_decision_route_plan(payload), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
