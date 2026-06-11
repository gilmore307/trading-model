from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from model_governance.local_layer_scripts import FIXTURE_INPUT_ROWS, write_payload
from models.model_05_alpha_confidence import train_after_cost_alpha_model
from models.model_05_alpha_confidence.contract import HORIZONS


REPO_ROOT = Path(__file__).resolve().parents[1]
LAYERS = {
    "model_04_event_failure_risk": "event_failure_risk",
    "model_05_alpha_confidence": "alpha_confidence",
    "model_06_dynamic_risk_policy": "dynamic_risk_policy",
    "model_07_position_projection": "position_projection",
    "model_08_underlying_action": "underlying_action",
    "model_09_option_expression": "option_expression",
    "model_10_event_risk_governor": "event_risk_governor",
}
LAYER_NUMBERS = {
    "model_04_event_failure_risk": 4,
    "model_05_alpha_confidence": 5,
    "model_06_dynamic_risk_policy": 6,
    "model_07_position_projection": 7,
    "model_08_underlying_action": 8,
    "model_09_option_expression": 9,
    "model_10_event_risk_governor": 10,
}


class LayerFourTenScriptEntrypointTests(unittest.TestCase):
    def _load_script_module(self, script: Path):
        spec = importlib.util.spec_from_file_location(script.stem, script)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, *args],
            cwd=REPO_ROOT,
            env={"PYTHONPATH": "src"},
            text=True,
            capture_output=True,
            check=False,
        )

    def _write_layer_05_artifact_bundle(self, tmp_path: Path) -> Path:
        fixture = FIXTURE_INPUT_ROWS["model_05_alpha_confidence"][0]
        training_rows = []
        for index, realized_return in enumerate((-0.02, 0.0, 0.02)):
            row = dict(fixture)
            row["target_candidate_id"] = f"layer_05_fixture_{index}"
            row.update({f"after_cost_return_{horizon}": realized_return for horizon in HORIZONS})
            training_rows.append(row)
        try:
            bundle = {
                "artifacts_by_horizon": {
                    horizon: train_after_cost_alpha_model(
                        training_rows,
                        horizon=horizon,
                        label_field=f"after_cost_return_{horizon}",
                        iterations=25,
                    )
                    for horizon in HORIZONS
                }
            }
        except RuntimeError as error:
            raise unittest.SkipTest(str(error)) from error
        path = tmp_path / "model_05_after_cost_alpha_artifacts.json"
        path.write_text(json.dumps(bundle, sort_keys=True), encoding="utf-8")
        return path

    def test_generate_evaluate_review_scripts_support_help(self) -> None:
        for surface, slug in LAYERS.items():
            scripts = [
                f"scripts/models/{surface}/generate_{surface}.py",
                f"scripts/models/{surface}/evaluate_{surface}.py",
                f"scripts/models/{surface}/review_{slug}_promotion.py",
            ]
            for script in scripts:
                with self.subTest(script=script):
                    result = self._run([script, "--help"])
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("usage:", result.stdout)

    def test_model_10_event_sql_column_typing_uses_layer_10_prefix(self) -> None:
        generator = self._load_script_module(REPO_ROOT / "scripts/models/model_10_event_risk_governor/generate_model_10_event_risk_governor.py")

        self.assertEqual(generator._column_type("10_event_gap_risk_score_1W"), "DOUBLE PRECISION")
        self.assertEqual(generator._column_type("8_event_gap_risk_score_1W"), "TEXT")

    def test_model_10_database_generation_allows_empty_decisions(self) -> None:
        generator = self._load_script_module(REPO_ROOT / "scripts/models/model_10_event_risk_governor/generate_model_10_event_risk_governor.py")

        self.assertEqual(generator._database_model_rows([], model_version="fixture"), [])

    def test_model_10_database_input_emits_no_event_decisions_from_target_context(self) -> None:
        generator = self._load_script_module(REPO_ROOT / "scripts/models/model_10_event_risk_governor/generate_model_10_event_risk_governor.py")

        rows = generator._decision_rows(
            source_rows=[],
            source_03_rows=[
                {
                    "available_time": "2016-01-04T09:35:00-05:00",
                    "target_candidate_id": "anon_aapl",
                    "symbol": "AAPL",
                }
            ],
            model_03_rows=[
                {
                    "available_time": "2016-01-04T09:35:00-05:00",
                    "tradeable_time": "2016-01-04T09:35:00-05:00",
                    "target_candidate_id": "anon_aapl",
                    "market_context_state_ref": "m01_1",
                    "sector_context_state_ref": "m02_1",
                    "target_context_state_ref": "m03_1",
                    "target_context_state": {"3_target_direction_score_1W": 0.1},
                }
            ],
            model_09_rows=[
                {
                    "available_time": "2016-01-04T09:35:00-05:00",
                    "target_candidate_id": "anon_aapl",
                    "underlying_action_plan_ref": "uap_1",
                }
            ],
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["event_rows"], [])
        self.assertEqual(rows[0]["symbol_for_join_only"], "AAPL")
        self.assertEqual(rows[0]["target_context_state_ref"], "m03_1")
        self.assertEqual(rows[0]["underlying_action_plan_ref"], "uap_1")

    def test_layer_06_database_input_marks_neutral_replay_portfolio_ref(self) -> None:
        generator = self._load_script_module(REPO_ROOT / "scripts/models/model_06_dynamic_risk_policy/generate_model_06_dynamic_risk_policy.py")

        rows = generator._decision_rows(
            [
                {
                    "available_time": "2016-01-04T09:35:00-05:00",
                    "target_candidate_id": "anon_aapl",
                    "alpha_confidence_vector_ref": "acv_1",
                }
            ]
        )

        self.assertEqual(
            rows[0]["portfolio_exposure_state_ref"],
            "portfolio_exposure_state:neutral_replay:anon_aapl:2016-01-04T09:35:00-05:00",
        )

    def test_model_10_database_generation_reads_current_event_source_table(self) -> None:
        generator = self._load_script_module(REPO_ROOT / "scripts/models/model_10_event_risk_governor/generate_model_10_event_risk_governor.py")

        class Cursor:
            def __init__(self) -> None:
                self.queries: list[tuple[str, list[object] | tuple[object, ...]]] = []

            def execute(self, query: str, params: list[object] | tuple[object, ...] = ()) -> None:
                self.queries.append((query, params))

            def fetchall(self):
                return []

        cursor = Cursor()
        generator._fetch_event_source_rows(cursor, schema="trading_data", source_start=None, source_end=None)

        self.assertIn('"trading_data"."m06_residual_event_governance_data_acquisition"', cursor.queries[-1][0])

    def test_active_generator_column_type_prefixes_match_layer_numbers(self) -> None:
        for surface, layer_number in LAYER_NUMBERS.items():
            with self.subTest(surface=surface):
                generator = self._load_script_module(REPO_ROOT / f"scripts/models/{surface}/generate_{surface}.py")
                self.assertEqual(generator._column_type(f"{layer_number}_fixture_score"), "DOUBLE PRECISION")
                other_layer = layer_number - 1
                self.assertEqual(generator._column_type(f"{other_layer}_fixture_score"), "TEXT")

    def test_layer_08_database_input_preserves_layer_7_projection_fields(self) -> None:
        generator = self._load_script_module(REPO_ROOT / "scripts/models/model_08_underlying_action/generate_model_08_underlying_action.py")

        rows = generator._decision_rows(
            alpha_rows=[
                {
                    "available_time": "2016-01-04T09:35:00-05:00",
                    "target_candidate_id": "anon_aapl",
                    "alpha_confidence_vector_ref": "acv_1",
                    "5_alpha_confidence_score_1W": 0.82,
                }
            ],
            projection_rows=[
                {
                    "available_time": "2016-01-04T09:35:00-05:00",
                    "target_candidate_id": "anon_aapl",
                    "alpha_confidence_vector_ref": "acv_1",
                    "position_projection_vector_ref": "ppv_1",
                    "7_dominant_projection_horizon": "1W",
                    "7_target_exposure_score_1W": 0.35,
                    "6_target_exposure_score_1W": 0.99,
                }
            ],
            source_rows=[
                {
                    "available_time": "2016-01-04T09:35:00-05:00",
                    "target_candidate_id": "anon_aapl",
                    "symbol": "AAPL",
                    "bar_close": 102.5,
                }
            ],
        )

        projection_payload = rows[0]["position_projection_vector"]
        self.assertEqual(projection_payload["7_dominant_projection_horizon"], "1W")
        self.assertEqual(projection_payload["7_target_exposure_score_1W"], 0.35)
        self.assertNotIn("6_target_exposure_score_1W", projection_payload)
        self.assertEqual(rows[0]["underlying_quote_state"]["reference_price"], 102.5)

    def test_layer_06_database_input_uses_market_and_event_model_rows(self) -> None:
        generator = self._load_script_module(REPO_ROOT / "scripts/models/model_06_dynamic_risk_policy/generate_model_06_dynamic_risk_policy.py")

        rows = generator._decision_rows(
            [
                {
                    "available_time": "2016-01-04T09:35:00-05:00",
                    "target_candidate_id": "anon_aapl",
                    "alpha_confidence_vector_ref": "acv_1",
                    "5_alpha_confidence_score_1W": 0.82,
                }
            ],
            market_rows=[
                {
                    "available_time": "2016-01-04T09:30:00-05:00",
                    "1_market_risk_stress_score_1W": 0.61,
                    "1_market_liquidity_support_score_1W": 0.42,
                }
            ],
            event_failure_rows=[
                {
                    "available_time": "2016-01-04T09:35:00-05:00",
                    "target_candidate_id": "anon_aapl",
                    "4_event_strategy_failure_risk_score_1W": 0.44,
                    "4_event_session_gap_risk_score_1W": 0.20,
                }
            ],
        )

        self.assertEqual(rows[0]["market_context_state"]["1_market_risk_stress_score_1W"], 0.61)
        self.assertEqual(rows[0]["systemic_event_risk_state"]["systemic_event_risk_score_1W"], 0.44)
        self.assertNotEqual(rows[0]["market_context_state"], {"1_market_risk_stress_score": 0.25, "1_market_liquidity_support_score": 0.70})

    def test_layer_07_database_input_requires_layer_6_policy_state(self) -> None:
        generator = self._load_script_module(REPO_ROOT / "scripts/models/model_07_position_projection/generate_model_07_position_projection.py")

        alpha_rows = [
            {
                "available_time": "2016-01-04T09:35:00-05:00",
                "target_candidate_id": "anon_aapl",
                "alpha_confidence_vector_ref": "acv_1",
                "5_alpha_confidence_score_1W": 0.82,
            }
        ]
        self.assertEqual(generator._decision_rows(alpha_rows, dynamic_risk_rows=[]), [])

        rows = generator._decision_rows(
            alpha_rows,
            dynamic_risk_rows=[
                {
                    "available_time": "2016-01-04T09:35:00-05:00",
                    "target_candidate_id": "anon_aapl",
                    "alpha_confidence_vector_ref": "acv_1",
                    "dynamic_risk_policy_state_ref": "drp_1",
                    "6_resolved_dynamic_risk_budget_score": 0.33,
                    "6_resolved_new_exposure_permission_score": 0.22,
                }
            ],
        )

        self.assertEqual(rows[0]["dynamic_risk_policy_state_ref"], "drp_1")
        self.assertEqual(rows[0]["risk_budget_state"]["risk_budget_available_score"], 0.33)
        self.assertEqual(rows[0]["risk_budget_state"]["single_name_exposure_limit"], 0.22)

    def test_layer_04_database_input_falls_back_to_neutral_target_context_without_gate_table(self) -> None:
        generator = self._load_script_module(REPO_ROOT / "scripts/models/model_04_event_failure_risk/generate_model_04_event_failure_risk.py")

        class FakeCursor:
            def __init__(self) -> None:
                self._one = None
                self._many = []
                self.statements: list[str] = []

            def execute(self, sql: str, params: tuple[object, ...] | list[object] | None = None) -> None:
                self.statements.append(sql)
                if "to_regclass" in sql:
                    self._one = {"table_ref": None}
                    return
                self._many = [
                    {
                        "available_time": "2016-01-04T09:35:00-05:00",
                        "tradeable_time": "2016-01-04T09:35:00-05:00",
                        "target_candidate_id": "anon_aapl",
                        "market_context_state_ref": "mcs_1",
                        "sector_context_state_ref": "scs_1",
                        "target_context_state_ref": "tcs_1",
                        "target_context_state": {"3_state_quality_score": 0.8},
                    }
                ]

            def fetchone(self):
                return self._one

            def fetchall(self):
                return self._many

        cursor = FakeCursor()
        rows = generator._fetch_input_rows(
            cursor,
            source_schema="trading_model",
            source_table="event_strategy_failure_gate",
            target_context_schema="trading_model",
            target_context_table="model_03_target_state_vector",
            source_start="2016-01-01T00:00:00-05:00",
            source_end="2016-07-01T00:00:00-04:00",
        )

        self.assertEqual(len(rows), 1)
        self.assertNotIn("model_03_target_state_vector_explainability", "\n".join(cursor.statements))
        self.assertEqual(rows[0]["target_candidate_id"], "anon_aapl")
        self.assertEqual(rows[0]["event_strategy_failure_gate"]["gate_status"], "not_present")
        model_rows = generator.generate_rows(rows)
        self.assertEqual(model_rows[0]["4_resolved_event_failure_risk_status"], "no_reviewed_event_failure_risk")

    def test_layer_04_target_context_explainability_join_casts_available_time(self) -> None:
        generator = self._load_script_module(REPO_ROOT / "scripts/models/model_04_event_failure_risk/generate_model_04_event_failure_risk.py")

        class FakeCursor:
            def __init__(self) -> None:
                self._one = None
                self._many = []
                self.statements: list[str] = []

            def execute(self, sql: str, params: tuple[object, ...] | list[object] | None = None) -> None:
                self.statements.append(sql)
                if "to_regclass" in sql:
                    self._one = {"table_ref": "trading_model.model_03_target_state_vector_explainability"}
                    return
                self._many = [
                    {
                        "available_time": "2016-01-04T09:35:00-05:00",
                        "target_candidate_id": "anon_aapl",
                        "target_context_state": {"3_state_quality_score": 0.8},
                        "target_state_embedding": {"embedding": [0.1]},
                        "state_cluster_id": "cluster_1",
                    }
                ]

            def fetchone(self):
                return self._one

            def fetchall(self):
                return self._many

        cursor = FakeCursor()
        rows = generator._fetch_target_context_rows(
            cursor,
            schema="trading_model",
            table="model_03_target_state_vector",
            source_start="2016-01-01T00:00:00-05:00",
            source_end="2016-07-01T00:00:00-04:00",
        )

        join_sql = "\n".join(cursor.statements)
        self.assertIn('e."available_time"::timestamptz = t."available_time"::timestamptz', join_sql)
        self.assertNotIn('e."target_state_embedding"', join_sql)
        self.assertEqual(rows[0]["state_cluster_id"], "cluster_1")

    def test_layer_09_reads_underlying_action_explainability_with_qualified_time_filters(self) -> None:
        generator = self._load_script_module(REPO_ROOT / "scripts/models/model_09_option_expression/generate_model_09_option_expression.py")

        class FakeCursor:
            def __init__(self) -> None:
                self._one = None
                self._many = []
                self.statements: list[str] = []

            def execute(self, sql: str, params: tuple[object, ...] | list[object] | None = None) -> None:
                self.statements.append(sql)
                if "to_regclass" in sql:
                    self._one = {"table_ref": "trading_model.model_08_underlying_action_explainability"}
                    return
                self._many = [
                    {
                        "available_time": "2016-01-04T09:35:00-05:00",
                        "target_candidate_id": "anon_aapl",
                        "underlying_action_plan_ref": "uap_1",
                        "underlying_action_plan": {"handoff_to_layer_9": {"direction": "neutral"}},
                    }
                ]

            def fetchone(self):
                return self._one

            def fetchall(self):
                return self._many

        cursor = FakeCursor()
        rows = generator._fetch_layer_8_rows(
            cursor,
            source_start="2016-01-01T00:00:00-05:00",
            source_end="2016-07-01T00:00:00-04:00",
        )

        sql = "\n".join(cursor.statements)
        self.assertIn('u."available_time"::timestamptz >= %s::timestamptz', sql)
        self.assertIn('u."available_time"::timestamptz < %s::timestamptz', sql)
        self.assertIn('e."underlying_action_plan_ref" = u."underlying_action_plan_ref"', sql)
        self.assertIn('s."bar_close" AS "underlying_reference_price"', sql)
        self.assertEqual(rows[0]["underlying_action_plan_ref"], "uap_1")

    def test_layer_09_database_input_binds_option_candidates_when_feature_rows_exist(self) -> None:
        generator = self._load_script_module(REPO_ROOT / "scripts/models/model_09_option_expression/generate_model_09_option_expression.py")

        layer_8_rows = [
            {
                "available_time": "2016-01-04T09:35:00-05:00",
                "tradeable_time": "2016-01-04T09:35:00-05:00",
                "target_candidate_id": "anon_aapl",
                "underlying_symbol": "AAPL",
                "underlying_reference_price": 102.5,
                "underlying_action_plan_ref": "uap_1",
                "underlying_action_plan": {
                    "planned_underlying_action_type": "open_long",
                    "handoff_to_layer_9": {"underlying_path_direction": "bullish"},
                },
            }
        ]
        candidate_rows = [
            {
                "underlying": "AAPL",
                "snapshot_time": "2016-01-04T09:35:00-05:00",
                "snapshot_type": "entry",
                "option_symbol": "AAPL160115C00100000",
                "feature_payload_json": {
                    "option_right_type": "CALL",
                    "bid_price": 2.10,
                    "ask_price": 2.20,
                    "days_to_expiration": 11,
                    "delta": 0.45,
                    "volume": 500,
                    "open_interest": 2500,
                    "quote_age_seconds": 15,
                },
                "feature_quality_diagnostics": {"quality_status": "ready"},
            }
        ]

        rows = generator._layer_9_input_rows(layer_8_rows, candidate_rows)

        self.assertEqual(rows[0]["option_chain_snapshot_ref"], "m05_option_expression_feature_generation:AAPL:2016-01-04T09:35:00-05:00")
        self.assertEqual(rows[0]["option_surface_status"], "optionable_chain_available")
        self.assertEqual(rows[0]["option_quote_available_time"], "2016-01-04T09:35:00-05:00")
        self.assertEqual(rows[0]["underlying_quote_snapshot_ref"], "m03_target_state_vector_data_acquisition:anon_aapl:2016-01-04T09:35:00-05:00")
        self.assertEqual(rows[0]["underlying_reference_price"], 102.5)
        self.assertEqual(rows[0]["option_contract_candidates"][0]["contract_ref"], "AAPL160115C00100000")
        self.assertEqual(rows[0]["option_contract_candidates"][0]["option_right"], "CALL")
        self.assertEqual(rows[0]["option_contract_candidates"][0]["dte"], 11)

    def test_layer_09_fetches_only_entry_option_candidates_for_layer_8_keys(self) -> None:
        generator = self._load_script_module(REPO_ROOT / "scripts/models/model_09_option_expression/generate_model_09_option_expression.py")

        class FakeCursor:
            def __init__(self) -> None:
                self._one = {"table_ref": "trading_data.m05_option_expression_feature_generation"}
                self._many = [
                    {
                        "underlying": "AAPL",
                        "snapshot_time": "2016-01-04T09:35:00-05:00",
                        "snapshot_type": "entry",
                        "option_symbol": "AAPL160115C00100000",
                        "feature_payload_json": {"option_right_type": "CALL"},
                        "feature_quality_diagnostics": {},
                    }
                ]
                self.statements: list[str] = []
                self.inserted_keys: list[tuple[object, ...]] = []

            def execute(self, sql: str, params: tuple[object, ...] | list[object] | None = None) -> None:
                self.statements.append(sql)

            def executemany(self, sql: str, params: list[tuple[object, ...]]) -> None:
                self.statements.append(sql)
                self.inserted_keys.extend(params)

            def fetchone(self):
                return self._one

            def fetchall(self):
                return self._many

        cursor = FakeCursor()
        rows = generator._fetch_option_candidate_rows(
            cursor,
            source_start="2016-01-01T00:00:00-05:00",
            source_end="2016-05-01T00:00:00-05:00",
            layer_8_rows=[
                {
                    "available_time": "2016-01-04T09:35:00-05:00",
                    "underlying_symbol": "AAPL",
                }
            ],
        )

        sql = "\n".join(cursor.statements)
        self.assertIn("layer_9_option_candidate_keys", sql)
        self.assertIn('lower(coalesce(f."snapshot_type"', sql)
        self.assertIn("= 'entry'", sql)
        self.assertIn('k.underlying = upper(f."underlying")', sql)
        self.assertEqual(cursor.inserted_keys, [("AAPL", "2016-01-04T09:35:00-05:00")])
        self.assertEqual(rows[0]["option_symbol"], "AAPL160115C00100000")

    def test_layer_09_database_input_keeps_status_row_when_option_chain_missing(self) -> None:
        generator = self._load_script_module(REPO_ROOT / "scripts/models/model_09_option_expression/generate_model_09_option_expression.py")

        rows = generator._layer_9_input_rows(
            [
                {
                    "available_time": "2016-01-04T09:35:00-05:00",
                    "tradeable_time": "2016-01-04T09:35:00-05:00",
                    "target_candidate_id": "anon_btc",
                    "underlying_symbol": "BTC",
                    "underlying_action_plan_ref": "uap_btc",
                    "underlying_action_plan": {
                        "planned_underlying_action_type": "open_long",
                        "handoff_to_layer_9": {"underlying_path_direction": "bullish"},
                    },
                }
            ],
            [],
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["option_surface_status"], "optionable_chain_missing")
        self.assertEqual(rows[0]["option_contract_candidates"], [])

    def test_local_layer_payload_writer_serializes_database_datetimes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "summary.json"
            write_payload(
                {
                    "labels": [
                        {
                            "available_time": datetime(2016, 1, 4, 14, 35, tzinfo=timezone.utc),
                            "underlying_action_plan_ref": "uap_fixture",
                        }
                    ],
                    "summary": {"model_surface": "model_08_underlying_action"},
                },
                output_path,
            )

            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["labels"][0]["available_time"], "2016-01-04T14:35:00+00:00")

    def test_layer_04_from_database_writes_target_table_by_default(self) -> None:
        script = (REPO_ROOT / "scripts/models/model_04_event_failure_risk/generate_model_04_event_failure_risk.py").read_text(encoding="utf-8")

        self.assertIn("if args.from_database or args.write_database:", script)
        self.assertIn("if args.output_jsonl or not args.from_database:", script)
        self.assertIn('print(f"generated {len(rows)} rows into {args.target_schema}.{args.target_table}")', script)

    def test_fixture_generate_evaluate_review_defers_activation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            for surface, slug in LAYERS.items():
                with self.subTest(surface=surface):
                    rows_path = tmp_path / f"{surface}.jsonl"
                    eval_path = tmp_path / f"{surface}.eval.json"
                    review_path = tmp_path / f"{surface}.review.json"

                    generate_args = [
                        f"scripts/models/{surface}/generate_{surface}.py",
                        "--output-jsonl",
                        str(rows_path),
                    ]
                    if surface == "model_05_alpha_confidence":
                        generate_args.extend([
                            "--after-cost-alpha-model-json",
                            str(self._write_layer_05_artifact_bundle(tmp_path)),
                        ])
                    generate = self._run(generate_args)
                    self.assertEqual(generate.returncode, 0, generate.stderr)
                    self.assertEqual(len(rows_path.read_text(encoding="utf-8").splitlines()), 1)

                    evaluate = self._run([
                        f"scripts/models/{surface}/evaluate_{surface}.py",
                        "--model-jsonl",
                        str(rows_path),
                        "--output-json",
                        str(eval_path),
                    ])
                    self.assertEqual(evaluate.returncode, 0, evaluate.stderr)
                    evaluation = json.loads(eval_path.read_text(encoding="utf-8"))
                    self.assertEqual(evaluation["summary"]["model_surface"], surface)
                    self.assertEqual(evaluation["summary"]["layer_number"], LAYER_NUMBERS[surface])
                    self.assertEqual(evaluation["summary"]["label_row_count"], 1)
                    self.assertTrue(evaluation["summary"]["leakage_check_passed"])
                    self.assertIn("fixture_or_local_evidence_must_defer", evaluation["summary"]["reason_codes"])
                    self.assertIn("acceptance_thresholds", evaluation)
                    self.assertIn("threshold_results", evaluation)
                    self.assertEqual(evaluation["acceptance_thresholds"]["minimum_eval_labels"], 1.0)
                    self.assertTrue(evaluation["threshold_results"]["minimum_eval_labels"]["passed"])
                    self.assertEqual(evaluation["failed_thresholds"], {})

                    review = self._run([
                        f"scripts/models/{surface}/review_{slug}_promotion.py",
                        "--evaluation-summary-json",
                        str(eval_path),
                        "--output-json",
                        str(review_path),
                    ])
                    self.assertEqual(review.returncode, 0, review.stderr)
                    decision = json.loads(review_path.read_text(encoding="utf-8"))
                    self.assertEqual(decision["decision_status"], "deferred")
                    self.assertFalse(decision["activation_allowed"])


if __name__ == "__main__":
    unittest.main()
