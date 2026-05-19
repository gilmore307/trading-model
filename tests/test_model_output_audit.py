from __future__ import annotations

import unittest

from model_governance.model_output_audit import audit_rows, cleanup_sql_for_reports


class ModelOutputAuditTests(unittest.TestCase):
    def test_audit_rows_classifies_empty_columns_by_actionability(self) -> None:
        rows = [
            {
                "available_time": "2016-01-04T09:35:00-05:00",
                "target_candidate_id": "anon_aapl",
                "model_id": "alpha_confidence_model",
                "5_alpha_confidence_score_390min": 0.8,
                "event_strategy_failure_gate_ref": None,
                "stale_debug_column": None,
            },
            {
                "available_time": "2016-01-04T09:40:00-05:00",
                "target_candidate_id": "anon_msft",
                "model_id": "alpha_confidence_model",
                "5_alpha_confidence_score_390min": None,
                "event_strategy_failure_gate_ref": None,
                "stale_debug_column": None,
            },
        ]

        report = audit_rows(
            "model_05_alpha_confidence",
            rows,
            columns=[
                "available_time",
                "target_candidate_id",
                "model_id",
                "5_alpha_confidence_score_390min",
                "event_strategy_failure_gate_ref",
                "stale_debug_column",
            ],
            estimated_total_rows=2,
        )

        self.assertEqual(report["all_null_column_count"], 2)
        by_column = {row["column"]: row for row in report["all_null_columns"]}
        self.assertEqual(by_column["event_strategy_failure_gate_ref"]["classification"], "all_null_optional_evidence")
        self.assertEqual(by_column["stale_debug_column"]["recommended_action"], "review_drop_or_stop_emitting_column")
        self.assertEqual(report["sparse_columns"][0]["column"], "5_alpha_confidence_score_390min")

    def test_cleanup_sql_only_includes_review_drop_columns(self) -> None:
        reports = [
            {
                "table": "model_05_alpha_confidence",
                "all_null_columns": [
                    {"column": "stale_debug_column", "recommended_action": "review_drop_or_stop_emitting_column"},
                    {"column": "event_strategy_failure_gate_ref", "recommended_action": "keep_as_explicit_missing_evidence_marker"},
                ],
            }
        ]

        sql = cleanup_sql_for_reports(reports)

        self.assertEqual(sql, ['ALTER TABLE "trading_model"."model_05_alpha_confidence" DROP COLUMN IF EXISTS "stale_debug_column";'])


if __name__ == "__main__":
    unittest.main()
