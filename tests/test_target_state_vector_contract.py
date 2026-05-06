from __future__ import annotations

import unittest
from pathlib import Path

from models.model_03_target_state_vector import contract


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    REPO_ROOT
    / "src"
    / "models"
    / "model_03_target_state_vector"
    / "target_state_vector_contract.md"
)


class TargetStateVectorContractTests(unittest.TestCase):
    def test_v1_blocks_are_relationship_first(self) -> None:
        self.assertEqual(contract.LAYER3_PREPROCESSING_VECTOR, "anonymous_target_feature_vector")
        self.assertEqual(contract.LAYER3_OUTPUT_STATE_VECTOR, "target_state_vector")
        self.assertEqual(
            contract.STATE_VECTOR_BLOCKS,
            (
                "market_state_features",
                "sector_state_features",
                "target_state_features",
                "cross_state_features",
            ),
        )
        self.assertIn("target_vs_market_residual_direction", contract.CROSS_STATE_FEATURE_GROUPS)
        self.assertIn("target_vs_sector_residual_direction", contract.CROSS_STATE_FEATURE_GROUPS)
        self.assertIn("sector_confirmation_state", contract.CROSS_STATE_FEATURE_GROUPS)
        self.assertIn("idiosyncratic_residual_state", contract.CROSS_STATE_FEATURE_GROUPS)
        self.assertIn("3_target_direction_score_<window>", contract.DIRECTION_NEUTRAL_SCORE_FAMILIES)
        self.assertIn("3_target_direction_strength_score_<window>", contract.DIRECTION_NEUTRAL_SCORE_FAMILIES)
        self.assertIn("3_target_state_persistence_score_<window>", contract.DIRECTION_NEUTRAL_SCORE_FAMILIES)
        self.assertIn("3_target_exhaustion_risk_score_<window>", contract.DIRECTION_NEUTRAL_SCORE_FAMILIES)
        self.assertIn("3_tradability_score_<window>", contract.DIRECTION_NEUTRAL_SCORE_FAMILIES)

    def test_v1_uses_sparse_state_windows_not_strategy_variants(self) -> None:
        self.assertEqual(contract.SYNCHRONIZED_STATE_WINDOWS, ("5min", "15min", "60min", "390min"))
        self.assertEqual(contract.TRAILING_STATE_WINDOWS, contract.SYNCHRONIZED_STATE_WINDOWS)
        self.assertEqual(
            contract.STATE_WINDOW_SYNC_POLICY,
            "market_sector_target_blocks_must_share_identical_observation_windows",
        )
        self.assertEqual(contract.LABEL_HORIZONS, ("15min", "60min", "390min"))
        self.assertEqual(
            contract.BASELINE_LADDER,
            (
                "market_only_baseline",
                "market_sector_baseline",
                "market_sector_target_vector",
            ),
        )

    def test_contract_document_names_required_feature_groups(self) -> None:
        text = CONTRACT_PATH.read_text(encoding="utf-8")
        required_tokens = {
            "trading_model.model_03_target_state_vector",
            "available_time",
            "tradeable_time",
            "target_candidate_id",
            "market_context_state_ref",
            "sector_context_state_ref",
            "target_state_vector_ref",
            "market_state_features",
            "sector_state_features",
            "target_state_features",
            "cross_state_features",
            "target_price_state",
            "target_direction_return_shape",
            "target_trend_age_state",
            "target_exhaustion_decay_state",
            "target_volatility_range_state",
            "target_liquidity_tradability_state",
            "target_peer_rank_state",
            "target_vs_market_residual_direction",
            "target_vs_sector_residual_direction",
            "sector_confirmation_state",
            "idiosyncratic_residual_state",
            "3_target_direction_score_<window>",
            "3_context_support_quality_score_<window>",
            "MFE/MAE balance",
        }
        for token in required_tokens:
            self.assertIn(token, text)

    def test_contract_excludes_identity_future_labels_and_strategy_variants(self) -> None:
        self.assertIn("target_candidate_id", contract.MODEL_FACING_IDENTITY_FIELDS)
        for forbidden in {
            "ticker",
            "symbol",
            "company",
            "audit_symbol_ref",
            "routing_symbol_ref",
            "future_return",
            "realized_pnl",
            "strategy_variant",
        }:
            self.assertIn(forbidden, contract.FORBIDDEN_MODEL_FACING_FIELDS)

        text = CONTRACT_PATH.read_text(encoding="utf-8")
        for token in {
            "target_candidate_id` as a categorical feature",
            "forward returns, realized PnL, or future bar outcomes in inference features",
            "audit/routing metadata into the model-facing vector",
            "optimizes downstream action variants before state/outcome relationships are accepted",
            "mismatched state observation windows across market, sector, and target blocks",
            "treats positive direction as inherently better than negative direction",
            "Layer 4 alpha/direction confidence",
            "anonymous_target_feature_vector` is the Layer 3 preprocessing/input vector",
            "target_state_vector` is the Layer 3 model output",
        }:
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
