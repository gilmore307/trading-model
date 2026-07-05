"""Model-local evaluation metric contracts for the current five-model stack.

The contract is about metric eligibility, not metric values. A model may report
a metric only when its label and point-in-time evidence satisfy the relevant
family requirements. This prevents group-level replay metrics from being
relabeled as model-local evidence.
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
    "event_state": "Event-state recall, attribution, timing, and impact-channel quality.",
    "decision_utility": "Unified decision utility, abstention, risk, and action-thesis quality.",
    "option_expression": "Option contract/expression fit, feasibility, and payoff quality.",
    "event_attribution": "Residual event-risk recall, component-control evidence, and opportunity-cost quality.",
    "integrity": "Point-in-time, leakage, lineage, and feasibility guardrails.",
    "group_contribution": "Ablation/counterfactual contribution tests owned by the model group.",
}


def _test(metric_id: str, label: str, family: str, role: MetricRole, eligibility: str, note: str) -> LayerMetricTest:
    return LayerMetricTest(metric_id=metric_id, label=label, family=family, role=role, eligibility=eligibility, note=note)


LAYER_METRIC_CONTRACTS: tuple[LayerMetricContract, ...] = (
    LayerMetricContract(
        1,
        "background_context_model",
        "Background Context",
        ("representation_context", "integrity", "group_contribution"),
        (
            _test("background_context_coverage", "Context coverage", "representation_context", "primary", "Requires point-in-time market and broad context rows.", "Measures whether M01 covers the fold without unexplained gaps."),
            _test("market_state_stability", "Market-state stability", "representation_context", "primary", "Requires ordered background context outputs.", "Penalizes unstable state flips near fold boundaries."),
            _test("macro_revision_leakage", "Macro/revision leakage", "integrity", "guardrail", "Requires source release clocks and revision timestamps.", "Blocks use of revised or future macro values as inference features."),
            _test("trade_pnl_as_background_score", "Direct trade PnL", "group_contribution", "avoid", "Only allowed as model-group context.", "A background context model does not own final trade outcomes."),
        ),
    ),
    LayerMetricContract(
        2,
        "target_state_model",
        "Target State",
        ("representation_context", "integrity", "group_contribution"),
        (
            _test("target_state_completeness", "Target-state completeness", "representation_context", "primary", "Requires target-state rows and expected block schema.", "Measures coverage, missingness, and block-level completeness."),
            _test("state_quantile_separation", "Future-outcome quantile separation", "representation_context", "primary", "Requires future labels kept outside inference features.", "Checks whether state buckets separate future tradability/path outcomes."),
            _test("target_identity_leakage", "Target identity leakage", "integrity", "guardrail", "Requires anonymous target candidate and split evidence.", "Blocks target/company identity leakage into model-facing fitting vectors."),
            _test("single_auroc_for_target_state", "Single target-state AUROC", "representation_context", "avoid", "Only allowed for an explicit binary probability head.", "A representation is not one binary classifier."),
        ),
    ),
    LayerMetricContract(
        3,
        "event_state_model",
        "Event State",
        ("event_state", "integrity", "group_contribution"),
        (
            _test("event_visibility_recall", "Event visibility recall", "event_state", "primary", "Requires PIT event visibility and realized event labels.", "Measures whether relevant events are visible before decisions."),
            _test("impact_channel_calibration", "Impact-channel calibration", "event_state", "primary", "Requires reviewed event channel labels.", "Checks whether underlying, option, volatility, liquidity, and gamma-flow channels are calibrated."),
            _test("distribution_effect_channel_calibration", "Distribution-effect calibration", "event_state", "primary", "Requires reviewed event-family effect-profile masks and channel labels.", "Checks whether mean/mode/contribution, variance, tail, skew, confidence, and gate channels are calibrated only where the family profile allows them."),
            _test("post_event_article_leakage", "Post-event article leakage", "integrity", "guardrail", "Requires article/source timestamps.", "Blocks using later coverage to score pre-decision event state."),
            _test("standalone_event_alpha", "Standalone event alpha", "event_state", "avoid", "Only allowed as separate research after acceptance.", "M03 describes event state; it does not own a standalone event-alpha route."),
        ),
    ),
    LayerMetricContract(
        4,
        "unified_decision_model",
        "Unified Decision",
        ("decision_utility", "integrity", "group_contribution"),
        (
            _test("realized_decision_utility", "Realized decision utility", "decision_utility", "primary", "Requires cost/slippage-adjusted decision outcomes.", "Measures realized utility by M04 action bucket."),
            _test("abstention_quality", "Abstention quality", "decision_utility", "primary", "Requires no-trade opportunity-cost and avoided-loss labels.", "Measures missed good trades and avoided bad trades."),
            _test("target_allocation_calibration", "Target-allocation calibration", "decision_utility", "primary", "Requires realized outcomes and M04 target-allocation fractions.", "Checks whether larger target allocation fractions are justified by outcomes."),
            _test("future_path_leakage", "Future path leakage", "integrity", "guardrail", "Requires bar/path timing rules.", "Blocks impossible target/stop ordering assumptions."),
            _test("uncosted_action_win_rate", "Uncosted action win rate", "decision_utility", "avoid", "Must include costs/slippage and feasibility.", "Raw win rate can reward bad risk/reward."),
        ),
    ),
    LayerMetricContract(
        5,
        "option_expression_model",
        "Option Expression",
        ("option_expression", "integrity", "group_contribution"),
        (
            _test("contract_selection_quality", "Contract selection quality", "option_expression", "primary", "Requires PIT option candidates and selected contract outcome labels.", "Measures selected contract quality versus feasible candidates."),
            _test("premium_efficiency", "Premium efficiency", "option_expression", "primary", "Requires premium, payoff, and spread-adjusted return labels.", "Measures payoff per premium/spread risk."),
            _test("greeks_iv_liquidity_fit", "Greeks / IV / liquidity fit", "option_expression", "primary", "Requires PIT chain Greeks, IV/skew/term, NBBO, OI/volume.", "Checks expression feasibility and thesis alignment."),
            _test("option_chain_timestamp_purity", "Option chain timestamp purity", "integrity", "guardrail", "Requires chain snapshot clocks and contract availability.", "Blocks expired/survivorship or future chain leakage."),
            _test("underlying_only_pnl_as_option_score", "Underlying-only PnL", "option_expression", "avoid", "Only valid as comparison context.", "M05 must be judged on option expression outcomes and feasibility."),
        ),
    ),
)


MODEL_GROUP_SUPPLEMENTAL_TESTS: tuple[LayerMetricTest, ...] = (
    _test("model_ablation", "Model ablation", "group_contribution", "primary", "Requires replay with one model removed/frozen.", "Measures end-to-end impact of a model without relabeling group PnL as model-local."),
    _test("model_replacement_baseline", "Model replacement baseline", "group_contribution", "primary", "Requires null, heuristic, or previous-version substitute.", "Compares each model against a controlled baseline."),
    _test("sequential_contribution", "Sequential contribution", "group_contribution", "primary", "Requires M01->M05 incremental replay.", "Measures marginal contribution as models are added."),
    _test("cross_model_consistency", "Cross-model consistency", "group_contribution", "guardrail", "Requires full decision audit trail.", "Detects contradictions across M01-M05 probability surfaces."),
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
