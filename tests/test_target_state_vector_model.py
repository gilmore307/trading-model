from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo

import scripts.models.model_03_target_state_vector.generate_model_03_target_state_vector as generate_script
import scripts.models.model_03_target_state_vector.evaluate_model_03_target_state_vector as evaluate_script
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
        "target_context_state_version": "target_context_state",
        "market_state_features": {"state_window_sync_policy": "market_sector_target_blocks_must_share_identical_observation_windows", "market_return_1h": 0.001},
        "sector_state_features": {"state_window_sync_policy": "market_sector_target_blocks_must_share_identical_observation_windows", "sector_return_1h": 0.002},
        "target_state_features": {
            "state_window_sync_policy": "market_sector_target_blocks_must_share_identical_observation_windows",
            "target_direction_return_shape": {"return_10min": ret, "return_1h": ret * 2, "return_1D": ret * 3, "return_1W": ret * 4},
            "target_trend_quality_state": {"trend_quality_1h": 0.8, "path_stability_1h": 0.9},
            "target_trend_age_state": {"state_persistence_score_1h": 0.7},
            "target_exhaustion_decay_state": {"late_trend_risk_score_1h": 0.1},
            "target_volatility_range_state": {"realized_vol_1h": 0.02},
            "target_liquidity_tradability_state": {"spread_bps": 5, "dollar_volume": 1_000_000},
        },
        "cross_state_features": {"state_window_sync_policy": "market_sector_target_blocks_must_share_identical_observation_windows", "target_vs_market_residual_direction": ret, "target_vs_sector_residual_direction": ret / 2, "sector_confirmation_state": "sector_confirmed"},
        "feature_quality_diagnostics": {"has_target_close": True},
    }


class TargetStateVectorModelTests(unittest.TestCase):
    def test_database_entrypoints_default_to_current_feature_surface(self) -> None:
        self.assertEqual(generate_script.DEFAULT_FEATURE_TABLE, "feature_03_target_state_vector")
        self.assertEqual(evaluate_script.DEFAULT_FEATURE_TABLE, "feature_03_target_state_vector")
        self.assertEqual(evaluation.DEFAULT_FEATURE_TABLE, "feature_03_target_state_vector")

    def test_database_evaluation_allows_empty_source_window(self) -> None:
        class EmptyCursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, *_args, **_kwargs):
                return None

            def fetchone(self):
                return {"row_count": 0, "data_start_time": None, "data_end_time": None, "target_candidate_count": 0}

            def fetchall(self):
                return []

            def __iter__(self):
                return iter(())

        class EmptyConnection:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def cursor(self, *args, **kwargs):
                return EmptyCursor()

        class EmptyPsycopg:
            def connect(self, *_args, **_kwargs):
                return EmptyConnection()

        original_load_psycopg = evaluate_script._load_psycopg
        evaluate_script._load_psycopg = lambda: (EmptyPsycopg(), object())
        try:
            with TemporaryDirectory() as tmpdir:
                output_path = Path(tmpdir) / "evaluation.json"
                exit_code = evaluate_script.main(
                    [
                        "--from-database",
                        "--database-url",
                        "postgresql://redacted@localhost/redacted",
                        "--source-start",
                        "2016-01-01T00:00:00-05:00",
                        "--source-end",
                        "2016-07-01T00:00:00-05:00",
                        "--output-json",
                        str(output_path),
                    ]
                )
                payload = json.loads(output_path.read_text(encoding="utf-8"))
        finally:
            evaluate_script._load_psycopg = original_load_psycopg

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["threshold_summary"]["promotion_gate_state"], "blocked")
        self.assertEqual(payload["empty_evaluation"]["status"], "blocked_no_rows")
        self.assertEqual(payload["empty_evaluation"]["row_counts"]["feature_rows"], 0)
        self.assertIn("minimum_feature_rows", payload["threshold_summary"]["failed_thresholds"])

    def test_database_evaluation_uses_summary_queries_for_nonempty_fold(self) -> None:
        class SummaryCursor:
            def __init__(self):
                self._summary_rows = [
                    {
                        "row_count": 300,
                        "data_start_time": "2016-01-01T09:30:00-05:00",
                        "data_end_time": "2016-06-30T16:00:00-05:00",
                        "target_candidate_count": 2,
                    },
                    {
                        "row_count": 300,
                        "data_start_time": "2016-01-01T09:30:00-05:00",
                        "data_end_time": "2016-06-30T16:00:00-05:00",
                        "target_candidate_count": 2,
                    },
                ]

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, *_args, **_kwargs):
                return None

            def fetchone(self):
                return self._summary_rows.pop(0)

            def fetchall(self):
                return [{"target_candidate_id": "tcand_001", "row_count": 300}]

            def __iter__(self):
                return iter(())

        class SummaryConnection:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def cursor(self, *args, **kwargs):
                return SummaryCursor()

        class SummaryPsycopg:
            def connect(self, *_args, **_kwargs):
                return SummaryConnection()

        original_load_psycopg = evaluate_script._load_psycopg
        evaluate_script._load_psycopg = lambda: (SummaryPsycopg(), object())
        try:
            with TemporaryDirectory() as tmpdir:
                output_path = Path(tmpdir) / "evaluation.json"
                exit_code = evaluate_script.main(
                    [
                        "--from-database",
                        "--database-url",
                        "postgresql://redacted@localhost/redacted",
                        "--source-start",
                        "2016-01-01T00:00:00-05:00",
                        "--source-end",
                        "2016-07-01T00:00:00-05:00",
                        "--output-json",
                        str(output_path),
                    ]
                )
                payload = json.loads(output_path.read_text(encoding="utf-8"))
        finally:
            evaluate_script._load_psycopg = original_load_psycopg

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["database_summary_evaluation"]["status"], "completed_summary_mode")
        self.assertEqual(payload["database_summary_evaluation"]["row_counts"]["feature_rows"], 300)
        self.assertEqual(payload["tables"]["model_eval_label"], [])
        self.assertIn("minimum_target_vs_market_sector_improvement_abs", payload["threshold_summary"]["failed_thresholds"])

    def test_database_generation_allows_empty_source_window(self) -> None:
        class EmptyCursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, *_args, **_kwargs):
                return None

            def fetchone(self):
                return {"table_ref": None}

            def fetchall(self):
                return []

            def __iter__(self):
                return iter(())

        class EmptyConnection:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def cursor(self, *args, **kwargs):
                return EmptyCursor()

        class EmptyPsycopg:
            def connect(self, *_args, **_kwargs):
                return EmptyConnection()

        original_load_psycopg = generate_script._load_psycopg
        generate_script._load_psycopg = lambda: (EmptyPsycopg(), object())
        try:
            with TemporaryDirectory() as tmpdir:
                output_path = Path(tmpdir) / "model_rows.jsonl"
                row_count = generate_script.generate_from_database(
                    database_url="postgresql://redacted@localhost/redacted",
                    feature_schema="trading_data",
                    feature_table="feature_03_target_state_vector",
                    target_schema="trading_model",
                    target_table="model_03_target_state_vector",
                    explainability_table="model_03_target_state_vector_explainability",
                    diagnostics_table="model_03_target_state_vector_diagnostics",
                    source_start="2016-01-01T00:00:00-05:00",
                    source_end="2016-07-01T00:00:00-05:00",
                    model_version=generator.MODEL_VERSION,
                    output=output_path,
                )
                output_text = output_path.read_text(encoding="utf-8")
        finally:
            generate_script._load_psycopg = original_load_psycopg

        self.assertEqual(row_count, 0)
        self.assertEqual(output_text, "")

    def test_database_generation_streams_feature_rows_in_batches(self) -> None:
        class EmptyCursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        class EmptyConnection:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def cursor(self, *args, **kwargs):
                return EmptyCursor()

        class EmptyPsycopg:
            def connect(self, *_args, **_kwargs):
                return EmptyConnection()

        batch_sizes: list[int] = []
        generated_ids: list[str] = []

        def fake_stream(*_args, **_kwargs):
            for index in range(5):
                yield {"target_candidate_id": f"tcand_{index}"}

        def fake_generate_ordered_row(feature_row, *, model_version):
            generated_ids.append(feature_row["target_candidate_id"])
            return {"target_candidate_id": feature_row["target_candidate_id"], "model_version": model_version}

        def fake_write_batch(_cursor, rows, **_kwargs):
            batch_sizes.append(len(rows))

        original_load_psycopg = generate_script._load_psycopg
        original_stream = generate_script.stream_feature_rows
        original_batch_size = generate_script.MODEL_WRITE_BATCH_SIZE
        original_generate_ordered_row = generator.generate_ordered_row
        original_write_batch = generate_script._write_model_batch
        generate_script._load_psycopg = lambda: (EmptyPsycopg(), object())
        generate_script.stream_feature_rows = fake_stream
        generate_script.MODEL_WRITE_BATCH_SIZE = 2
        generator.generate_ordered_row = fake_generate_ordered_row
        generate_script._write_model_batch = fake_write_batch
        try:
            row_count = generate_script.generate_from_database(
                database_url="postgresql://redacted@localhost/redacted",
                feature_schema="trading_data",
                feature_table="feature_03_target_state_vector",
                target_schema="trading_model",
                target_table="model_03_target_state_vector",
                explainability_table="model_03_target_state_vector_explainability",
                diagnostics_table="model_03_target_state_vector_diagnostics",
                source_start="2016-01-01T00:00:00-05:00",
                source_end="2016-07-01T00:00:00-05:00",
                model_version=generator.MODEL_VERSION,
                output=None,
            )
        finally:
            generate_script._load_psycopg = original_load_psycopg
            generate_script.stream_feature_rows = original_stream
            generate_script.MODEL_WRITE_BATCH_SIZE = original_batch_size
            generator.generate_ordered_row = original_generate_ordered_row
            generate_script._write_model_batch = original_write_batch

        self.assertEqual(row_count, 5)
        self.assertEqual(batch_sizes, [2, 2, 1])
        self.assertEqual(generated_ids, [f"tcand_{index}" for index in range(5)])

    def test_generator_emits_direction_neutral_scores_without_downstream_actions(self) -> None:
        rows = generator.generate_rows([_feature_row(15)])
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["model_id"], "target_state_vector_model")
        self.assertIn("3_target_direction_score_1h", row)
        self.assertIn("3_target_direction_strength_score_1h", row)
        self.assertIn("3_target_state_persistence_score_1h", row)
        self.assertIn("3_target_exhaustion_risk_score_1h", row)
        self.assertIn("3_tradability_score_1h", row)
        self.assertIn("target_context_state", row)
        self.assertNotIn("alpha_confidence", row)
        self.assertNotIn("position_size", row)
        self.assertNotIn("final_action", row)
        self.assertEqual(row["state_quality_diagnostics"]["identity_leakage_check"], "passed")
        self.assertEqual(row["state_quality_diagnostics"]["field_semantics_policy"]["target_state_embedding"], "research_only_not_primary_model_feature")

        primary_rows = generator.build_primary_rows(rows)
        explainability_rows = generator.build_explainability_rows(rows)
        diagnostics_rows = generator.build_diagnostics_rows(rows)
        self.assertNotIn("target_context_state", primary_rows[0])
        self.assertNotIn("state_quality_diagnostics", primary_rows[0])
        self.assertEqual(explainability_rows[0]["target_context_state_ref"], row["target_context_state_ref"])
        self.assertIn("target_context_state", explainability_rows[0])
        self.assertEqual(diagnostics_rows[0]["diagnostic_payload_json"]["identity_leakage_check"], "passed")
        self.assertIn("3_state_quality_score", diagnostics_rows[0])

    def test_evaluation_builds_baseline_ladder_and_defers_small_fixture_thresholds(self) -> None:
        feature_rows = [_feature_row(index) for index in range(40)]
        model_rows = generator.generate_rows(feature_rows)
        artifacts = evaluation.build_evaluation_artifacts(feature_rows=feature_rows, model_rows=model_rows)
        metric_names = {row["metric_name"] for row in artifacts.eval_metrics}
        label_names = {row["label_name"] for row in artifacts.eval_labels}
        self.assertIn("future_tradeable_path", label_names)
        self.assertIn("forward_path_risk", label_names)
        self.assertIn("liquidity_tradability_outcome", label_names)
        self.assertIn("state_transition_quality", label_names)
        self.assertIn("abs_corr:market_only_baseline", metric_names)
        self.assertIn("abs_corr:market_sector_baseline", metric_names)
        self.assertIn("abs_corr:market_sector_target_context", metric_names)
        self.assertIn("label_count:future_tradeable_path", metric_names)
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
            target_evidence_rows=[{"available_time": "2026-01-02T09:30:00-05:00", "routing_symbol_ref": "AAPL", "target_return_1h": 0.02, "target_dollar_volume": 1_000_000, "target_spread_bps": 4}],
            anonymity_min_bucket_k=1,
        )
        self.assertEqual(len(rows), 1)
        payload = rows[0]["anonymous_target_feature_vector"]
        self.assertNotIn("AAPL", repr(payload))
        self.assertEqual(rows[0]["metadata_payload_json"]["routing_symbol_ref"], "AAPL")
        self.assertEqual(rows[0]["candidate_anonymity_check_state"], "pass")


if __name__ == "__main__":
    unittest.main()
