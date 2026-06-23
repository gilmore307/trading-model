#!/usr/bin/env python3
"""Write the current replay entry-utility bundle for M05 alpha confidence.

The current replay contract derives entry utility from point-in-time M02/M03
state inside trading-evaluation. This entrypoint exists so manager-owned replay
can materialize a fold-scoped artifact before execution without activating a
model, calling providers, mutating SQL, or touching broker/account state.
"""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


MODEL_ID = "model_05_alpha_confidence"
MODEL_VERSION = "current_replay_entry_utility"
CONTRACT_TYPE = "current_replay_entry_utility_model_bundle"
HORIZONS = ("10min", "1h", "1D", "1W")


def build_artifact(
    *,
    source_start: str | None,
    source_end: str | None,
    all_horizons: bool,
    from_database: bool,
    generated_at_utc: str | None = None,
) -> dict[str, Any]:
    """Build the side-effect-free replay utility artifact."""

    horizons = list(HORIZONS if all_horizons else ("1W",))
    return {
        "contract_type": CONTRACT_TYPE,
        "schema_version": "2026-06-23",
        "model_id": MODEL_ID,
        "model_version": MODEL_VERSION,
        "model_type": "replay_entry_utility_policy_bundle",
        "score_policy": "derive_from_current_m02_m03_state",
        "score_semantics": "entry utility confidence derived at replay time from point-in-time target and event state",
        "horizons": horizons,
        "source_window": {
            "source_start": source_start,
            "source_end": source_end,
        },
        "selected_thresholds": {
            "minimum_entry_alpha_confidence": 0.50,
            "minimum_trade_intensity": 0.05,
        },
        "training_summary": {
            "training_mode": "policy_bundle_no_supervised_fit",
            "source": "database" if from_database else "local",
            "sample_count": None,
            "reason": "current replay computes utility from already materialized M02/M03 state",
        },
        "safety": {
            "provider_calls_performed": False,
            "model_activation_performed": False,
            "broker_execution_performed": False,
            "account_mutation_performed": False,
            "sql_mutation_performed": False,
        },
        "generated_at_utc": generated_at_utc or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }


def write_artifact(path: Path, artifact: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-database", action="store_true", help="Record that the request is tied to database-backed fold scope.")
    parser.add_argument("--all-horizons", action="store_true", help="Emit the current model decision horizon grid.")
    parser.add_argument("--source-start")
    parser.add_argument("--source-end")
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args(argv)

    artifact = build_artifact(
        source_start=args.source_start,
        source_end=args.source_end,
        all_horizons=args.all_horizons,
        from_database=args.from_database,
    )
    write_artifact(args.output_json, artifact)
    print(json.dumps({"status": "succeeded", "output_json": str(args.output_json), "contract_type": CONTRACT_TYPE}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
