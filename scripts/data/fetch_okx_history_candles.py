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


def fetch_history(*, inst_id: str, bar: str, pages: int, limit: int, sleep_seconds: float) -> list[dict[str, Any]]:
    all_rows: list[list[str]] = []
    after: int | None = None
    for page in range(1, pages + 1):
        rows = fetch_page(inst_id=inst_id, bar=bar, limit=limit, after=after)
        if not rows:
            break
        all_rows.extend(rows)
        after = min(int(r[0]) for r in rows)
        if page < pages:
            time.sleep(sleep_seconds)
    dedup: dict[int, dict[str, Any]] = {}
    for row in all_rows:
        normalized = normalize_row(row, inst_id=inst_id, bar=bar)
        dedup[int(normalized["ts"])] = normalized
    return [dedup[k] for k in sorted(dedup.keys())]


def default_output_path(*, inst_id: str, bar: str) -> Path:
    safe_inst = inst_id.replace("/", "-")
    return Path("data/raw/okx/candles") / safe_inst / bar / f"{safe_inst}_{bar}.jsonl"


def write_jsonl(rows: list[dict[str, Any]], path: Path, *, only_confirmed: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            if only_confirmed and int(row.get("confirm", 0)) != 1:
                continue
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch OKX historical candles into normalized JSONL.")
    parser.add_argument("--inst-id", default=DEFAULT_INST_ID)
    parser.add_argument("--bar", default=DEFAULT_BAR)
    parser.add_argument("--pages", type=int, default=10)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--sleep-seconds", type=float, default=DEFAULT_SLEEP_SECONDS)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--include-unconfirmed", action="store_true")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    output = args.output or default_output_path(inst_id=args.inst_id, bar=args.bar)
    rows = fetch_history(
        inst_id=args.inst_id,
        bar=args.bar,
        pages=args.pages,
        limit=args.limit,
        sleep_seconds=args.sleep_seconds,
    )
    write_jsonl(rows, output, only_confirmed=not args.include_unconfirmed)
    if rows:
        print(json.dumps({
            "output": str(output),
            "row_count": len(rows),
            "first": rows[0]["timestamp"],
            "last": rows[-1]["timestamp"],
            "instId": args.inst_id,
            "bar": args.bar,
        }, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({
            "output": str(output),
            "row_count": 0,
            "instId": args.inst_id,
            "bar": args.bar,
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
