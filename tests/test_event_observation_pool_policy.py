from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from models.model_09_event_risk_governor.event_observation_pool_policy import (
    build_event_observation_pool_policy,
    write_event_observation_pool_policy_artifacts,
)


class EventObservationPoolPolicyTests(unittest.TestCase):
    def test_policy_separates_research_and_realtime_scope(self) -> None:
        policy = build_event_observation_pool_policy(generated_at_utc="2026-05-17T03:00:00+00:00")
        summary = policy.summary

        self.assertEqual(summary["historical_research_scope"], "scan_all_point_in_time_events_to_explain_residual_anomalies")
        self.assertEqual(summary["realtime_operation_scope"], "observe_reviewed_event_observation_pool_only")
        self.assertIn("cpi_inflation_release", summary["active_realtime_observation_pool"])
        self.assertIn("legal_regulatory_investigation", summary["probationary_realtime_observation_pool"])
        self.assertTrue(summary["agent_review_required_for_strategy_promotion"])
        self.assertEqual(summary["provider_calls"], 0)
        self.assertFalse(summary["model_activation_performed"])

    def test_strategy_promotion_requires_agent_review(self) -> None:
        policy = build_event_observation_pool_policy(generated_at_utc="2026-05-17T03:00:00+00:00")
        rules = {row.rule_key: row for row in policy.promotion_rule_rows}

        self.assertIn("strategy_layer_promotion", rules)
        self.assertTrue(rules["strategy_layer_promotion"].agent_review_required)
        self.assertIn("stable predictive reaction", rules["strategy_layer_promotion"].minimum_requirement)
        self.assertTrue(rules["agent_final_decision"].agent_review_required)

    def test_writes_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            output_dir = Path(raw_tmp) / "policy"
            policy = build_event_observation_pool_policy(generated_at_utc="2026-05-17T03:00:00+00:00")
            write_event_observation_pool_policy_artifacts(policy, output_dir)

            payload_path = output_dir / "event_observation_pool_policy.json"
            pool_path = output_dir / "event_observation_pool.csv"
            rules_path = output_dir / "event_promotion_rules.csv"
            self.assertTrue(payload_path.exists())
            self.assertTrue(pool_path.exists())
            self.assertTrue(rules_path.exists())
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["contract_type"], "event_observation_pool_policy_v1")
            self.assertIn("legal_regulatory_investigation", pool_path.read_text(encoding="utf-8"))
            self.assertIn("strategy_layer_promotion", rules_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
