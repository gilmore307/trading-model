from __future__ import annotations

import unittest
from unittest.mock import patch

from model_governance import model_output_support


class ModelOutputSupportTests(unittest.TestCase):
    def test_write_model_output_splits_primary_explainability_and_diagnostics_rows(self) -> None:
        rows = [
            {
                "available_time": "2016-01-04T09:35:00-05:00",
                "target_candidate_id": "anon_aapl",
                "model_output_ref": "out_1",
                "4_after_cost_edge_score_1W": 0.7,
                "unified_decision_vector": {"score": 0.7},
                "unified_decision_diagnostics": {"status": "ok"},
            }
        ]

        calls: list[dict[str, object]] = []

        def record_write_rows(cursor, rows, *, schema, table, primary_key, drop_columns, drop_absent_retired_horizon_columns=False):
            calls.append(
                {
                    "rows": rows,
                    "schema": schema,
                    "table": table,
                    "primary_key": primary_key,
                    "drop_columns": drop_columns,
                    "drop_absent_retired_horizon_columns": drop_absent_retired_horizon_columns,
                }
            )

        with patch.object(model_output_support, "_write_rows", side_effect=record_write_rows):
            model_output_support.write_model_output_with_support(
                object(),
                rows,
                target_schema="trading_model",
                target_table="model_04_unified_decision",
                primary_key=("model_output_ref",),
                explainability_columns={"unified_decision_vector"},
                diagnostics_columns={"unified_decision_diagnostics"},
            )

        self.assertEqual([call["table"] for call in calls], [
            "model_04_unified_decision",
            "model_04_unified_decision_explainability",
            "model_04_unified_decision_diagnostics",
        ])
        primary = calls[0]["rows"][0]
        self.assertIn("4_after_cost_edge_score_1W", primary)
        self.assertNotIn("unified_decision_vector", primary)
        self.assertNotIn("unified_decision_diagnostics", primary)
        self.assertEqual(calls[0]["drop_columns"], {"unified_decision_vector", "unified_decision_diagnostics"})
        self.assertTrue(calls[0]["drop_absent_retired_horizon_columns"])

        explainability = calls[1]["rows"][0]
        self.assertEqual(explainability["unified_decision_vector"], {"score": 0.7})
        self.assertEqual(explainability["explanation_payload_json"]["primary_table"], "model_04_unified_decision")
        self.assertFalse(calls[1]["drop_absent_retired_horizon_columns"])

        diagnostics = calls[2]["rows"][0]
        self.assertEqual(diagnostics["unified_decision_diagnostics"], {"status": "ok"})
        self.assertEqual(diagnostics["diagnostic_payload_json"]["primary_table"], "model_04_unified_decision")

    def test_support_identity_omits_null_reference_columns(self) -> None:
        rows = [
            {
                "available_time": "2016-01-04T09:35:00-05:00",
                "target_candidate_id": "anon_aapl",
                "model_output_ref": "out_1",
                "upstream_context_ref": None,
                "source_snapshot_ref": "src_1",
                "payload": {"score": 0.7},
            }
        ]

        identity = model_output_support._support_identity_columns(rows, ("model_output_ref",))

        self.assertIn("source_snapshot_ref", identity)
        self.assertNotIn("upstream_context_ref", identity)

    def test_empty_support_payload_columns_do_not_create_support_rows(self) -> None:
        rows = [
            {
                "available_time": "2016-01-04T09:35:00-05:00",
                "model_output_ref": "out_1",
                "4_after_cost_edge_score_1W": 0.7,
                "unified_decision_vector": {},
                "unified_decision_diagnostics": None,
            }
        ]
        calls: list[dict[str, object]] = []

        def record_write_rows(cursor, rows, *, schema, table, primary_key, drop_columns, drop_absent_retired_horizon_columns=False):
            calls.append(
                {
                    "rows": rows,
                    "table": table,
                    "drop_columns": drop_columns,
                    "drop_absent_retired_horizon_columns": drop_absent_retired_horizon_columns,
                }
            )

        with patch.object(model_output_support, "_write_rows", side_effect=record_write_rows):
            model_output_support.write_model_output_with_support(
                object(),
                rows,
                target_schema="trading_model",
                target_table="model_04_unified_decision",
                primary_key=("model_output_ref",),
                explainability_columns={"unified_decision_vector"},
                diagnostics_columns={"unified_decision_diagnostics"},
            )

        self.assertEqual([call["table"] for call in calls], ["model_04_unified_decision"])
        self.assertEqual(calls[0]["drop_columns"], {"unified_decision_vector", "unified_decision_diagnostics"})
        self.assertTrue(calls[0]["drop_absent_retired_horizon_columns"])

    def test_retired_horizon_columns_are_current_contract_only(self) -> None:
        self.assertTrue(model_output_support._is_retired_horizon_column("4_edge_score_5min"))
        self.assertTrue(model_output_support._is_retired_horizon_column("6_risk_score_390m"))
        self.assertFalse(model_output_support._is_retired_horizon_column("5_alpha_score_10min"))
        self.assertFalse(model_output_support._is_retired_horizon_column("target_context_state"))

    def test_write_rows_uses_batched_executemany_for_model_outputs(self) -> None:
        class FakeCursor:
            def __init__(self) -> None:
                self.executed: list[tuple[str, object | None]] = []
                self.executemany_calls: list[tuple[str, list[list[object]]]] = []

            def execute(self, sql: str, params: object | None = None) -> None:
                self.executed.append((sql, params))

            def executemany(self, sql: str, params: list[list[object]]) -> None:
                self.executemany_calls.append((sql, params))

            def fetchone(self):
                return (1,)

            def fetchall(self):
                return []

        cursor = FakeCursor()
        with patch.object(model_output_support, "DEFAULT_WRITE_BATCH_SIZE", 2):
            model_output_support._write_rows(
                cursor,
                [
                    {"model_output_ref": "out_1", "score": 0.1},
                    {"model_output_ref": "out_2", "score": 0.2},
                    {"model_output_ref": "out_3", "score": 0.3},
                ],
                schema="trading_model",
                table="model_04_unified_decision",
                primary_key=("model_output_ref",),
                drop_columns=set(),
            )

        self.assertEqual([len(params) for _, params in cursor.executemany_calls], [2, 1])
        self.assertTrue(all("INSERT INTO" in sql for sql, _ in cursor.executemany_calls))
        self.assertFalse(any("CREATE TEMP TABLE" in sql for sql, _ in cursor.executed))

    def test_write_rows_dedupes_duplicate_primary_keys_before_upsert(self) -> None:
        class FakeCursor:
            def __init__(self) -> None:
                self.executemany_calls: list[tuple[str, list[list[object]]]] = []

            def execute(self, sql: str, params: object | None = None) -> None:
                pass

            def executemany(self, sql: str, params: list[list[object]]) -> None:
                self.executemany_calls.append((sql, params))

            def fetchone(self):
                return (1,)

            def fetchall(self):
                return []

        cursor = FakeCursor()
        model_output_support._write_rows(
            cursor,
            [
                {"model_output_ref": "out_1", "score": 0.1},
                {"model_output_ref": "out_1", "score": 0.2},
                {"model_output_ref": "out_2", "score": 0.3},
            ],
            schema="trading_model",
            table="model_04_unified_decision",
            primary_key=("model_output_ref",),
            drop_columns=set(),
        )

        params = cursor.executemany_calls[0][1]
        self.assertEqual(params, [["out_1", 0.2], ["out_2", 0.3]])


if __name__ == "__main__":
    unittest.main()
