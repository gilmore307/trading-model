from __future__ import annotations

import pandas as pd

from trading_model.utils.time import month_label_utc

WINNER_METRIC = "forward_return_12bar"


def build_trivial_baseline_policy(state_evaluation_table: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = state_evaluation_table.copy()
    frame["month_label"] = month_label_utc(frame["timestamp"])

    bucket_variant_scores = (
        frame.groupby(["trivial_baseline_id", "variant_id"], as_index=False)
        .agg(score=(WINNER_METRIC, "mean"), support_n=("ts", "size"))
        .sort_values(["trivial_baseline_id", "score", "support_n", "variant_id"], ascending=[True, False, False, True])
    )
    bucket_winners = bucket_variant_scores.groupby("trivial_baseline_id", as_index=False).first()
    bucket_winners = bucket_winners.rename(columns={"variant_id": "trivial_baseline_winner_id", "score": "trivial_baseline_winner_score"})

    realized = frame.merge(
        bucket_winners[["trivial_baseline_id", "trivial_baseline_winner_id"]],
        on="trivial_baseline_id",
        how="left",
    )
    realized = realized[realized["variant_id"] == realized["trivial_baseline_winner_id"]].copy()
    realized = realized.rename(
        columns={
            "forward_return_1bar": "trivial_baseline_forward_return_1bar",
            "forward_return_3bar": "trivial_baseline_forward_return_3bar",
            "forward_return_12bar": "trivial_baseline_forward_return_12bar",
            "forward_return_24bar": "trivial_baseline_forward_return_24bar",
        }
    )
    realized = realized[
        [
            "symbol",
            "ts",
            "trivial_baseline_id",
            "trivial_baseline_winner_id",
            "trivial_baseline_forward_return_1bar",
            "trivial_baseline_forward_return_3bar",
            "trivial_baseline_forward_return_12bar",
            "trivial_baseline_forward_return_24bar",
        ]
    ].drop_duplicates(subset=["symbol", "ts"], keep="first")

    return bucket_winners, realized
