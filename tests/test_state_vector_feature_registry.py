from __future__ import annotations

import unittest

from models import state_vector_feature_registry as registry
from models.model_04_event_overlay import contract as layer4_contract
from models.model_05_alpha_confidence import contract as layer5_contract
from models.model_06_position_projection import contract as layer6_contract
from models.model_07_underlying_action import contract as layer7_contract
from models.model_08_option_expression import contract as layer8_contract


class StateVectorFeatureRegistryTests(unittest.TestCase):
    def test_feature_semantics_are_explicit_and_valid(self) -> None:
        registry.validate_feature_semantics()
        by_field = registry.semantics_by_field()

        self.assertEqual(by_field["1_breadth_participation_score"].feature_use, "model_facing")
        self.assertEqual(by_field["3_target_direction_score_<window>"].high_value_meaning, "signed")
        self.assertEqual(by_field["3_tradability_score_<window>"].feature_use, "model_facing")
        self.assertEqual(by_field["3_tradability_score_<window>"].high_value_meaning, "good")
        self.assertEqual(by_field["3_target_noise_score_<window>"].high_value_meaning, "bad")
        self.assertEqual(by_field["2_sector_handoff_state"].feature_use, "routing_only")
        self.assertEqual(by_field["target_state_embedding"].feature_use, "research_only")
        self.assertEqual(by_field["4_event_direction_bias_score_<horizon>"].high_value_meaning, "signed")
        self.assertEqual(by_field["4_event_gap_risk_score_<horizon>"].high_value_meaning, "bad")
        self.assertEqual(by_field["5_alpha_direction_score_<horizon>"].high_value_meaning, "signed")
        self.assertEqual(by_field["5_drawdown_risk_score_<horizon>"].high_value_meaning, "bad")
        self.assertEqual(by_field["6_target_exposure_score_<horizon>"].high_value_meaning, "signed")
        self.assertEqual(by_field["6_cost_to_adjust_position_score_<horizon>"].high_value_meaning, "bad")
        self.assertEqual(by_field["7_underlying_action_direction_score_<horizon>"].high_value_meaning, "signed")
        self.assertEqual(by_field["7_underlying_adverse_risk_score_<horizon>"].high_value_meaning, "bad")
        self.assertEqual(by_field["7_underlying_trade_intensity_score_<horizon>"].score_class, "intensity")
        self.assertEqual(by_field["7_underlying_action_confidence_score_<horizon>"].feature_use, "model_facing")
        self.assertEqual(by_field["8_option_expression_direction_score_<horizon>"].high_value_meaning, "signed")
        self.assertEqual(by_field["8_option_theta_risk_score_<horizon>"].high_value_meaning, "bad")
        self.assertEqual(by_field["8_option_liquidity_fit_score_<horizon>"].score_class, "liquidity")
        self.assertEqual(by_field["8_option_expression_confidence_score_<horizon>"].feature_use, "model_facing")

    def test_layer_two_dispersion_and_crowding_are_split(self) -> None:
        by_field = registry.semantics_by_field()

        self.assertIn("2_sector_internal_dispersion_score", by_field)
        self.assertIn("2_sector_crowding_risk_score", by_field)
        self.assertNotIn("2_sector_dispersion_crowding_score", by_field)

    def test_layer_4_8_contract_score_families_are_registered(self) -> None:
        by_field = registry.semantics_by_field()
        required_fields = (
            layer4_contract.CORE_SCORE_FAMILIES
            + layer4_contract.IMPACT_SCORE_FAMILIES
            + layer5_contract.SCORE_FAMILIES
            + layer6_contract.SCORE_FAMILIES
            + layer7_contract.SCORE_FAMILIES
            + layer8_contract.SCORE_FAMILIES
        )

        missing = [field for field in required_fields if field not in by_field]
        self.assertEqual([], missing)


if __name__ == "__main__":
    unittest.main()
