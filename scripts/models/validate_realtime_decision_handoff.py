#!/usr/bin/env python3
"""Validate realtime decision input snapshots or route plans."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from models.realtime_decision_handoff import (
    validate_execution_model_decision_input_snapshot,
    validate_realtime_decision_route_plan,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate realtime model decision handoff JSON without side effects.")
    parser.add_argument("payload_json", help="Path to execution_model_decision_input_snapshot_v1 or model_realtime_decision_route_plan_v1 JSON.")
    args = parser.parse_args()

    payload = json.loads(Path(args.payload_json).read_text(encoding="utf-8"))
    contract_type = payload.get("contract_type")
    if contract_type == "execution_model_decision_input_snapshot_v1":
        result = validate_execution_model_decision_input_snapshot(payload)
    elif contract_type == "model_realtime_decision_route_plan_v1":
        result = validate_realtime_decision_route_plan(payload)
    else:
        raise SystemExit(f"unsupported contract_type: {contract_type!r}")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
