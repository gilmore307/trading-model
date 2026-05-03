from __future__ import annotations

import unittest

from model_governance import schema


class ModelGovernanceSchemaTests(unittest.TestCase):
    def test_governance_schema_creates_tables_in_dependency_order(self) -> None:
        statements = schema.create_governance_schema_sql()
        joined = "\n".join(statements)

        self.assertIn('CREATE SCHEMA IF NOT EXISTS "trading_model"', statements[0])
        table_positions = {
            table: joined.index(f'"trading_model"."{table}"')
            for table in schema.TABLE_NAMES
        }
        self.assertLess(table_positions["model_dataset_request"], table_positions["model_dataset_snapshot"])
        self.assertLess(table_positions["model_dataset_snapshot"], table_positions["model_dataset_split"])
        self.assertLess(table_positions["model_dataset_snapshot"], table_positions["model_eval_label"])
        self.assertLess(table_positions["model_dataset_snapshot"], table_positions["model_eval_run"])
        self.assertLess(table_positions["model_eval_run"], table_positions["model_promotion_metric"])
        self.assertLess(table_positions["model_eval_run"], table_positions["model_promotion_candidate"])
        self.assertLess(table_positions["model_config_version"], table_positions["model_promotion_candidate"])
        self.assertLess(table_positions["model_promotion_candidate"], table_positions["model_promotion_decision"])
        self.assertLess(table_positions["model_promotion_decision"], table_positions["model_promotion_activation"])
        self.assertLess(table_positions["model_promotion_decision"], table_positions["model_promotion_rollback"])

    def test_request_table_uses_control_plane_data_window_contract(self) -> None:
        joined = "\n".join(schema.create_governance_schema_sql())

        self.assertIn('"required_data_start_time" TIMESTAMPTZ NOT NULL', joined)
        self.assertIn('"required_data_end_time" TIMESTAMPTZ NOT NULL', joined)
        self.assertIn('"required_source_key" TEXT', joined)
        self.assertIn('"required_feature_key" TEXT', joined)
        self.assertNotIn('"label_horizons"', joined)
        self.assertNotIn('"required_derived_key"', joined)
        self.assertIn('CHECK ("required_data_end_time" >= "required_data_start_time")', joined)

    def test_eval_tables_keep_model_local_semantics_outside_requests(self) -> None:
        joined = "\n".join(schema.create_governance_schema_sql())

        self.assertIn('CREATE TABLE IF NOT EXISTS "trading_model"."model_eval_label"', joined)
        self.assertIn('"horizon" TEXT NOT NULL', joined)
        self.assertIn('"label_value" DOUBLE PRECISION', joined)
        self.assertIn('CREATE TABLE IF NOT EXISTS "trading_model"."model_promotion_metric"', joined)
        self.assertIn('"factor_name" TEXT', joined)
        self.assertIn('"metric_value" DOUBLE PRECISION', joined)

    def test_promotion_tables_require_evaluation_evidence_before_decision(self) -> None:
        joined = "\n".join(schema.create_governance_schema_sql())

        self.assertIn('CREATE TABLE IF NOT EXISTS "trading_model"."model_config_version"', joined)
        self.assertIn('CREATE TABLE IF NOT EXISTS "trading_model"."model_promotion_candidate"', joined)
        self.assertIn('"eval_run_id" TEXT NOT NULL REFERENCES "trading_model"."model_eval_run"', joined)
        self.assertIn('"config_version_id" TEXT NOT NULL REFERENCES "trading_model"."model_config_version"', joined)
        self.assertIn('CREATE TABLE IF NOT EXISTS "trading_model"."model_promotion_decision"', joined)
        self.assertIn('"promotion_candidate_id" TEXT NOT NULL REFERENCES "trading_model"."model_promotion_candidate"', joined)
        self.assertIn('CREATE TABLE IF NOT EXISTS "trading_model"."model_promotion_activation"', joined)
        self.assertIn('"to_config_version_id" TEXT NOT NULL REFERENCES "trading_model"."model_config_version"', joined)
        self.assertIn('CREATE TABLE IF NOT EXISTS "trading_model"."model_promotion_rollback"', joined)
        self.assertIn('"from_config_version_id" TEXT NOT NULL REFERENCES "trading_model"."model_config_version"', joined)

    def test_json_payload_columns_are_jsonb_not_text_blobs(self) -> None:
        joined = "\n".join(schema.create_governance_schema_sql())

        for column in [
            "request_payload_json",
            "snapshot_payload_json",
            "split_payload_json",
            "label_payload_json",
            "run_payload_json",
            "metric_payload_json",
            "config_payload_json",
            "candidate_payload_json",
            "decision_payload_json",
            "activation_payload_json",
            "rollback_payload_json",
        ]:
            self.assertIn(f'"{column}" JSONB NOT NULL DEFAULT', joined)

    def test_identifier_validation_rejects_unsafe_schema_names(self) -> None:
        with self.assertRaises(ValueError):
            schema.create_governance_schema_sql('trading_model; DROP SCHEMA trading_model')

    def test_ensure_schema_executes_all_statements(self) -> None:
        class FakeCursor:
            def __init__(self) -> None:
                self.statements: list[str] = []

            def execute(self, statement: str) -> None:
                self.statements.append(statement)

        cursor = FakeCursor()
        schema.ensure_model_governance_schema(cursor)

        self.assertEqual(cursor.statements, schema.create_governance_schema_sql())


if __name__ == "__main__":
    unittest.main()
