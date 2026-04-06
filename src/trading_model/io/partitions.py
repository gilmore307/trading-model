from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

MAX_PARTITION_FILE_BYTES = 50 * 1024 * 1024


def _partition_path(root: Path, partition_names: list[str], keys: tuple[Any, ...], filename: str) -> Path:
    parts = [f"{col}={value}" for col, value in zip(partition_names, keys)]
    return root.joinpath(*parts) / filename


def _write_csv_with_size_cap(frame: pd.DataFrame, path: Path, *, max_file_bytes: int = MAX_PARTITION_FILE_BYTES) -> list[Path]:
    path.parent.mkdir(parents=True, exist_ok=True)
    csv_bytes = frame.to_csv(index=False).encode("utf-8")
    if len(csv_bytes) <= max_file_bytes:
        path.write_bytes(csv_bytes)
        return [path]

    bytes_per_row = max(1, math.ceil(len(csv_bytes) / max(len(frame), 1)))
    chunk_rows = max(1, (max_file_bytes // bytes_per_row) - 1)
    written: list[Path] = []
    stem = path.stem
    suffix = path.suffix
    for chunk_index, start in enumerate(range(0, len(frame), chunk_rows), start=1):
        chunk = frame.iloc[start:start + chunk_rows]
        chunk_path = path.with_name(f"{stem}.part-{chunk_index:04d}{suffix}")
        chunk_bytes = chunk.to_csv(index=False).encode("utf-8")
        if len(chunk_bytes) > max_file_bytes and len(chunk) > 1:
            half = max(1, len(chunk) // 2)
            for sub_index, sub_start in enumerate(range(0, len(chunk), half), start=1):
                sub = chunk.iloc[sub_start:sub_start + half]
                sub_path = path.with_name(f"{stem}.part-{chunk_index:04d}-{sub_index:02d}{suffix}")
                sub_path.write_bytes(sub.to_csv(index=False).encode("utf-8"))
                written.append(sub_path)
            continue
        chunk_path.write_bytes(chunk_bytes)
        written.append(chunk_path)
    return written


def _write_json_bytes_with_size_cap(payload_bytes: bytes, path: Path, *, max_file_bytes: int = MAX_PARTITION_FILE_BYTES) -> list[Path]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if len(payload_bytes) <= max_file_bytes:
        path.write_bytes(payload_bytes)
        return [path]
    raise ValueError(f"Single JSON object exceeds max partition file size: {path}")


def write_partitioned_csv(
    frame: pd.DataFrame,
    root: Path,
    *,
    partition_cols: list[str],
    filename: str,
    max_file_bytes: int = MAX_PARTITION_FILE_BYTES,
) -> list[Path]:
    root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    grouped = frame.groupby(partition_cols, dropna=False, sort=True)
    for keys, group in grouped:
        if not isinstance(keys, tuple):
            keys = (keys,)
        path = _partition_path(root, partition_cols, keys, filename)
        written.extend(_write_csv_with_size_cap(group, path, max_file_bytes=max_file_bytes))
    return written


def write_partitioned_json_records(
    records: list[dict[str, Any]],
    root: Path,
    *,
    partition_cols: list[str],
    filename: str,
    max_file_bytes: int = MAX_PARTITION_FILE_BYTES,
) -> list[Path]:
    root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for record in records:
        keys = tuple(record.get(col) for col in partition_cols)
        grouped.setdefault(keys, []).append(record)

    for keys, group_records in sorted(grouped.items(), key=lambda item: item[0]):
        path = _partition_path(root, partition_cols, keys, filename)
        payload_bytes = json.dumps(group_records, ensure_ascii=False, indent=2).encode("utf-8")
        if len(payload_bytes) <= max_file_bytes:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload_bytes)
            written.append(path)
            continue

        bytes_per_record = max(1, math.ceil(len(payload_bytes) / max(len(group_records), 1)))
        chunk_size = max(1, (max_file_bytes // bytes_per_record) - 1)
        stem = path.stem
        suffix = path.suffix
        for chunk_index, start in enumerate(range(0, len(group_records), chunk_size), start=1):
            chunk_records = group_records[start:start + chunk_size]
            chunk_path = path.with_name(f"{stem}.part-{chunk_index:04d}{suffix}")
            chunk_bytes = json.dumps(chunk_records, ensure_ascii=False, indent=2).encode("utf-8")
            if len(chunk_bytes) > max_file_bytes:
                raise ValueError(f"JSON record chunk exceeds max partition file size: {chunk_path}")
            chunk_path.parent.mkdir(parents=True, exist_ok=True)
            chunk_path.write_bytes(chunk_bytes)
            written.append(chunk_path)
    return written


def write_partitioned_json_object(
    payload: dict[str, Any],
    root: Path,
    *,
    partition_values: dict[str, Any],
    filename: str,
    max_file_bytes: int = MAX_PARTITION_FILE_BYTES,
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    keys = tuple(partition_values.values())
    path = _partition_path(root, list(partition_values.keys()), keys, filename)
    payload_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    _write_json_bytes_with_size_cap(payload_bytes, path, max_file_bytes=max_file_bytes)
    return path
