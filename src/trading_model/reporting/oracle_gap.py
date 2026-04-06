from __future__ import annotations

import pandas as pd

from trading_model.utils.time import month_label_utc


def build_oracle_gap_report(state_evaluation_table: pd.DataFrame, mapping: pd.DataFrame) -> dict:
    frame = state_evaluation_table.copy()
    metric = "forward_return_12bar"
    oracle_metric = "oracle_forward_return_12bar"
    realized_1bar = "forward_return_1bar"
    oracle_1bar = "oracle_forward_return_1bar"

    overall_realized = float(frame[metric].mean())
    overall_oracle = float(frame[oracle_metric].mean()) if frame[oracle_metric].notna().any() else None
    overall_gap_abs = None if overall_oracle is None else float(overall_oracle - overall_realized)
    overall_realized_1bar = float(frame[realized_1bar].mean()) if frame[realized_1bar].notna().any() else None
    overall_oracle_1bar = float(frame[oracle_1bar].mean()) if frame[oracle_1bar].notna().any() else None
    overall_gap_abs_1bar = None if overall_oracle_1bar is None or overall_realized_1bar is None else float(overall_oracle_1bar - overall_realized_1bar)

    by_month = (
        frame.assign(month=month_label_utc(frame["timestamp"]))
        .groupby("month", as_index=False)
        .agg(
            realized_metric_state_routed=(metric, "mean"),
            oracle_metric=(oracle_metric, "mean"),
            realized_metric_state_routed_1bar=(realized_1bar, "mean"),
            oracle_metric_1bar=(oracle_1bar, "mean"),
            realized_metric_trivial_baseline=("trivial_baseline_forward_return_12bar", "mean"),
            realized_metric_trivial_baseline_1bar=("trivial_baseline_forward_return_1bar", "mean"),
        )
    )
    by_month["gap_abs_state_routed"] = by_month["oracle_metric"] - by_month["realized_metric_state_routed"]
    by_month["gap_abs_state_routed_1bar"] = by_month["oracle_metric_1bar"] - by_month["realized_metric_state_routed_1bar"]
    by_month["gap_abs_trivial_baseline"] = by_month["oracle_metric"] - by_month["realized_metric_trivial_baseline"]
    by_month["gap_abs_trivial_baseline_1bar"] = by_month["oracle_metric_1bar"] - by_month["realized_metric_trivial_baseline_1bar"]
    by_month["symbol"] = frame["symbol"].iloc[0] if not frame.empty else None

    by_state = (
        frame.groupby("state_id", as_index=False)
        .agg(
            state_support_n=("ts", "size"),
            oracle_metric_mean=(oracle_metric, "mean"),
            realized_metric_mean=(metric, "mean"),
            trivial_baseline_metric_mean=("trivial_baseline_forward_return_12bar", "mean"),
            oracle_metric_mean_1bar=(oracle_1bar, "mean"),
            realized_metric_mean_1bar=(realized_1bar, "mean"),
            trivial_baseline_metric_mean_1bar=("trivial_baseline_forward_return_1bar", "mean"),
        )
    )
    by_state["gap_abs"] = by_state["oracle_metric_mean"] - by_state["realized_metric_mean"]
    by_state["gap_abs_1bar"] = by_state["oracle_metric_mean_1bar"] - by_state["realized_metric_mean_1bar"]
    by_state["gap_abs_trivial_baseline"] = by_state["oracle_metric_mean"] - by_state["trivial_baseline_metric_mean"]
    by_state["gap_abs_trivial_baseline_1bar"] = by_state["oracle_metric_mean_1bar"] - by_state["trivial_baseline_metric_mean_1bar"]
    mapping_join_cols = [col for col in ["state_id", "winner_id", "execution_confidence", "execution_confidence_bucket"] if col in mapping.columns]
    by_state = by_state.merge(mapping[mapping_join_cols], on="state_id", how="left")
    by_state = by_state.rename(columns={"winner_id": "preferred_target"})
    by_state["symbol"] = frame["symbol"].iloc[0] if not frame.empty else None
    if "preferred_target" in by_state.columns:
        by_state["preferred_target"] = by_state["preferred_target"].fillna("no_target")
    by_state["winner_type"] = by_state["preferred_target"].apply(lambda value: "variant" if value not in {"no_strong_preference", "no_target"} else "fallback")

    attach_audit = {
        "strategy_attach_status": frame["attach_status"].value_counts(dropna=False).to_dict(),
        "oracle_attach_status": frame["oracle_attach_status"].value_counts(dropna=False).to_dict(),
        "strategy_attach_match_direction": frame["attach_match_direction"].value_counts(dropna=False).to_dict() if "attach_match_direction" in frame.columns else {},
        "oracle_attach_match_direction": frame["oracle_attach_match_direction"].value_counts(dropna=False).to_dict() if "oracle_attach_match_direction" in frame.columns else {},
        "strategy_attach_delta_ms": {
            "min": float(frame["attach_delta_ms"].dropna().min()) if frame["attach_delta_ms"].notna().any() else None,
            "max": float(frame["attach_delta_ms"].dropna().max()) if frame["attach_delta_ms"].notna().any() else None,
        },
        "strategy_attach_abs_delta_ms": {
            "min": float(frame["attach_abs_delta_ms"].dropna().min()) if "attach_abs_delta_ms" in frame.columns and frame["attach_abs_delta_ms"].notna().any() else None,
            "max": float(frame["attach_abs_delta_ms"].dropna().max()) if "attach_abs_delta_ms" in frame.columns and frame["attach_abs_delta_ms"].notna().any() else None,
        },
        "oracle_attach_delta_ms": {
            "min": float(frame["oracle_attach_delta_ms"].dropna().min()) if frame["oracle_attach_delta_ms"].notna().any() else None,
            "max": float(frame["oracle_attach_delta_ms"].dropna().max()) if frame["oracle_attach_delta_ms"].notna().any() else None,
        },
        "oracle_attach_abs_delta_ms": {
            "min": float(frame["oracle_attach_abs_delta_ms"].dropna().min()) if "oracle_attach_abs_delta_ms" in frame.columns and frame["oracle_attach_abs_delta_ms"].notna().any() else None,
            "max": float(frame["oracle_attach_abs_delta_ms"].dropna().max()) if "oracle_attach_abs_delta_ms" in frame.columns and frame["oracle_attach_abs_delta_ms"].notna().any() else None,
        },
        "attach_tolerance_ms": int(frame["attach_tolerance_ms"].dropna().iloc[0]) if "attach_tolerance_ms" in frame.columns and frame["attach_tolerance_ms"].notna().any() else None,
        "oracle_attach_tolerance_ms": int(frame["oracle_attach_tolerance_ms"].dropna().iloc[0]) if "oracle_attach_tolerance_ms" in frame.columns and frame["oracle_attach_tolerance_ms"].notna().any() else None,
    }

    trivial_baseline_overall = {
        "overall_realized_metric": float(frame["trivial_baseline_forward_return_12bar"].mean()) if frame["trivial_baseline_forward_return_12bar"].notna().any() else None,
        "overall_realized_metric_1bar": float(frame["trivial_baseline_forward_return_1bar"].mean()) if frame["trivial_baseline_forward_return_1bar"].notna().any() else None,
    }

    return {
        "overall": {
            "overall_realized_metric": overall_realized,
            "overall_oracle_metric": overall_oracle,
            "overall_gap_abs": overall_gap_abs,
            "overall_realized_metric_1bar": overall_realized_1bar,
            "overall_oracle_metric_1bar": overall_oracle_1bar,
            "overall_gap_abs_1bar": overall_gap_abs_1bar,
            "trivial_baseline": trivial_baseline_overall,
        },
        "attach_audit": attach_audit,
        "by_month": by_month.to_dict(orient="records"),
        "by_state": by_state.to_dict(orient="records"),
    }
