from __future__ import annotations

import numpy as np
import pandas as pd

from trading_model.contracts.types import AttachStatus
from trading_model.evaluation.horizons import add_group_forward_returns


def _compute_attach_status(ts: pd.Series, matched_ts: pd.Series, tolerance_ms: int) -> pd.Series:
    delta = ts - matched_ts
    status = pd.Series(np.full(len(ts), AttachStatus.MISSING.value, dtype=object), index=ts.index)
    has_match = matched_ts.notna()
    status.loc[has_match & (delta == 0)] = AttachStatus.EXACT.value
    status.loc[has_match & (delta > 0) & (delta <= tolerance_ms)] = AttachStatus.PREVIOUS_BAR.value
    status.loc[has_match & (delta > tolerance_ms)] = AttachStatus.OUT_OF_TOLERANCE.value
    status.loc[has_match & (delta < 0)] = AttachStatus.OUT_OF_TOLERANCE.value
    return status


def _prepare_strategy_returns(variant_returns: pd.DataFrame) -> pd.DataFrame:
    frame = variant_returns.copy()
    frame["return_since_prev"] = frame.get("bar_return")
    frame["trade_pnl"] = pd.NA
    frame["signal_state"] = pd.NA
    frame = add_group_forward_returns(
        frame,
        group_cols=["symbol", "family_id", "variant_id"],
        value_col="equity",
        prefix="strategy",
    )
    return frame


def _prepare_oracle_returns(oracle_returns: pd.DataFrame) -> pd.DataFrame:
    frame = oracle_returns.copy()
    frame = add_group_forward_returns(
        frame,
        group_cols=["symbol"],
        value_col="oracle_equity_source",
        prefix="oracle",
    )
    return frame


def attach_strategy_to_states(
    state_table: pd.DataFrame,
    variant_returns: pd.DataFrame,
    oracle_returns: pd.DataFrame,
    *,
    tolerance_ms: int = 60_000,
    research_object_type: str = "stocks",
) -> pd.DataFrame:
    states = state_table.sort_values(["symbol", "ts"]).copy()
    variants = _prepare_strategy_returns(variant_returns).sort_values(["symbol", "family_id", "variant_id", "ts"]).copy()
    oracle_raw = oracle_returns.copy()
    oracle_raw["oracle_equity_source"] = oracle_raw["equity"]
    oracle = _prepare_oracle_returns(oracle_raw).sort_values(["symbol", "ts"]).copy()

    attached_frames: list[pd.DataFrame] = []
    for (symbol, family_id, variant_id), group in variants.groupby(["symbol", "family_id", "variant_id"], sort=True):
        left = states[states["symbol"] == symbol].copy()
        right = group.copy().rename(columns={"ts": "strategy_ts", "timestamp": "strategy_timestamp"})
        merged = pd.merge_asof(
            left.sort_values("ts"),
            right.sort_values("strategy_ts"),
            left_on="ts",
            right_on="strategy_ts",
            by="symbol",
            direction="backward",
            tolerance=tolerance_ms,
            suffixes=("", "_strategy"),
        )
        merged["family_id"] = family_id
        merged["variant_id"] = variant_id
        merged["attach_status"] = _compute_attach_status(merged["ts"], merged["strategy_ts"], tolerance_ms)
        merged["attach_delta_ms"] = merged["ts"] - merged["strategy_ts"]
        merged["attach_abs_delta_ms"] = (merged["ts"] - merged["strategy_ts"]).abs()
        merged["attach_tolerance_ms"] = tolerance_ms
        merged["attach_match_direction"] = np.where(
            merged["strategy_ts"].isna(),
            "missing",
            np.where(merged["attach_delta_ms"] == 0, "exact", np.where(merged["attach_delta_ms"] > 0, "backward", "forward_or_invalid")),
        )
        merged["attach_source"] = np.where(merged["strategy_ts"].notna(), "strategy_equity_returns", "missing")
        attached_frames.append(merged)

    if not attached_frames:
        raise ValueError("No strategy attachments were produced")

    evaluation = pd.concat(attached_frames, ignore_index=True)
    oracle_ready = oracle.rename(
        columns={
            "ts": "oracle_ts",
            "timestamp": "oracle_timestamp",
            "equity": "oracle_equity",
            "bar_return": "oracle_bar_return",
            "oracle_forward_return_1bar": "oracle_forward_return_1bar",
            "oracle_forward_return_3bar": "oracle_forward_return_3bar",
            "oracle_forward_return_12bar": "oracle_forward_return_12bar",
            "oracle_forward_return_24bar": "oracle_forward_return_24bar",
        }
    )
    evaluation = pd.merge_asof(
        evaluation.sort_values(["symbol", "ts"]),
        oracle_ready.sort_values(["symbol", "oracle_ts"]),
        left_on="ts",
        right_on="oracle_ts",
        by="symbol",
        direction="backward",
        tolerance=tolerance_ms,
        suffixes=("", "_oracle"),
    )
    evaluation["oracle_attach_status"] = _compute_attach_status(evaluation["ts"], evaluation["oracle_ts"], tolerance_ms)
    evaluation["oracle_attach_delta_ms"] = evaluation["ts"] - evaluation["oracle_ts"]
    evaluation["oracle_attach_abs_delta_ms"] = (evaluation["ts"] - evaluation["oracle_ts"]).abs()
    evaluation["oracle_attach_tolerance_ms"] = tolerance_ms
    evaluation["oracle_attach_match_direction"] = np.where(
        evaluation["oracle_ts"].isna(),
        "missing",
        np.where(evaluation["oracle_attach_delta_ms"] == 0, "exact", np.where(evaluation["oracle_attach_delta_ms"] > 0, "backward", "forward_or_invalid")),
    )
    evaluation["oracle_attach_source"] = np.where(evaluation["oracle_ts"].notna(), "global_oracle_equity_returns", "missing")

    evaluation["forward_return_1bar"] = evaluation["bar_return"]
    for horizon in [3, 12, 24]:
        evaluation[f"forward_return_{horizon}bar"] = evaluation[f"strategy_forward_return_{horizon}bar"]
    evaluation["oracle_forward_return_1bar"] = evaluation["oracle_bar_return"]

    for horizon in [1, 3, 12, 24]:
        strategy_field = f"forward_return_{horizon}bar"
        oracle_field = f"oracle_forward_return_{horizon}bar"
        evaluation[f"oracle_gap_{horizon}bar"] = evaluation[oracle_field] - evaluation[strategy_field]

    evaluation["research_object_type"] = research_object_type
    evaluation["family_oracle_selected_variant_id"] = pd.NA
    evaluation["source_manifest_id"] = pd.NA
    evaluation["data_partition_month"] = evaluation["month"]
    return evaluation
