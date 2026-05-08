from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import scripts.models.model_03_target_state_vector.review_target_state_vector_production_substrate as production_substrate
from models.model_03_target_state_vector import evaluation, generator
from models.model_03_target_state_vector.anonymous_target_candidate_builder import builder

ET = ZoneInfo("America/New_York")


def _feature_row(index: int) -> dict:
    ts = datetime(2026, 1, 2, 9, 30, tzinfo=ET) + timedelta(minutes=index)
    ret = index / 1000
    return {
        "available_time": ts.isoformat(),
        "tradeable_time": ts.isoformat(),
        "target_candidate_id": "tcand_001",
        "market_context_state_ref": "mkt_001",
        "sector_context_state_ref": "sec_001",
        "target_context_state_version": "target_context_state_v1",
        "market_state_features": {"state_window_sync_policy": "market_sector_target_blocks_must_share_identical_observation_windows", "market_return_15min": 0.001},
        "sector_state_features": {"state_window_sync_policy": "market_sector_target_blocks_must_share_identical_observation_windows", "sector_return_15min": 0.002},
        "target_state_features": {
            "state_window_sync_policy": "market_sector_target_blocks_must_share_identical_observation_windows",
            "target_direction_return_shape": {"return_5min": ret, "return_15min": ret * 2, "return_60min": ret * 3, "return_390min": ret * 4},
            "target_trend_quality_state": {"trend_quality_15min": 0.8, "path_stability_15min": 0.9},
            "target_trend_age_state": {"state_persistence_score_15min": 0.7},
            "target_exhaustion_decay_state": {"late_trend_risk_score_15min": 0.1},
            "target_volatility_range_state": {"realized_vol_15min": 0.02},
            "target_liquidity_tradability_state": {"spread_bps": 5, "dollar_volume": 1_000_000},
        },
        "cross_state_features": {"state_window_sync_policy": "market_sector_target_blocks_must_share_identical_observation_windows", "target_vs_market_residual_direction": ret, "target_vs_sector_residual_direction": ret / 2, "sector_confirmation_state": "sector_confirmed"},
        "feature_quality_diagnostics": {"has_target_close": True},
    }


class TargetStateVectorModelTests(unittest.TestCase):
    def test_generator_emits_direction_neutral_scores_without_downstream_actions(self) -> None:
        rows = generator.generate_rows([_feature_row(15)])
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["model_id"], "target_state_vector_model")
        self.assertIn("3_target_direction_score_15min", row)
        self.assertIn("3_target_direction_strength_score_15min", row)
        self.assertIn("3_target_state_persistence_score_15min", row)
        self.assertIn("3_target_exhaustion_risk_score_15min", row)
        self.assertIn("3_tradability_score_15min", row)
        self.assertIn("target_context_state", row)
        self.assertNotIn("alpha_confidence", row)
        self.assertNotIn("position_size", row)
        self.assertNotIn("final_action", row)
        self.assertEqual(row["state_quality_diagnostics"]["identity_leakage_check"], "passed")
        self.assertEqual(row["state_quality_diagnostics"]["field_semantics_policy"]["target_state_embedding"], "research_only_not_primary_model_feature")

    def test_evaluation_builds_baseline_ladder_and_defers_small_fixture_thresholds(self) -> None:
        feature_rows = [_feature_row(index) for index in range(8)]
        model_rows = generator.generate_rows(feature_rows)
        artifacts = evaluation.build_evaluation_artifacts(feature_rows=feature_rows, model_rows=model_rows)
        metric_names = {row["metric_name"] for row in artifacts.eval_metrics}
        self.assertIn("abs_corr:market_only_baseline", metric_names)
        self.assertIn("abs_corr:market_sector_baseline", metric_names)
        self.assertIn("abs_corr:market_sector_target_context", metric_names)
        self.assertIn("threshold:minimum_feature_rows", metric_names)
        summary = evaluation.summarize_threshold_results(artifacts.eval_metrics)
        self.assertEqual(summary["promotion_gate_state"], "blocked")
        self.assertIn("minimum_feature_rows", summary["failed_thresholds"])

    def test_production_substrate_conversion_matches_governance_persistence_shape(self) -> None:
        feature_rows = [_feature_row(index) for index in range(30)]
        model_rows = generator.generate_rows(feature_rows)
        artifacts = evaluation.build_evaluation_artifacts(
            feature_rows=feature_rows,
            model_rows=model_rows,
            purpose="production_promotion_evaluation",
            request_status="completed",
            write_policy="database_persisted_production_eval_substrate",
            evidence_source="real_database_evaluation",
        )

        persistence_rows = production_substrate.to_persistence_artifacts(artifacts)
        summary = production_substrate.build_summary(
            feature_rows=feature_rows,
            model_rows=model_rows,
            artifacts=artifacts,
            persistence_rows=persistence_rows,
        )

        self.assertEqual(persistence_rows["model_eval_run"][0]["run_name"], "production_promotion_evaluation")
        self.assertIn("horizon", persistence_rows["model_eval_label"][0])
        self.assertIn("factor_name", persistence_rows["model_promotion_metric"][0])
        self.assertEqual(summary["write_policy"], "database_persisted_production_eval_substrate")
        self.assertEqual(summary["evidence_source"], "real_database_evaluation")
        self.assertEqual(summary["calibration_summary"], None)
        self.assertEqual(summary["upstream_dependency_status"]["model_01_market_regime"], "deferred_after_real_evaluation")

    def test_candidate_builder_keeps_symbol_in_metadata_not_model_vector(self) -> None:
        rows = builder.build_candidate_rows(
            sector_context_rows=[{"available_time": "2026-01-02T09:30:00-05:00", "sector_or_industry_symbol": "XLK", "2_sector_handoff_state": "selected", "2_sector_handoff_rank": 1}],
            exposure_rows=[{"available_time": "2026-01-02T09:30:00-05:00", "source_sector_or_industry_symbol": "XLK", "routing_symbol_ref": "AAPL", "holding_weight": 0.05}],
            target_evidence_rows=[{"available_time": "2026-01-02T09:30:00-05:00", "routing_symbol_ref": "AAPL", "target_return_15min": 0.02, "target_dollar_volume": 1_000_000, "target_spread_bps": 4}],
            anonymity_min_bucket_k=1,
        )
        self.assertEqual(len(rows), 1)
        payload = rows[0]["anonymous_target_feature_vector"]
        self.assertNotIn("AAPL", repr(payload))
        self.assertEqual(rows[0]["metadata_payload_json"]["routing_symbol_ref"], "AAPL")
        self.assertEqual(rows[0]["candidate_anonymity_check_state"], "pass")


if __name__ == "__main__":
    unittest.main()
