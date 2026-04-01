from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.review.export import export_report_artifacts
from src.review.framework import build_weekly_window
from src.runtime.business_time import to_business

DEFAULT_HISTORY_PATH = Path('/root/.openclaw/workspace/projects/crypto-trading/logs/runtime/execution-cycles')


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return to_business(parsed)


def run_weekly_review(
    *,
    now: datetime | None = None,
    history_path: str | Path | None = None,
    out_dir: str | Path | None = None,
) -> dict[str, Any]:
    now = to_business(now or datetime.now(UTC))
    history = Path(history_path) if history_path is not None else DEFAULT_HISTORY_PATH
    window = build_weekly_window(now)
    exported = export_report_artifacts(window, history_path=str(history), out_dir=out_dir, generated_at=now)
    return exported


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Generate weekly trade review artifacts.')
    parser.add_argument('--now', help='ISO-8601 timestamp to anchor the weekly review window (default: current UTC time).')
    parser.add_argument('--history-path', default=str(DEFAULT_HISTORY_PATH), help='Execution history jsonl path.')
    parser.add_argument('--out-dir', help='Output directory for report artifacts.')
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    exported = run_weekly_review(
        now=_parse_dt(args.now),
        history_path=args.history_path,
        out_dir=args.out_dir,
    )
    print(json.dumps({'json_path': exported['json_path'], 'markdown_path': exported['markdown_path']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
