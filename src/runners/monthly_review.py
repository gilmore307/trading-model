from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.review.export import export_report_artifacts
from src.review.framework import build_monthly_window
from src.runtime.business_time import business_month_start, previous_business_month_start, to_business

DEFAULT_HISTORY_PATH = Path('/root/.openclaw/workspace/projects/crypto-trading/logs/runtime/execution-cycles')


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return to_business(parsed)


def run_monthly_review(
    *,
    now: datetime | None = None,
    previous_review_end: datetime | None = None,
    history_path: str | Path | None = None,
    out_dir: str | Path | None = None,
) -> dict[str, Any]:
    now = to_business(now or datetime.now(UTC))
    current_review_end = business_month_start(now)
    previous_end = to_business(previous_review_end) if previous_review_end is not None else previous_business_month_start(now)
    history = Path(history_path) if history_path is not None else DEFAULT_HISTORY_PATH
    window = build_monthly_window(previous_end, current_review_end)
    exported = export_report_artifacts(window, history_path=str(history), out_dir=out_dir, generated_at=now)
    return exported


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Generate monthly trade review artifacts.')
    parser.add_argument('--now', help='ISO-8601 timestamp used to derive the current business-month review boundary in America/New_York (default: current UTC time).')
    parser.add_argument('--previous-review-end', help='ISO-8601 timestamp for the previous monthly review boundary (default: start of previous America/New_York business month).')
    parser.add_argument('--history-path', default=str(DEFAULT_HISTORY_PATH), help='Execution history jsonl path or daily-partitioned directory.')
    parser.add_argument('--out-dir', help='Output directory for report artifacts.')
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    exported = run_monthly_review(
        now=_parse_dt(args.now),
        previous_review_end=_parse_dt(args.previous_review_end),
        history_path=args.history_path,
        out_dir=args.out_dir,
    )
    print(json.dumps({'json_path': exported['json_path'], 'markdown_path': exported['markdown_path']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
