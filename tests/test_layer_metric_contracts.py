import unittest

from model_governance.evaluation.layer_metric_contracts import (
    METRIC_FAMILY_DESCRIPTIONS,
    all_layer_metric_contracts,
    layer_metric_contract,
    layer_metric_contract_payload,
)


class LayerMetricContractTests(unittest.TestCase):
    def test_contract_covers_current_five_models(self) -> None:
        contracts = all_layer_metric_contracts()

        self.assertEqual([contract.layer for contract in contracts], list(range(1, 6)))
        self.assertEqual(len({contract.model_id for contract in contracts}), 5)
        for contract in contracts:
            self.assertTrue(contract.tests_for_role("primary"), contract.model_id)
            self.assertTrue(contract.tests_for_role("guardrail"), contract.model_id)
            self.assertTrue(contract.tests_for_role("avoid"), contract.model_id)

    def test_unified_decision_contract_covers_target_allocation(self) -> None:
        model_four = layer_metric_contract(4)
        metric_ids = {test.metric_id for test in model_four.tests}

        self.assertIn("target_allocation_calibration", metric_ids)
        self.assertIn("uncosted_action_win_rate", {test.metric_id for test in model_four.tests_for_role("avoid")})

    def test_event_state_contract_covers_distribution_effect_channels(self) -> None:
        model_three = layer_metric_contract(3)
        metric_ids = {test.metric_id for test in model_three.tests}

        self.assertIn("distribution_effect_channel_calibration", metric_ids)

    def test_option_expression_contract_does_not_use_underlying_only_pnl(self) -> None:
        model_five = layer_metric_contract(5)

        self.assertIn("option_expression", model_five.metric_families)
        avoided = {test.metric_id for test in model_five.tests_for_role("avoid")}
        self.assertIn("underlying_only_pnl_as_option_score", avoided)

    def test_payload_exposes_group_supplemental_tests(self) -> None:
        payload = layer_metric_contract_payload()

        self.assertIn("group_contribution", METRIC_FAMILY_DESCRIPTIONS)
        self.assertEqual(len(payload["layers"]), 5)
        self.assertTrue(payload["model_group_supplemental_tests"])


if __name__ == "__main__":
    unittest.main()
