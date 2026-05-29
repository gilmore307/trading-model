from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from models.model_05_alpha_confidence import generate_rows, train_after_cost_alpha_model
from models.model_05_alpha_confidence.evaluation import assert_no_label_leakage, build_alpha_confidence_labels


REPO_ROOT = Path(__file__).resolve().parents[1]


FORBIDDEN_TERMS = {
    "buy",
    "sell",
    "hold",
    "target_exposure",
    "position_size",
    "account_risk_allocation",
    "option_contract",
    "option_symbol",
    "strike",
    "dte",
    "delta",
    "order_type",
    "broker_order_id",
    "execution_result",
    "final_action",
    "future_fill",
    "realized_pnl",
}


class AlphaConfidenceModelTests(unittest.TestCase):
    def test_generation_requires_trained_after_cost_artifacts(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires trained Layer 5 after-cost alpha artifacts"):
            generate_rows([_base_row()])

    def test_trained_after_cost_artifacts_produce_final_vector(self) -> None:
        artifact_bundle = _artifact_bundle()
        output = generate_rows([_positive_row()], after_cost_alpha_model=artifact_bundle)[0]
        vector = output["alpha_confidence_vector"]

        self.assertGreater(vector["5_alpha_direction_score_1W"], 0.0)
        self.assertGreater(vector["5_alpha_confidence_score_1W"], 0.5)
        self.assertEqual(vector["5_after_cost_alpha_score_1W"], vector["5_alpha_confidence_score_1W"])
        self.assertNotIn("base_alpha_vector", output)
        self.assertIn("trained_after_cost_alpha_score", output["alpha_confidence_diagnostics"]["horizon_reason_codes"]["1W"])
        assert_no_label_leakage(output)
        self.assert_no_forbidden_terms(output)

    def test_trained_negative_after_cost_score_drives_negative_direction(self) -> None:
        artifact_bundle = _artifact_bundle()
        output = generate_rows([_negative_row()], after_cost_alpha_model=artifact_bundle)[0]
        vector = output["alpha_confidence_vector"]

        self.assertLess(vector["5_alpha_confidence_score_1W"], 0.5)
        self.assertLess(vector["5_alpha_direction_score_1W"], 0.0)
        self.assertGreater(vector["5_alpha_strength_score_1W"], 0.0)

    def test_neutral_after_cost_score_keeps_direction_strength_and_tradability_low(self) -> None:
        artifact_bundle = _artifact_bundle()
        output = generate_rows([_neutral_row()], after_cost_alpha_model=artifact_bundle)[0]
        vector = output["alpha_confidence_vector"]

        self.assertAlmostEqual(vector["5_alpha_confidence_score_1W"], 0.5, delta=0.12)
        self.assertLess(abs(vector["5_alpha_direction_score_1W"]), 0.25)
        self.assertLess(vector["5_alpha_tradability_score_1W"], 0.5)
        self.assertEqual(output["training_sample_scope"], "dense_minute_target_state")
        self.assertIn("no_material_alpha_edge", output["alpha_confidence_diagnostics"]["horizon_reason_codes"]["1W"])

    def test_single_horizon_artifact_must_match_horizon(self) -> None:
        artifact = _artifact_bundle()["artifacts_by_horizon"]["1W"]

        with self.assertRaisesRegex(ValueError, "missing horizon '10min'"):
            generate_rows([_positive_row()], after_cost_alpha_model=artifact)

    def test_database_decision_rows_are_dense_target_state_not_event_gated(self) -> None:
        script = _load_generator_script()
        rows = script._decision_rows(
            event_failure_rows=[],
            model_03_rows=[
                {
                    "available_time": "2026-05-07T10:30:00-04:00",
                    "target_candidate_id": "anon_target_001",
                    "target_context_state_ref": "tcs_fixture",
                    "3_state_quality_score": 0.80,
                }
            ],
            source_03_rows=[],
            model_02_rows=[],
            model_01_rows=[
                {
                    "available_time": "2026-05-07T10:29:00-04:00",
                    "1_market_risk_stress_score": 0.25,
                }
            ],
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["training_sample_scope"], "dense_minute_target_state")
        self.assertEqual(rows[0]["target_candidate_id"], "anon_target_001")
        self.assertEqual(rows[0]["event_failure_risk_vector"], {})

    def test_database_decision_rows_use_latest_prior_context(self) -> None:
        script = _load_generator_script()
        rows = script._decision_rows(
            event_failure_rows=[],
            model_03_rows=[
                {
                    "available_time": "2026-05-07T10:30:00-04:00",
                    "target_candidate_id": "anon_target_001",
                    "3_state_quality_score": 0.80,
                }
            ],
            source_03_rows=[
                {
                    "available_time": "2026-05-07T10:30:00-04:00",
                    "target_candidate_id": "anon_target_001",
                    "symbol": "AAPL",
                }
            ],
            model_02_rows=[
                {
                    "available_time": "2026-05-07T10:00:00-04:00",
                    "sector_or_industry_symbol": "AAPL",
                    "2_sector_context_support_quality_score": 0.30,
                },
                {
                    "available_time": "2026-05-07T10:29:00-04:00",
                    "sector_or_industry_symbol": "AAPL",
                    "2_sector_context_support_quality_score": 0.70,
                },
                {
                    "available_time": "2026-05-07T10:31:00-04:00",
                    "sector_or_industry_symbol": "AAPL",
                    "2_sector_context_support_quality_score": 0.10,
                },
            ],
            model_01_rows=[
                {
                    "available_time": "2026-05-07T10:29:00-04:00",
                    "1_state_quality_score": 0.60,
                },
                {
                    "available_time": "2026-05-07T10:31:00-04:00",
                    "1_state_quality_score": 0.20,
                },
            ],
        )

        self.assertEqual(rows[0]["market_context_state"]["1_state_quality_score"], 0.60)
        self.assertEqual(rows[0]["sector_context_state"]["2_sector_context_support_quality_score"], 0.70)

    def test_training_script_attaches_after_cost_labels_from_future_bars(self) -> None:
        script = _load_training_script()
        rows = script.attach_after_cost_return_labels(
            [
                {
                    **_base_row(),
                    "available_time": "2026-05-07T10:30:00-04:00",
                    "target_candidate_id": "anon_target_001",
                    "target_context_state": _target_state(direction=-0.40),
                }
            ],
            source_03_rows=[
                {
                    "target_candidate_id": "anon_target_001",
                    "available_time": "2026-05-07T10:30:00-04:00",
                    "bar_close": 100.0,
                },
                {
                    "target_candidate_id": "anon_target_001",
                    "available_time": "2026-05-07T10:40:00-04:00",
                    "bar_close": 99.0,
                },
            ],
            cost_bps=5.0,
        )

        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0]["after_cost_return_10min"], 0.0095)
        self.assertEqual(rows[0]["after_cost_label_time_10min"], "2026-05-07T10:40:00-04:00")

    def test_labels_are_offline_and_join_by_vector_ref(self) -> None:
        output = generate_rows([_base_row()], after_cost_alpha_model=_artifact_bundle())[0]
        labels = build_alpha_confidence_labels(
            [output],
            [
                {
                    "alpha_confidence_vector_ref": output["alpha_confidence_vector_ref"],
                    "forward_return_1W": -0.05,
                    "idiosyncratic_residual_return_1W": -0.04,
                    "alpha_tradable_label_1W": True,
                }
            ],
        )

        self.assertEqual(len(labels), 1)
        self.assertTrue(labels[0]["alpha_tradable_label_1W"])
        self.assertNotIn("forward_return_1W", output)

    def assert_no_forbidden_terms(self, value: object) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                self.assertNotIn(str(key).lower(), FORBIDDEN_TERMS)
                self.assert_no_forbidden_terms(nested)
        elif isinstance(value, list):
            for nested in value:
                self.assert_no_forbidden_terms(nested)


def _base_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "available_time": "2026-05-07T10:30:00-04:00",
        "tradeable_time": "2026-05-07T10:31:00-04:00",
        "target_candidate_id": "anon_target_001",
        "market_context_state_ref": "mcs_fixture",
        "sector_context_state_ref": "scs_fixture",
        "target_context_state_ref": "tcs_fixture",
        "event_failure_risk_vector_ref": "efrv_fixture",
        "market_context_state": {
            "1_market_risk_stress_score": 0.20,
            "1_market_liquidity_support_score": 0.85,
            "1_state_quality_score": 0.90,
        },
        "sector_context_state": {
            "2_sector_context_support_quality_score": 0.80,
            "2_state_quality_score": 0.88,
        },
        "target_context_state": _target_state(direction=0.40),
        "event_failure_risk_vector": {
            "4_event_strategy_failure_risk_score_1W": 0.85,
            "4_event_entry_block_pressure_score_1W": 0.80,
            "4_event_exposure_cap_pressure_score_1W": 0.45,
            "4_event_strategy_disable_pressure_score_1W": 0.30,
            "4_event_path_risk_amplifier_score_1W": 0.70,
            "4_event_evidence_quality_score_1W": 0.95,
            "4_event_applicability_confidence_score_1W": 0.90,
        },
        "quality_calibration_state": {
            "sample_support_score": 0.85,
            "walk_forward_reliability_score": 0.80,
            "model_ensemble_agreement_score": 0.85,
            "model_disagreement_score": 0.10,
            "out_of_distribution_score": 0.10,
            "data_quality_score": 0.90,
        },
    }
    row.update(overrides)
    return row


def _target_state(*, direction: float) -> dict[str, object]:
    state: dict[str, object] = {"3_state_quality_score": 0.90}
    for horizon in ("10min", "1h", "1D", "1W"):
        state.update(
            {
                f"3_target_direction_score_{horizon}": direction,
                f"3_target_trend_quality_score_{horizon}": 0.75,
                f"3_target_path_stability_score_{horizon}": 0.80,
                f"3_target_noise_score_{horizon}": 0.20,
                f"3_target_transition_risk_score_{horizon}": 0.15,
                f"3_context_direction_alignment_score_{horizon}": 0.70 if direction >= 0 else -0.70,
                f"3_context_support_quality_score_{horizon}": 0.80,
                f"3_tradability_score_{horizon}": 0.85,
                f"3_beta_dependency_score_{horizon}": 0.20,
            }
        )
    return state


def _row_with_after_cost_label(direction: float, realized_return: float) -> dict[str, object]:
    row = _base_row(target_context_state=_target_state(direction=direction), event_failure_risk_vector={})
    row.update({f"after_cost_return_{horizon}": realized_return for horizon in ("10min", "1h", "1D", "1W")})
    return row


def _positive_row() -> dict[str, object]:
    return _row_with_after_cost_label(0.70, 0.04)


def _neutral_row() -> dict[str, object]:
    return _row_with_after_cost_label(0.0, 0.0)


def _negative_row() -> dict[str, object]:
    return _row_with_after_cost_label(-0.70, -0.04)


def _artifact_bundle() -> dict[str, object]:
    training_rows = [_positive_row(), _neutral_row(), _negative_row()]
    try:
        return {
            "artifacts_by_horizon": {
                horizon: train_after_cost_alpha_model(
                    training_rows,
                    horizon=horizon,
                    label_field=f"after_cost_return_{horizon}",
                    iterations=900,
                    learning_rate=0.10,
                )
                for horizon in ("10min", "1h", "1D", "1W")
            }
        }
    except RuntimeError as error:
        raise unittest.SkipTest(str(error)) from error


def _load_generator_script():
    script = REPO_ROOT / "scripts/models/model_05_alpha_confidence/generate_model_05_alpha_confidence.py"
    spec = importlib.util.spec_from_file_location(script.stem, script)
    if spec is None or spec.loader is None:
        raise AssertionError("failed to load Layer 5 generator script")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_training_script():
    script = REPO_ROOT / "scripts/models/model_05_alpha_confidence/train_model_05_alpha_confidence.py"
    spec = importlib.util.spec_from_file_location(script.stem, script)
    if spec is None or spec.loader is None:
        raise AssertionError("failed to load Layer 5 training script")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    unittest.main()
