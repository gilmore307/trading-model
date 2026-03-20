from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

OKX_HISTORY_CANDLES_URL = "https://www.okx.com/api/v5/market/history-candles"
DEFAULT_SLEEP_SECONDS = 0.12
DEFAULT_LIMIT = 100
DEFAULT_INST_ID = "BTC-USDT"
DEFAULT_BAR = "1m"


def parse_time_to_ms(value: str) -> int:
    value = value.strip()
    if value.isdigit():
        return int(value)
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return int(dt.timestamp() * 1000)


def fetch_page(*, inst_id: str, bar: str, limit: int, after: int | None = None) -> list[list[str]]:
    params = {
        "instId": inst_id,
        "bar": bar,
        "limit": str(limit),
    }
    if after is not None:
        params["after"] = str(after)
    resp = requests.get(OKX_HISTORY_CANDLES_URL, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != "0":
        raise RuntimeError(f"OKX error: {data}")
    rows = data.get("data", [])
    if not isinstance(rows, list):
        raise RuntimeError(f"unexpected OKX payload: {data}")
    return rows


def normalize_row(row: list[str], *, inst_id: str, bar: str) -> dict[str, Any]:
    ts = int(row[0])
    return {
        "exchange": "okx",
        "endpoint": "history-candles",
        "instId": inst_id,
        "bar": bar,
        "ts": ts,
        "timestamp": datetime.fromtimestamp(ts / 1000, tz=UTC).isoformat(),
        "open": float(row[1]),
        "high": float(row[2]),
        "low": float(row[3]),
        "close": float(row[4]),
        "vol": float(row[5]),
        "volCcy": float(row[6]),
        "volCcyQuote": float(row[7]),
        "confirm": int(row[8]),
    }


def default_output_path(*, inst_id: str, bar: str) -> Path:
    safe_inst = inst_id.replace("/", "-")
    return Path("data/raw/okx/candles") / safe_inst / bar / f"{safe_inst}_{bar}.jsonl"


def load_existing_rows(path: Path) -> dict[int, dict[str, Any]]:
    existing: dict[int, dict[str, Any]] = {}
    if not path.exists():
        return existing
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            existing[int(row["ts"])] = row
    return existing


def write_jsonl(rows_by_ts: dict[int, dict[str, Any]], path: Path, *, only_confirmed: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for ts in sorted(rows_by_ts.keys()):
            row = rows_by_ts[ts]
            if only_confirmed and int(row.get("confirm", 0)) != 1:
                continue
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def fetch_history_range(
    *,
    inst_id: str,
    bar: str,
    limit: int,
    sleep_seconds: float,
    start_ms: int | None,
    end_ms: int | None,
    max_pages: int | None,
    rows_by_ts: dict[int, dict[str, Any]],
    progress_every: int,
) -> tuple[dict[int, dict[str, Any]], int]:
    after: int | None = end_ms
    pages = 0
    while True:
        if max_pages is not None and pages >= max_pages:
            break
        rows = fetch_page(inst_id=inst_id, bar=bar, limit=limit, after=after)
        if not rows:
            break
        pages += 1
        min_ts = min(int(r[0]) for r in rows)
        max_ts = max(int(r[0]) for r in rows)
        kept = 0
        for raw in rows:
            normalized = normalize_row(raw, inst_id=inst_id, bar=bar)
            ts = int(normalized["ts"])
            if end_ms is not None and ts > end_ms:
                continue
            if start_ms is not None and ts < start_ms:
                continue
            rows_by_ts[ts] = normalized
            kept += 1
        if pages % progress_every == 0:
            oldest = min(rows_by_ts.keys()) if rows_by_ts else None
            newest = max(rows_by_ts.keys()) if rows_by_ts else None
            print(json.dumps({
                "event": "progress",
                "pages": pages,
                "page_oldest": min_ts,
                "page_newest": max_ts,
                "kept_in_page": kept,
                "stored_rows": len(rows_by_ts),
                "stored_oldest": None if oldest is None else datetime.fromtimestamp(oldest / 1000, tz=UTC).isoformat(),
                "stored_newest": None if newest is None else datetime.fromtimestamp(newest / 1000, tz=UTC).isoformat(),
            }, ensure_ascii=False))
        if start_ms is not None and min_ts < start_ms:
            break
        after = min_ts
        time.sleep(sleep_seconds)
    return rows_by_ts, pages


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch OKX historical candles into normalized JSONL.")
    parser.add_argument("--inst-id", default=DEFAULT_INST_ID)
    parser.add_argument("--bar", default=DEFAULT_BAR)
    parser.add_argument("--pages", type=int, default=None, help="Optional page cap. Omit for unbounded until start is reached.")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--sleep-seconds", type=float, default=DEFAULT_SLEEP_SECONDS)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--include-unconfirmed", action="store_true")
    parser.add_argument("--start", type=str, default=None, help="Inclusive start time (ISO8601 or ms).")
    parser.add_argument("--end", type=str, default=None, help="Inclusive end time (ISO8601 or ms). Defaults to latest available.")
    parser.add_argument("--resume", action="store_true", help="Load and extend an existing output file.")
    parser.add_argument("--progress-every", type=int, default=100)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    output = args.output or default_output_path(inst_id=args.inst_id, bar=args.bar)
    start_ms = None if args.start is None else parse_time_to_ms(args.start)
    end_ms = None if args.end is None else parse_time_to_ms(args.end)
    rows_by_ts = load_existing_rows(output) if args.resume else {}
    rows_by_ts, pages = fetch_history_range(
        inst_id=args.inst_id,
        bar=args.bar,
        limit=args.limit,
        sleep_seconds=args.sleep_seconds,
        start_ms=start_ms,
        end_ms=end_ms,
        max_pages=args.pages,
        rows_by_ts=rows_by_ts,
        progress_every=max(1, args.progress_every),
    )
    write_jsonl(rows_by_ts, output, only_confirmed=not args.include_unconfirmed)
    ordered = [rows_by_ts[k] for k in sorted(rows_by_ts.keys())]
    if ordered:
        print(json.dumps({
            "output": str(output),
            "row_count": len(ordered),
            "first": ordered[0]["timestamp"],
            "last": ordered[-1]["timestamp"],
            "instId": args.inst_id,
            "bar": args.bar,
            "pages": pages,
            "start": args.start,
            "end": args.end,
        }, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({
            "output": str(output),
            "row_count": 0,
            "instId": args.inst_id,
            "bar": args.bar,
            "pages": pages,
            "start": args.start,
            "end": args.end,
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
