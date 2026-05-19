from __future__ import annotations

import unittest

from model_governance.model_output_quality_gate import evaluate_quality_gate


class ModelOutputQualityGateTests(unittest.TestCase):
    def test_primary_score_gap_blocks_gate(self) -> None:
        audit = {
            "contract_type": "model_output_table_quality_audit",
            "schema": "trading_model",
            "sample_limit": 5000,
            "tables": [
                {
                    "table": "model_01_market_regime",
                    "status": "sampled",
                    "all_null_columns": [
                        {
                            "column": "1_market_trend_quality_score",
                            "classification": "all_null_score_gap",
                            "recommended_action": "repair_generator_or_upstream_data",
                        }
                    ],
                    "sparse_column_count": 0,
                }
            ],
        }

        gate = evaluate_quality_gate(audit)

        self.assertEqual(gate["contract_type"], "model_output_quality_gate")
        self.assertEqual(gate["status"], "blocked")
        self.assertEqual(gate["summary"]["blocker_count"], 1)
        self.assertEqual(gate["blockers"][0]["column"], "1_market_trend_quality_score")

    def test_support_gaps_warn_by_default_and_block_when_strict(self) -> None:
        audit = {
            "contract_type": "model_output_table_quality_audit",
            "schema": "trading_model",
            "sample_limit": 5000,
            "tables": [
                {
                    "table": "model_02_sector_context_explainability",
                    "status": "sampled",
                    "all_null_columns": [
                        {
                            "column": "2_rate_sensitivity_score",
                            "classification": "all_null_explainability_gap",
                            "recommended_action": "repair_explainability_generation_or_stop_emitting_column",
                        }
                    ],
                    "sparse_column_count": 0,
                }
            ],
        }

        self.assertEqual(evaluate_quality_gate(audit)["status"], "passed")
        self.assertEqual(evaluate_quality_gate(audit, strict_support=True)["status"], "blocked")

    def test_data_accumulation_gap_warns_without_blocking(self) -> None:
        audit = {
            "contract_type": "model_output_table_quality_audit",
            "schema": "trading_model",
            "sample_limit": 5000,
            "tables": [
                {
                    "table": "model_02_sector_context",
                    "status": "sampled",
                    "all_null_columns": [
                        {
                            "column": "2_sector_transition_risk_score",
                            "classification": "all_null_data_accumulation_gap",
                            "recommended_action": "backfill_longer_history_or_keep_missing_until_evidence_matures",
                        }
                    ],
                    "sparse_column_count": 0,
                }
            ],
        }

        gate = evaluate_quality_gate(audit)

        self.assertEqual(gate["status"], "passed")
        self.assertEqual(gate["summary"]["warning_count"], 1)


if __name__ == "__main__":
    unittest.main()
