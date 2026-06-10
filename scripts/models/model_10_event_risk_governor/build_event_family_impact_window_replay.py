#!/usr/bin/env python3
"""Apply Layer 10 impact-window event context to frozen replay decision rows."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from models.model_10_event_risk_governor.event_family_impact_window_replay import (
    DEFAULT_EVENT_CSV,
    DEFAULT_FOLD_ID,
    DEFAULT_IMPACT_WINDOW_SUMMARY,
    DEFAULT_MAX_SQL_DATES_PER_FAMILY,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_REPLAY_DECISION_ROWS,
    DEFAULT_REPLAY_RUN_ID,
    DEFAULT_STORAGE_SECRET_ALIAS,
    build_impact_window_replay_artifacts,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay-decision-rows", type=Path, default=DEFAULT_REPLAY_DECISION_ROWS)
    parser.add_argument("--event-csv", type=Path, default=DEFAULT_EVENT_CSV)
    parser.add_argument("--impact-window-summary", type=Path, default=DEFAULT_IMPACT_WINDOW_SUMMARY)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--fold-id", default=DEFAULT_FOLD_ID)
    parser.add_argument("--replay-run-id", default=DEFAULT_REPLAY_RUN_ID)
    parser.add_argument("--database-url")
    parser.add_argument("--storage-secret-alias", default=DEFAULT_STORAGE_SECRET_ALIAS)
    parser.add_argument("--max-sql-dates-per-family", type=int, default=DEFAULT_MAX_SQL_DATES_PER_FAMILY)
    parser.add_argument("--no-sql-candidate-events", action="store_true")
    parser.add_argument("--print-json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_impact_window_replay_artifacts(
        replay_decision_rows=args.replay_decision_rows,
        event_csv=args.event_csv,
        impact_window_summary=args.impact_window_summary,
        output_dir=args.output_dir,
        fold_id=args.fold_id,
        replay_run_id=args.replay_run_id,
        include_sql_candidate_events=not args.no_sql_candidate_events,
        database_url=args.database_url,
        storage_secret_alias=args.storage_secret_alias,
        max_sql_dates_per_family=args.max_sql_dates_per_family,
    )
    if args.print_json:
        json.dump(result.to_dict(), sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
