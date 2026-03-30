from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ccxt  # type: ignore


DEFAULT_START = "2022-01-01T00:00:00Z"
TIMEFRAME_MS = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "8h": 28_800_000,
}


def parse_time_to_ms(value: str) -> int:
    value = value.strip()
    if value.isdigit():
        return int(value)
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return int(dt.timestamp() * 1000)


def ts_to_iso(ts: int) -> str:
    return datetime.fromtimestamp(ts / 1000, tz=UTC).isoformat()


def jsonl_path(kind: str, *, inst_id: str, timeframe: str | None = None) -> Path:
    safe_inst = inst_id.replace("/", "-")
    if timeframe:
        return Path("data/raw/okx/derivatives") / safe_inst / kind / timeframe / f"{safe_inst}_{kind}_{timeframe}.jsonl"
    return Path("data/raw/okx/derivatives") / safe_inst / kind / f"{safe_inst}_{kind}.jsonl"


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
            ts = row.get("ts")
            if ts is None:
                continue
            existing[int(ts)] = row
    return existing


def write_jsonl(rows_by_ts: dict[int, dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for ts in sorted(rows_by_ts.keys()):
            handle.write(json.dumps(rows_by_ts[ts], ensure_ascii=False) + "\n")


def exchange_symbol(inst_id: str) -> str:
    if inst_id.endswith("-USDT-SWAP"):
        return inst_id.replace("-USDT-SWAP", "/USDT:USDT")
    return inst_id.replace("-", "/")


def fetch_with_retry(fn: Callable[[], Any], *, label: str, max_retries: int = 10) -> Any:
    backoff = 2.0
    for attempt in range(1, max_retries + 1):
        try:
            return fn()
        except Exception as exc:
            status = getattr(exc, "http_status_code", None)
            message = str(exc).lower()
            is_rate = status == 429 or "429" in message or "too many requests" in message or "rate limit" in message
            if attempt == max_retries or not is_rate:
                raise
            sleep_for = backoff + random.uniform(0, 1.0)
            print(json.dumps({
                "event": "retry",
                "label": label,
                "attempt": attempt,
                "sleep_seconds": round(sleep_for, 2),
                "reason": str(exc)[:200],
            }, ensure_ascii=False))
            time.sleep(sleep_for)
            backoff = min(backoff * 1.8, 60.0)
    raise RuntimeError("unreachable")


def normalize_funding_row(row: dict[str, Any], *, inst_id: str) -> tuple[int, dict[str, Any]] | None:
    ts = row.get("timestamp") or row.get("fundingTimestamp") or row.get("ts")
    if ts is None:
        return None
    ts = int(ts)
    out = {
        "exchange": "okx",
        "dataset": "funding_rate_history",
        "instId": inst_id,
        "ts": ts,
        "timestamp": ts_to_iso(ts),
        "fundingRate": None if row.get("fundingRate") is None else float(row.get("fundingRate")),
        "nextFundingRate": None if row.get("nextFundingRate") is None else float(row.get("nextFundingRate")),
        "nextFundingTimestamp": row.get("nextFundingTimestamp"),
        "symbol": row.get("symbol"),
        "info": row.get("info"),
    }
    return ts, out


def normalize_open_interest_row(row: dict[str, Any], *, inst_id: str, timeframe: str) -> tuple[int, dict[str, Any]] | None:
    ts = row.get("timestamp") or row.get("ts") or row.get("time")
    if ts is None:
        info = row.get("info")
        if isinstance(info, (list, tuple)) and info:
            ts = info[0]
    if ts is None:
        return None
    ts = int(ts)
    oi = row.get("openInterestAmount")
    if oi is None:
        oi = row.get("openInterestValue")
    if oi is None:
        oi = row.get("openInterest")
    if oi is None:
        info = row.get("info")
        if isinstance(info, (list, tuple)) and len(info) >= 2:
            oi = info[1]
    out = {
        "exchange": "okx",
        "dataset": "open_interest_history",
        "instId": inst_id,
        "timeframe": timeframe,
        "ts": ts,
        "timestamp": ts_to_iso(ts),
        "openInterest": None if oi is None else float(oi),
        "quoteVolume": None if row.get("quoteVolume") is None else float(row.get("quoteVolume")),
        "baseVolume": None if row.get("baseVolume") is None else float(row.get("baseVolume")),
        "symbol": row.get("symbol"),
        "info": row.get("info"),
    }
    return ts, out


def normalize_basis_rows(mark_rows: list[list[Any]], index_rows: list[list[Any]], *, inst_id: str, timeframe: str) -> dict[int, dict[str, Any]]:
    index_map = {int(r[0]): r for r in index_rows if len(r) >= 5}
    rows_by_ts: dict[int, dict[str, Any]] = {}
    for row in mark_rows:
        if len(row) < 5:
            continue
        ts = int(row[0])
        idx = index_map.get(ts)
        if idx is None or len(idx) < 5:
            continue
        mark_close = float(row[4])
        index_close = float(idx[4])
        basis_pct = None if index_close == 0 else (mark_close - index_close) / index_close
        rows_by_ts[ts] = {
            "exchange": "okx",
            "dataset": "basis_history",
            "instId": inst_id,
            "timeframe": timeframe,
            "ts": ts,
            "timestamp": ts_to_iso(ts),
            "markOpen": float(row[1]),
            "markHigh": float(row[2]),
            "markLow": float(row[3]),
            "markClose": mark_close,
            "indexOpen": float(idx[1]),
            "indexHigh": float(idx[2]),
            "indexLow": float(idx[3]),
            "indexClose": index_close,
            "basisPct": basis_pct,
        }
    return rows_by_ts


def next_since(existing_ts: dict[int, dict[str, Any]], *, start_ms: int, bucket_ms: int, limit: int) -> int:
    if not existing_ts:
        return start_ms
    oldest = min(existing_ts.keys())
    coverage_threshold = start_ms + bucket_ms * limit
    if oldest > coverage_threshold:
        return start_ms
    return max(existing_ts.keys()) + 1


def fetch_funding_history(exchange: Any, *, symbol: str, inst_id: str, start_ms: int, end_ms: int | None, limit: int, sleep_seconds: float, rows_by_ts: dict[int, dict[str, Any]], progress_every: int, checkpoint_every: int, output_path: Path) -> tuple[dict[int, dict[str, Any]], int]:
    rounds = 0
    step_ms = 8 * 60 * 60 * 1000
    since = next_since(rows_by_ts, start_ms=start_ms, bucket_ms=step_ms, limit=limit)
    while since <= (end_ms or 2**63 - 1):
        rows = fetch_with_retry(lambda: exchange.fetch_funding_rate_history(symbol, since=since, limit=limit), label="funding")
        if not rows:
            break
        rounds += 1
        before = len(rows_by_ts)
        max_seen = None
        for row in rows:
            normalized = normalize_funding_row(row, inst_id=inst_id)
            if normalized is None:
                continue
            ts, payload = normalized
            if ts < start_ms:
                continue
            if end_ms is not None and ts > end_ms:
                continue
            rows_by_ts[ts] = payload
            max_seen = ts if max_seen is None else max(max_seen, ts)
        if rounds % checkpoint_every == 0:
            write_jsonl(rows_by_ts, output_path)
        if rounds % progress_every == 0:
            newest = max(rows_by_ts.keys()) if rows_by_ts else None
            oldest = min(rows_by_ts.keys()) if rows_by_ts else None
            print(json.dumps({"event": "funding_progress", "rounds": rounds, "stored_rows": len(rows_by_ts), "stored_oldest": ts_to_iso(oldest) if oldest else None, "stored_newest": ts_to_iso(newest) if newest else None}, ensure_ascii=False))
        if max_seen is None or len(rows_by_ts) == before:
            since += step_ms * limit
        else:
            since = max_seen + 1
        if end_ms is not None and since > end_ms:
            break
        time.sleep(sleep_seconds)
    return rows_by_ts, rounds


def fetch_open_interest_history(exchange: Any, *, symbol: str, inst_id: str, timeframe: str, start_ms: int, end_ms: int | None, limit: int, sleep_seconds: float, rows_by_ts: dict[int, dict[str, Any]], progress_every: int, checkpoint_every: int, output_path: Path) -> tuple[dict[int, dict[str, Any]], int]:
    rounds = 0
    step_ms = TIMEFRAME_MS[timeframe]
    since = next_since(rows_by_ts, start_ms=start_ms, bucket_ms=step_ms, limit=limit)
    while since <= (end_ms or 2**63 - 1):
        rows = fetch_with_retry(lambda: exchange.fetch_open_interest_history(symbol, timeframe=timeframe, since=since, limit=limit), label="open_interest")
        if not rows:
            break
        rounds += 1
        before = len(rows_by_ts)
        max_seen = None
        for row in rows:
            normalized = normalize_open_interest_row(row, inst_id=inst_id, timeframe=timeframe)
            if normalized is None:
                continue
            ts, payload = normalized
            if ts < start_ms:
                continue
            if end_ms is not None and ts > end_ms:
                continue
            rows_by_ts[ts] = payload
            max_seen = ts if max_seen is None else max(max_seen, ts)
        if rounds % checkpoint_every == 0:
            write_jsonl(rows_by_ts, output_path)
        if rounds % progress_every == 0:
            newest = max(rows_by_ts.keys()) if rows_by_ts else None
            oldest = min(rows_by_ts.keys()) if rows_by_ts else None
            print(json.dumps({"event": "open_interest_progress", "rounds": rounds, "stored_rows": len(rows_by_ts), "stored_oldest": ts_to_iso(oldest) if oldest else None, "stored_newest": ts_to_iso(newest) if newest else None}, ensure_ascii=False))
        if max_seen is None or len(rows_by_ts) == before:
            since += step_ms * limit
        else:
            since = max_seen + 1
        if end_ms is not None and since > end_ms:
            break
        time.sleep(sleep_seconds)
    return rows_by_ts, rounds


def fetch_basis_history(exchange: Any, *, symbol: str, inst_id: str, timeframe: str, start_ms: int, end_ms: int | None, limit: int, sleep_seconds: float, rows_by_ts: dict[int, dict[str, Any]], progress_every: int, checkpoint_every: int, output_path: Path) -> tuple[dict[int, dict[str, Any]], int]:
    rounds = 0
    step_ms = TIMEFRAME_MS[timeframe]
    since = next_since(rows_by_ts, start_ms=start_ms, bucket_ms=step_ms, limit=limit)
    while since <= (end_ms or 2**63 - 1):
        mark_rows = fetch_with_retry(lambda: exchange.fetch_mark_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit), label="mark_ohlcv")
        index_rows = fetch_with_retry(lambda: exchange.fetch_index_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit), label="index_ohlcv")
        if not mark_rows or not index_rows:
            break
        rounds += 1
        before = len(rows_by_ts)
        batch = normalize_basis_rows(mark_rows, index_rows, inst_id=inst_id, timeframe=timeframe)
        max_seen = None
        for ts, payload in batch.items():
            if ts < start_ms:
                continue
            if end_ms is not None and ts > end_ms:
                continue
            rows_by_ts[ts] = payload
            max_seen = ts if max_seen is None else max(max_seen, ts)
        if rounds % checkpoint_every == 0:
            write_jsonl(rows_by_ts, output_path)
        if rounds % progress_every == 0:
            newest = max(rows_by_ts.keys()) if rows_by_ts else None
            oldest = min(rows_by_ts.keys()) if rows_by_ts else None
            print(json.dumps({"event": "basis_progress", "rounds": rounds, "stored_rows": len(rows_by_ts), "stored_oldest": ts_to_iso(oldest) if oldest else None, "stored_newest": ts_to_iso(newest) if newest else None}, ensure_ascii=False))
        if max_seen is None or len(rows_by_ts) == before:
            since += step_ms * limit
        else:
            since = max_seen + 1
        if end_ms is not None and since > end_ms:
            break
        time.sleep(sleep_seconds)
    return rows_by_ts, rounds


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch OKX derivatives context history into normalized JSONL.")
    parser.add_argument("--inst-id", default="BTC-USDT-SWAP")
    parser.add_argument("--kind", choices=["funding", "open-interest", "basis", "all"], default="all")
    parser.add_argument("--timeframe", default="5m")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--sleep-seconds", type=float, default=0.35)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--progress-every", type=int, default=25)
    parser.add_argument("--checkpoint-every", type=int, default=10)
    parser.add_argument("--start", type=str, default=DEFAULT_START)
    parser.add_argument("--end", type=str, default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    exchange = ccxt.okx({"enableRateLimit": True})
    symbol = exchange_symbol(args.inst_id)
    start_ms = parse_time_to_ms(args.start)
    end_ms = parse_time_to_ms(args.end) if args.end else None

    summary: dict[str, Any] = {"instId": args.inst_id, "timeframe": args.timeframe, "start": args.start, "end": args.end}

    if args.kind in {"funding", "all"}:
        path = jsonl_path("funding", inst_id=args.inst_id)
        rows_by_ts = load_existing_rows(path) if args.resume else {}
        rows_by_ts, rounds = fetch_funding_history(exchange, symbol=symbol, inst_id=args.inst_id, start_ms=start_ms, end_ms=end_ms, limit=args.limit, sleep_seconds=args.sleep_seconds, rows_by_ts=rows_by_ts, progress_every=max(1, args.progress_every), checkpoint_every=max(1, args.checkpoint_every), output_path=path)
        write_jsonl(rows_by_ts, path)
        summary["funding"] = {"output": str(path), "rows": len(rows_by_ts), "rounds": rounds}

    if args.kind in {"open-interest", "all"}:
        path = jsonl_path("open_interest", inst_id=args.inst_id, timeframe=args.timeframe)
        rows_by_ts = load_existing_rows(path) if args.resume else {}
        rows_by_ts, rounds = fetch_open_interest_history(exchange, symbol=symbol, inst_id=args.inst_id, timeframe=args.timeframe, start_ms=start_ms, end_ms=end_ms, limit=args.limit, sleep_seconds=args.sleep_seconds, rows_by_ts=rows_by_ts, progress_every=max(1, args.progress_every), checkpoint_every=max(1, args.checkpoint_every), output_path=path)
        write_jsonl(rows_by_ts, path)
        summary["open_interest"] = {"output": str(path), "rows": len(rows_by_ts), "rounds": rounds}

    if args.kind in {"basis", "all"}:
        path = jsonl_path("basis", inst_id=args.inst_id, timeframe=args.timeframe)
        rows_by_ts = load_existing_rows(path) if args.resume else {}
        rows_by_ts, rounds = fetch_basis_history(exchange, symbol=symbol, inst_id=args.inst_id, timeframe=args.timeframe, start_ms=start_ms, end_ms=end_ms, limit=args.limit, sleep_seconds=args.sleep_seconds, rows_by_ts=rows_by_ts, progress_every=max(1, args.progress_every), checkpoint_every=max(1, args.checkpoint_every), output_path=path)
        write_jsonl(rows_by_ts, path)
        summary["basis"] = {"output": str(path), "rows": len(rows_by_ts), "rounds": rounds}

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
