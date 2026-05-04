from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    REPO_ROOT
    / "src"
    / "models"
    / "model_03_strategy_selection"
    / "anonymous_target_candidate_builder"
    / "target_candidate_builder_contract.md"
)


class AnonymousTargetCandidateBuilderContractTests(unittest.TestCase):
    def test_contract_names_required_candidate_surfaces(self) -> None:
        contract = CONTRACT_PATH.read_text(encoding="utf-8")

        for token in {
            "anonymous_target_candidate[available_time, target_candidate_id]",
            "`available_time`",
            "`target_candidate_id`",
            "`candidate_builder_version`",
            "`market_context_state_ref`",
            "`sector_context_state_ref`",
            "anonymous_target_feature_vector",
            "audit_symbol_ref",
            "routing_symbol_ref",
            "source_stock_etf_exposure_ref",
            "target_behavior_vector",
            "sector_context_projection_vector",
            "market_context_projection_vector",
            "exposure_transmission_vector",
            "candidate_anonymity_check_state",
        }:
            self.assertIn(token, contract)

    def test_contract_preserves_anonymity_and_layer_boundaries(self) -> None:
        contract = CONTRACT_PATH.read_text(encoding="utf-8")

        for token in {
            "It is a key, not a fitting feature.",
            "must not reveal raw ticker, company, exchange, issuer, or",
            "stable symbol identity",
            "Metadata must not be joined into model-facing",
            "fitting vectors except through reviewed non-identity evidence fields",
            "ETF holdings and `stock_etf_exposure` are used only at this candidate-builder boundary",
            "raw ticker/company identity",
            "memorized symbol-specific winner/loser labels",
            "future returns or realized PnL as production fields",
            "Layer 2 selected/prioritized baskets are the source of sector transmission",
        }:
            self.assertIn(token, contract)


if __name__ == "__main__":
    unittest.main()
