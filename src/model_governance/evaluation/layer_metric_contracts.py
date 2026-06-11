"""Layer-local evaluation metric contracts for the ten-model stack.

The contract is intentionally about metric eligibility, not metric values.  A
layer may report a metric only when its label and point-in-time evidence satisfy
the relevant family requirements.  This prevents group-level replay metrics from
being relabeled as layer-local evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

MetricRole = Literal["primary", "guardrail", "avoid"]


@dataclass(frozen=True)
class LayerMetricTest:
    metric_id: str
    label: str
    family: str
    role: MetricRole
    eligibility: str
    note: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "label": self.label,
            "metric_family": self.family,
            "role": self.role,
            "eligibility": self.eligibility,
            "note": self.note,
        }


@dataclass(frozen=True)
class LayerMetricContract:
    layer: int
    model_id: str
    layer_name: str
    metric_families: tuple[str, ...]
    tests: tuple[LayerMetricTest, ...]

    def tests_for_role(self, role: MetricRole) -> tuple[LayerMetricTest, ...]:
        return tuple(test for test in self.tests if test.role == role)

    def as_dict(self) -> dict[str, Any]:
        return {
            "layer": self.layer,
            "model_id": self.model_id,
            "layer_name": self.layer_name,
            "metric_families": list(self.metric_families),
            "tests": [test.as_dict() for test in self.tests],
        }


METRIC_FAMILY_DESCRIPTIONS: dict[str, str] = {
    "representation_context": "State/context coverage, stability, separability, and baseline improvement.",
    "calibrated_prediction": "Binary probabilistic prediction metrics with valid point-in-time labels.",
    "ranking_alpha": "Rank, spread, and score-bucket calibration for alpha/return ordering.",
    "policy_utility": "Risk-policy and allocation utility under realistic constraints.",
    "path_projection": "Projected path accuracy for exposure, risk, and state trajectories.",
    "action_plan": "Action thesis, entry/target/stop, regret, and abstention quality.",
    "option_expression": "Option contract/expression fit, feasibility, and payoff quality.",
    "event_attribution": "Event-risk recall, attribution, intervention, and opportunity-cost quality.",
    "integrity": "Point-in-time, leakage, lineage, and feasibility guardrails.",
    "group_contribution": "Ablation/counterfactual contribution tests owned by the model group.",
}


def _test(metric_id: str, label: str, family: str, role: MetricRole, eligibility: str, note: str) -> LayerMetricTest:
    return LayerMetricTest(metric_id=metric_id, label=label, family=family, role=role, eligibility=eligibility, note=note)


LAYER_METRIC_CONTRACTS: tuple[LayerMetricContract, ...] = (
    LayerMetricContract(
        1,
        "model_01_market_regime",
        "Market Regime",
        ("representation_context", "integrity", "group_contribution"),
        (
            _test("regime_state_coverage", "Regime coverage", "representation_context", "primary", "Requires point-in-time market-state rows by date/session.", "Measures whether the context surface covers the fold without unexplained gaps."),
            _test("regime_transition_stability", "Transition stability", "representation_context", "primary", "Requires ordered regime-state outputs.", "Penalizes unstable state flips near fold boundaries."),
            _test("market_context_baseline_lift", "Baseline lift", "representation_context", "primary", "Requires broad-market labels or proxies such as realized volatility/breadth/liquidity.", "Compares state output against naive market buckets."),
            _test("macro_revision_leakage", "Macro/revision leakage", "integrity", "guardrail", "Requires source release clocks and revision timestamps.", "Blocks use of revised or future macro values as inference features."),
            _test("trade_pnl_as_regime_score", "Direct trade PnL", "group_contribution", "avoid", "Only allowed as model-group context.", "A broad context layer does not own final trade outcomes."),
        ),
    ),
    LayerMetricContract(
        2,
        "model_02_sector_context",
        "Sector Context",
        ("representation_context", "integrity", "group_contribution"),
        (
            _test("sector_relative_explanatory_power", "Sector-relative explanatory power", "representation_context", "primary", "Requires PIT sector/proxy rows and sector ETF/peer outcomes.", "Measures whether sector context explains relative moves beyond Layer 1."),
            _test("proxy_mapping_accuracy", "Proxy mapping accuracy", "representation_context", "primary", "Requires timestamped sector/proxy mapping evidence.", "Checks ETF/industry proxy relevance and stability."),
            _test("sector_residual_reduction", "Residual reduction vs L1", "group_contribution", "primary", "Requires counterfactual replay or residual study with Layer 1 held fixed.", "Measures marginal context value over market regime."),
            _test("sector_map_survivorship", "Sector map survivorship", "integrity", "guardrail", "Requires point-in-time membership/proxy evidence.", "Blocks use of future sector membership or static maps as truth."),
            _test("target_trade_outcome_as_sector_score", "Target trade outcome", "group_contribution", "avoid", "Only allowed in model-group attribution.", "A sector context layer does not own target action or execution."),
        ),
    ),
    LayerMetricContract(
        3,
        "model_03_target_state_vector",
        "Target State Vector",
        ("representation_context", "path_projection", "integrity"),
        (
            _test("target_state_completeness", "State completeness", "representation_context", "primary", "Requires target-state vector rows and expected block schema.", "Measures coverage, missingness, and block-level completeness."),
            _test("baseline_ladder_improvement", "Baseline ladder improvement", "representation_context", "primary", "Requires target-state labels and baseline ladder definitions.", "Compares representation against naive/current-state baselines."),
            _test("state_quantile_separation", "Future-outcome quantile separation", "representation_context", "primary", "Requires future labels kept outside inference features.", "Checks whether state buckets separate future tradability/path outcomes."),
            _test("target_identity_leakage", "Target identity leakage", "integrity", "guardrail", "Requires anonymous target candidate and split evidence.", "Blocks target/company identity leakage into model-facing fitting vectors."),
            _test("single_auroc_for_state_vector", "Single state-vector AUROC", "calibrated_prediction", "avoid", "Only allowed for an explicit binary probability head.", "A representation is not one binary classifier."),
        ),
    ),
    LayerMetricContract(
        4,
        "model_04_event_failure_risk",
        "Event Failure Risk",
        ("calibrated_prediction", "event_attribution", "integrity"),
        (
            _test("event_failure_precision_recall", "Event failure precision/recall", "event_attribution", "primary", "Requires known-event failure labels with PIT event visibility.", "Measures event-family failure detection quality."),
            _test("event_failure_auroc_pr_auc", "Failure AUROC / PR-AUC", "calibrated_prediction", "primary", "Requires explicit binary probabilistic failure label.", "Valid only when the layer emits a probability of known event failure."),
            _test("lead_time_usefulness", "Lead-time usefulness", "event_attribution", "primary", "Requires event visibility time and decision time.", "Measures whether risk was available early enough to matter."),
            _test("post_event_article_leakage", "Post-event article leakage", "integrity", "guardrail", "Requires article/source timestamps.", "Blocks using later coverage to score pre-alpha risk."),
            _test("post_replay_residual_as_pre_alpha_input", "Post-replay residual attribution", "event_attribution", "avoid", "Owned by M06, not Layer 4.", "Residual attribution must not leak into pre-alpha event risk."),
        ),
    ),
    LayerMetricContract(
        5,
        "model_05_alpha_confidence",
        "Alpha Confidence",
        ("ranking_alpha", "calibrated_prediction", "integrity"),
        (
            _test("rank_ic_by_horizon", "Rank IC by horizon", "ranking_alpha", "primary", "Requires after-cost future return labels by horizon.", "Measures ordering quality of alpha confidence."),
            _test("decile_spread_after_cost", "After-cost decile spread", "ranking_alpha", "primary", "Requires score buckets and cost-adjusted outcomes.", "Checks whether higher scores realize better outcomes."),
            _test("expected_realized_calibration", "Expected vs realized calibration", "ranking_alpha", "primary", "Requires score buckets and realized after-cost return.", "Measures calibration of score magnitude."),
            _test("positive_alpha_auroc_brier_ece", "Positive alpha AUROC / Brier / ECE", "calibrated_prediction", "primary", "Requires explicit probability of positive after-cost return.", "Valid only for a probabilistic binary alpha head."),
            _test("purged_embargoed_cv", "Purged / embargoed CV", "integrity", "guardrail", "Requires overlapping horizon metadata.", "Prevents horizon overlap and future label bleed."),
            _test("uncosted_win_rate", "Uncosted win rate", "ranking_alpha", "avoid", "Must be cost/slippage adjusted.", "Raw win rate overstates alpha quality."),
        ),
    ),
    LayerMetricContract(
        6,
        "model_06_dynamic_risk_policy",
        "Dynamic Risk Policy",
        ("policy_utility", "integrity", "group_contribution"),
        (
            _test("risk_budget_utility", "Risk budget utility", "policy_utility", "primary", "Requires intended risk budget and realized risk evidence.", "Measures whether policy improved risk-adjusted exposure."),
            _test("volatility_target_error", "Volatility targeting error", "policy_utility", "primary", "Requires ex-ante target risk and realized volatility.", "Checks realized risk versus intended risk."),
            _test("tail_loss_reduction", "Tail-loss reduction", "policy_utility", "primary", "Requires counterfactual baseline policy.", "Measures drawdown/tail containment value."),
            _test("hard_limit_compliance", "Hard-limit compliance", "integrity", "guardrail", "Requires timestamped account-independent limits.", "Blocks budget or exposure violations."),
            _test("auroc_as_risk_policy_primary", "AUROC primary score", "calibrated_prediction", "avoid", "Only allowed for an explicit binary risk-event probability.", "Risk policy is a utility/constraint layer."),
        ),
    ),
    LayerMetricContract(
        7,
        "model_07_position_projection",
        "Position Projection",
        ("path_projection", "integrity"),
        (
            _test("exposure_path_error", "Exposure path error", "path_projection", "primary", "Requires projected and realized exposure paths.", "Measures delta/notional/gross/net projection accuracy."),
            _test("holding_period_accuracy", "Holding-period accuracy", "path_projection", "primary", "Requires planned and realized holding path labels.", "Checks duration and turnover fit."),
            _test("risk_trajectory_calibration", "Risk trajectory calibration", "path_projection", "primary", "Requires projected and realized risk trajectory.", "Measures path risk calibration."),
            _test("position_state_timestamp_audit", "Position timestamp audit", "integrity", "guardrail", "Requires point-in-time position state evidence.", "Blocks using future fills/account state in projection."),
            _test("final_pnl_as_projection_metric", "Final PnL", "group_contribution", "avoid", "Only allowed as group contribution context.", "Projection does not own action execution or expression choice."),
        ),
    ),
    LayerMetricContract(
        8,
        "model_08_underlying_action",
        "Underlying Action",
        ("action_plan", "policy_utility", "integrity"),
        (
            _test("target_before_stop_rate", "Target-before-stop rate", "action_plan", "primary", "Requires realistic path labels after planned entry.", "Measures price-path quality of the action thesis."),
            _test("realized_action_utility", "Realized action utility", "policy_utility", "primary", "Requires cost/slippage-adjusted action outcomes.", "Measures realized utility by action bucket."),
            _test("regret_vs_feasible_baseline", "Regret vs feasible baseline", "action_plan", "primary", "Requires feasible baseline action set.", "Compares selected action to available alternatives."),
            _test("abstention_quality", "Abstention quality", "action_plan", "primary", "Requires no-trade opportunity-cost and avoided-loss labels.", "Measures missed good trades and avoided bad trades."),
            _test("intrabar_path_leakage", "Intrabar path leakage", "integrity", "guardrail", "Requires bar/path timing rules.", "Blocks impossible target/stop ordering assumptions."),
            _test("uncosted_action_win_rate", "Uncosted action win rate", "action_plan", "avoid", "Must include costs/slippage and feasibility.", "Raw win rate can reward bad risk/reward."),
        ),
    ),
    LayerMetricContract(
        9,
        "model_05_option_expression",
        "Option Expression",
        ("option_expression", "calibrated_prediction", "integrity"),
        (
            _test("contract_selection_quality", "Contract selection quality", "option_expression", "primary", "Requires PIT option candidates and selected contract outcome labels.", "Measures selected contract quality versus feasible candidates."),
            _test("option_profit_auroc_pr_auc", "Option profit AUROC / PR-AUC", "calibrated_prediction", "primary", "Requires explicit binary probability of profitable option outcome.", "Valid only when the option score is probabilistic for a binary option label."),
            _test("premium_efficiency", "Premium efficiency", "option_expression", "primary", "Requires premium, payoff, and spread-adjusted return labels.", "Measures payoff per premium/spread risk."),
            _test("greeks_iv_liquidity_fit", "Greeks / IV / liquidity fit", "option_expression", "primary", "Requires PIT chain Greeks, IV/skew/term, NBBO, OI/volume.", "Checks expression feasibility and thesis alignment."),
            _test("option_chain_timestamp_purity", "Option chain timestamp purity", "integrity", "guardrail", "Requires chain snapshot clocks and contract availability.", "Blocks expired/survivorship or future chain leakage."),
            _test("underlying_only_pnl_as_option_score", "Underlying-only PnL", "option_expression", "avoid", "Only valid as comparison context.", "Option layer must be judged on option expression outcomes and feasibility."),
        ),
    ),
    LayerMetricContract(
        10,
        "model_06_residual_event_governance",
        "Event Risk Governor",
        ("event_attribution", "policy_utility", "integrity"),
        (
            _test("residual_event_attribution_accuracy", "Residual event attribution accuracy", "event_attribution", "primary", "Requires post-replay event-failure attribution labels.", "Measures whether residual failures are attributed to the right event family."),
            _test("intervention_precision_recall", "Intervention precision/recall", "event_attribution", "primary", "Requires reviewed intervention/failure labels.", "Measures false block and false allow quality."),
            _test("avoided_loss_opportunity_cost", "Avoided loss / opportunity cost", "policy_utility", "primary", "Requires counterfactual and opportunity-cost accounting.", "Balances avoided losses against missed winners."),
            _test("severity_calibration", "Severity calibration", "event_attribution", "primary", "Requires severity labels or reviewed ordinal outcomes.", "Checks whether warning severity matches realized residual risk."),
            _test("post_replay_to_inference_leakage", "Post-replay leakage", "integrity", "guardrail", "Requires explicit inference-time route separation.", "Blocks replay-only evidence from entering live inference."),
            _test("causal_avoided_loss_claim", "Causal avoided-loss claim", "event_attribution", "avoid", "Requires counterfactual evidence before causality.", "Avoided loss cannot be counted as causal proof by default."),
        ),
    ),
)


MODEL_GROUP_SUPPLEMENTAL_TESTS: tuple[LayerMetricTest, ...] = (
    _test("layer_ablation", "Layer ablation", "group_contribution", "primary", "Requires replay with one layer removed/frozen.", "Measures end-to-end impact of a layer without relabeling group PnL as layer-local."),
    _test("layer_replacement_baseline", "Layer replacement baseline", "group_contribution", "primary", "Requires null, heuristic, or previous-version substitute.", "Compares each layer against a controlled baseline."),
    _test("sequential_contribution", "Sequential contribution", "group_contribution", "primary", "Requires M01->M06 incremental replay.", "Measures marginal contribution as layers are added."),
    _test("cross_layer_consistency", "Cross-layer consistency", "group_contribution", "guardrail", "Requires full decision audit trail.", "Detects contradictions such as high alpha and hard event block."),
    _test("interaction_stress", "Interaction stress", "group_contribution", "guardrail", "Requires stress windows such as earnings/Fed/halts/volatility shocks.", "Tests stack behavior in known difficult regimes."),
)


def all_layer_metric_contracts() -> tuple[LayerMetricContract, ...]:
    return LAYER_METRIC_CONTRACTS


def layer_metric_contract(layer: int) -> LayerMetricContract:
    for contract in LAYER_METRIC_CONTRACTS:
        if contract.layer == layer:
            return contract
    raise KeyError(f"unknown layer metric contract: {layer}")


def layer_metric_contract_payload() -> dict[str, Any]:
    return {
        "metric_family_descriptions": dict(METRIC_FAMILY_DESCRIPTIONS),
        "layers": [contract.as_dict() for contract in LAYER_METRIC_CONTRACTS],
        "model_group_supplemental_tests": [test.as_dict() for test in MODEL_GROUP_SUPPLEMENTAL_TESTS],
    }
