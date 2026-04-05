from __future__ import annotations

import pandas as pd

from trading_model.contracts.types import AttachStatus


MERGE_COLUMNS = [
    "symbol",
    "ts",
    "timestamp",
    "month",
    "state_id",
    "state_confidence",
]


def _prepare_strategy_returns(variant_returns: pd.DataFrame) -> pd.DataFrame:
    frame = variant_returns.copy()
    frame["equity"] = pd.NA
    frame["return_since_prev"] = frame.get("bar_return")
    frame["trade_pnl"] = pd.NA
    frame["position"] = pd.NA
    frame["signal_state"] = pd.NA
    return frame


def attach_strategy_to_states(state_table: pd.DataFrame, variant_returns: pd.DataFrame, oracle_returns: pd.DataFrame) -> pd.DataFrame:
    states = state_table.sort_values(["symbol", "ts"]).copy()
    variants = _prepare_strategy_returns(variant_returns).sort_values(["symbol", "family_id", "variant_id", "ts"]).copy()
    oracle = oracle_returns.sort_values(["symbol", "ts"]).copy()

    attached_frames: list[pd.DataFrame] = []
    for (symbol, family_id, variant_id), group in variants.groupby(["symbol", "family_id", "variant_id"], sort=True):
        left = states[states["symbol"] == symbol].copy()
        right = group.copy()
        merged = pd.merge_asof(
            left.sort_values("ts"),
            right.sort_values("ts"),
            on="ts",
            by="symbol",
            direction="backward",
            tolerance=60_000,
            suffixes=("", "_strategy"),
        )
        merged["family_id"] = family_id
        merged["variant_id"] = variant_id
        merged["attach_status"] = merged["bar_return"].notna().map(
            lambda ok: AttachStatus.EXACT.value if ok else AttachStatus.MISSING.value
        )
        attached_frames.append(merged)

    if not attached_frames:
        raise ValueError("No strategy attachments were produced")

    evaluation = pd.concat(attached_frames, ignore_index=True)
    evaluation = pd.merge_asof(
        evaluation.sort_values(["symbol", "ts"]),
        oracle.sort_values(["symbol", "ts"]),
        on="ts",
        by="symbol",
        direction="backward",
        tolerance=60_000,
        suffixes=("", "_oracle"),
    )

    for horizon in [1, 3, 12, 24]:
        strategy_field = f"forward_return_{horizon}bar"
        oracle_field = f"oracle_forward_return_{horizon}bar"
        evaluation[oracle_field] = evaluation.get("bar_return") if horizon == 1 else evaluation.get(oracle_field)
        if oracle_field not in evaluation.columns:
            evaluation[oracle_field] = pd.NA
        evaluation[f"oracle_gap_{horizon}bar"] = evaluation[oracle_field] - evaluation[strategy_field]

    evaluation["research_object_type"] = "stocks"
    evaluation["family_oracle_selected_variant_id"] = pd.NA
    evaluation["source_manifest_id"] = pd.NA
    evaluation["data_partition_month"] = evaluation["month"]
    return evaluation
