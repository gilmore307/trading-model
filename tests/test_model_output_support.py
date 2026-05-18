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
                "5_alpha_score_390min": 0.7,
                "alpha_confidence_vector": {"score": 0.7},
                "alpha_confidence_diagnostics": {"status": "ok"},
            }
        ]

        calls: list[dict[str, object]] = []

        def record_write_rows(cursor, rows, *, schema, table, primary_key, drop_columns):
            calls.append(
                {
                    "rows": rows,
                    "schema": schema,
                    "table": table,
                    "primary_key": primary_key,
                    "drop_columns": drop_columns,
                }
            )

        with patch.object(model_output_support, "_write_rows", side_effect=record_write_rows):
            model_output_support.write_model_output_with_support(
                object(),
                rows,
                target_schema="trading_model",
                target_table="model_05_alpha_confidence",
                primary_key=("model_output_ref",),
                explainability_columns={"alpha_confidence_vector"},
                diagnostics_columns={"alpha_confidence_diagnostics"},
            )

        self.assertEqual([call["table"] for call in calls], [
            "model_05_alpha_confidence",
            "model_05_alpha_confidence_explainability",
            "model_05_alpha_confidence_diagnostics",
        ])
        primary = calls[0]["rows"][0]
        self.assertIn("5_alpha_score_390min", primary)
        self.assertNotIn("alpha_confidence_vector", primary)
        self.assertNotIn("alpha_confidence_diagnostics", primary)
        self.assertEqual(calls[0]["drop_columns"], {"alpha_confidence_vector", "alpha_confidence_diagnostics"})

        explainability = calls[1]["rows"][0]
        self.assertEqual(explainability["alpha_confidence_vector"], {"score": 0.7})
        self.assertEqual(explainability["explanation_payload_json"]["primary_table"], "model_05_alpha_confidence")

        diagnostics = calls[2]["rows"][0]
        self.assertEqual(diagnostics["alpha_confidence_diagnostics"], {"status": "ok"})
        self.assertEqual(diagnostics["diagnostic_payload_json"]["primary_table"], "model_05_alpha_confidence")

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


if __name__ == "__main__":
    unittest.main()
