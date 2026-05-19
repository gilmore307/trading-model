from __future__ import annotations

import unittest

from model_governance.model_output_audit import audit_rows, cleanup_sql_for_reports, audit_database


class ModelOutputAuditTests(unittest.TestCase):
    def test_audit_database_uses_fast_table_sample_before_limit_fallback(self) -> None:
        class FakeCursor:
            def __init__(self) -> None:
                self.executed: list[str] = []
                self._result: list[dict[str, object]] = []

            def execute(self, sql: str, params=()) -> None:
                self.executed.append(sql)
                if "to_regclass" in sql:
                    self._result = [{"table_ref": "trading_model.model_01_market_regime"}]
                elif "information_schema.columns" in sql:
                    self._result = [{"column_name": "available_time"}, {"column_name": "1_score"}]
                elif "estimated_rows" in sql:
                    self._result = [{"estimated_rows": 2}]
                else:
                    self._result = [{"available_time": "2016-01-05T09:35:00-05:00", "1_score": 0.4}]

            def fetchone(self):
                return self._result[0] if self._result else None

            def fetchall(self):
                return self._result

        cursor = FakeCursor()

        audit_database(cursor, tables=("model_01_market_regime",), sample_limit=1)

        select_sql = "\n".join(cursor.executed)
        self.assertIn('TABLESAMPLE SYSTEM (10) LIMIT %s', select_sql)

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

    def test_known_accumulation_and_selection_columns_are_not_generator_defects(self) -> None:
        report = audit_rows(
            "model_02_sector_context",
            [
                {
                    "available_time": "2016-01-04T09:35:00-05:00",
                    "2_sector_trend_stability_score": None,
                    "2_sector_handoff_rank": None,
                }
            ],
            columns=["available_time", "2_sector_trend_stability_score", "2_sector_handoff_rank"],
            estimated_total_rows=1,
        )

        by_column = {row["column"]: row for row in report["all_null_columns"]}
        self.assertEqual(by_column["2_sector_trend_stability_score"]["classification"], "all_null_data_accumulation_gap")
        self.assertEqual(by_column["2_sector_handoff_rank"]["classification"], "all_null_optional_selection")

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
