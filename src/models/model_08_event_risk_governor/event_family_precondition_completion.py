"""Complete event-family precondition packets before final association judgment.

This module fills the governance/evidence-design gaps for every fine-grained
EventRiskGovernor family without claiming empirical association. It converts the
batch catalog into maintained scouting packets that define source precedence,
point-in-time clocks, baselines, controls, label windows, residual/liquidity
requirements, and early-stop gates.

It performs no provider calls, model training, activation, broker/account
mutation, SQL mutation, artifact deletion, or final alpha/risk promotion.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, TextIO

CONTRACT_TYPE = "event_family_precondition_completion_v1"
PACKET_CONTRACT_TYPE = "event_family_scouting_packet_v1"
SUMMARY_CONTRACT_TYPE = "event_family_precondition_completion_summary_v1"
DEFAULT_CATALOG_PATH = Path("storage/event_family_batch_catalog_20260516/event_family_batch_catalog.json")
DEFAULT_CLOSEOUT_PATH = Path("storage/event_family_remaining_closeout_20260516/event_family_remaining_closeout.json")
DEFAULT_OUTPUT_DIR = Path("storage/event_family_precondition_completion_20260516")

EXPECTATION_BASELINE_FAMILIES = {
    "earnings_guidance_result_metrics",
    "earnings_guidance_raise_cut_or_withdrawal",
    "nfp_employment_release",
}
RESIDUAL_DEFINITION_FAMILIES = {
    "price_action_pattern",
    "residual_market_structure_disturbance",
    "treasury_yield_curve_shock",
}
LIQUIDITY_EVIDENCE_FAMILIES = {"microstructure_liquidity_disruption"}
TEMPORARY_EVIDENCE_FAMILIES = {"cpi_inflation_release"}
DEFERRED_LOW_SIGNAL_FAMILIES = {"option_derivatives_abnormality"}
RISK_ONLY_CURRENT_EVIDENCE_FAMILIES = {"earnings_guidance_scheduled_shell", "cpi_inflation_release"}

DEFAULT_LABEL_WINDOWS = ("event_day", "h1", "h5", "h10")
DEFAULT_PRICE_LABELS = (
    "forward_return",
    "absolute_forward_return",
    "path_range",
    "maximum_favorable_excursion",
    "maximum_adverse_excursion",
    "gap_return_when_applicable",
)
SAFETY_STATEMENT = (
    "Packet completion is governance/evidence design only: no provider calls, no training, no model activation, "
    "no broker/account mutation, no SQL destructive action, and no artifact deletion."
)


@dataclass(frozen=True)
class EventFamilyPreconditionPacket:
    contract_type: str
    family_key: str
    routing_bucket: str
    mechanism_group: str
    priority: str
    packet_status: str
    mechanism_question: str
    accepted_current_use: str
    blocked_use: str
    canonical_source_precedence: tuple[str, ...]
    point_in_time_clock_rules: tuple[str, ...]
    event_identity_fields: tuple[str, ...]
    event_measure_fields: tuple[str, ...]
    inclusion_rules: tuple[str, ...]
    exclusion_rules: tuple[str, ...]
    baseline_requirements: tuple[str, ...]
    matched_control_design: tuple[str, ...]
    label_windows: tuple[str, ...]
    required_price_path_labels: tuple[str, ...]
    residual_definition: str
    liquidity_evidence_requirement: str
    early_stop_rules: tuple[str, ...]
    remaining_blocker_codes: tuple[str, ...]
    next_empirical_action: str
    final_judgment_status: str
    safety_statement: str = SAFETY_STATEMENT

    def to_row(self) -> dict[str, Any]:
        return asdict(self)

    def csv_row(self) -> dict[str, str]:
        row = self.to_row()
        return {key: ";".join(value) if isinstance(value, tuple) else str(value) for key, value in row.items()}


@dataclass(frozen=True)
class EventFamilyPreconditionCompletion:
    contract_type: str
    generated_at_utc: str
    source_catalog_path: str
    source_closeout_path: str
    packets: tuple[EventFamilyPreconditionPacket, ...]
    provider_calls: int = 0
    model_training_performed: bool = False
    model_activation_performed: bool = False
    broker_execution_performed: bool = False
    account_mutation_performed: bool = False
    sql_destructive_mutation_performed: bool = False
    artifact_deletion_performed: bool = False

    @property
    def summary(self) -> dict[str, Any]:
        return {
            "contract_type": SUMMARY_CONTRACT_TYPE,
            "generated_at_utc": self.generated_at_utc,
            "family_count": len(self.packets),
            "packet_status_counts": _counts(packet.packet_status for packet in self.packets),
            "final_judgment_status_counts": _counts(packet.final_judgment_status for packet in self.packets),
            "remaining_blocker_counts": _counts(blocker for packet in self.packets for blocker in packet.remaining_blocker_codes),
            "risk_only_current_evidence_family_keys": [
                packet.family_key for packet in self.packets if packet.family_key in RISK_ONLY_CURRENT_EVIDENCE_FAMILIES
            ],
            "deferred_low_signal_family_keys": [
                packet.family_key for packet in self.packets if packet.family_key in DEFERRED_LOW_SIGNAL_FAMILIES
            ],
            "expectation_baseline_family_keys": [
                packet.family_key for packet in self.packets if "pit_expectation_or_comparable_baseline_required" in packet.remaining_blocker_codes
            ],
            "residual_definition_family_keys": [
                packet.family_key for packet in self.packets if "residual_over_base_state_required" in packet.remaining_blocker_codes
            ],
            "liquidity_evidence_family_keys": [
                packet.family_key for packet in self.packets if "liquidity_depth_evidence_required" in packet.remaining_blocker_codes
            ],
            "provider_calls": self.provider_calls,
            "model_training_performed": self.model_training_performed,
            "model_activation_performed": self.model_activation_performed,
            "broker_execution_performed": self.broker_execution_performed,
            "account_mutation_performed": self.account_mutation_performed,
            "sql_destructive_mutation_performed": self.sql_destructive_mutation_performed,
            "artifact_deletion_performed": self.artifact_deletion_performed,
            "final_conclusion": "withheld_until_all_required_empirical_association_studies_exist",
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_type": self.contract_type,
            "generated_at_utc": self.generated_at_utc,
            "source_catalog_path": self.source_catalog_path,
            "source_closeout_path": self.source_closeout_path,
            "packets": [packet.to_row() for packet in self.packets],
            "summary": self.summary,
            "provider_calls": self.provider_calls,
            "model_training_performed": self.model_training_performed,
            "model_activation_performed": self.model_activation_performed,
            "broker_execution_performed": self.broker_execution_performed,
            "account_mutation_performed": self.account_mutation_performed,
            "sql_destructive_mutation_performed": self.sql_destructive_mutation_performed,
            "artifact_deletion_performed": self.artifact_deletion_performed,
        }


def _counts(values: Iterable[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return tuple(part for part in value.split(";") if part)
    if isinstance(value, Sequence):
        return tuple(str(item) for item in value if str(item))
    return (str(value),)


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    out: list[str] = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return tuple(out)


def _read_catalog(path: Path) -> list[dict[str, Any]]:
    return [dict(item) for item in _read_json(path).get("candidates", [])]


def _read_closeout(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    return {str(row.get("family_key") or ""): dict(row) for row in _read_json(path).get("family_rows", [])}


def _source_precedence(spec: Mapping[str, Any]) -> tuple[str, ...]:
    family = str(spec.get("family_key") or "")
    routing = str(spec.get("routing_bucket") or "")
    mechanism = str(spec.get("mechanism_group") or "")
    if family == "cpi_inflation_release":
        return (
            "Trading Economics CPI rows with actual and consensus; canonical surprise = actual - consensus.",
            "Trading Economics CPI rows with actual and te_forecast when consensus is unavailable; fallback surprise = actual - te_forecast.",
            "Official CPI release identity/timestamp cross-check; FRED/BLS series may validate realized values but cannot replace PIT expectation fields.",
            "Temporary public-history diagnostics may remain supporting evidence until the fuller TE expectation-history route is complete.",
        )
    if family.startswith("earnings_guidance") or routing == "earnings_guidance":
        return (
            "Official company earnings release, SEC furnished exhibit, or company IR document with captured release time.",
            "Persisted pre-event expectation baseline artifact with captured_at/as_of_time and no post-event actual/surprise fields.",
            "Official transcript or call materials only after source timestamp is known and comparable current/prior guidance fields are review-accepted.",
            "Derivative news may be coverage context only, not canonical event identity or surprise baseline.",
        )
    if routing == "sec_filing":
        return (
            "Official SEC filing or exhibit with accession/document timestamp.",
            "Company IR or exchange/regulator primary source when SEC is not the canonical disclosure surface.",
            "Tier-1 news only as discovery/coverage; official source remains canonical when available.",
            "Derivative news/social summaries cannot establish event identity without source review.",
        )
    if routing in {"macro_data", "macro_news"} or mechanism.startswith("macro"):
        return (
            "Official agency/central-bank/regulator release or accepted primary economic-calendar provider with PIT actual/consensus/forecast fields.",
            "Market-implied expectation route when the family is a policy/rates repricing event.",
            "News/GDELT rows are discovery/coverage only until reconciled to the primary release clock.",
        )
    if routing == "sector_news":
        return (
            "Official regulator/government/industry-primary document when available.",
            "Mapped sector/industry source with affected-universe evidence.",
            "GDELT/news may propose candidates but must not define scope without source-quality and readthrough review.",
        )
    if routing in {"price_action", "equity_abnormal_activity", "option_abnormal_activity"}:
        return (
            "Timestamped market/option/microstructure data that directly defines the abnormality.",
            "Matched market/sector/target-state controls from already accepted model state artifacts.",
            "News proximity may explain or stratify risk but cannot retroactively define the abnormality as alpha.",
        )
    return (
        "Primary official source where available.",
        "Timestamped reputable news/source feed as discovery with canonical-source reconciliation.",
        "Derivative coverage only as supporting context after source precedence review.",
    )


def _clock_rules(spec: Mapping[str, Any]) -> tuple[str, ...]:
    routing = str(spec.get("routing_bucket") or "")
    family = str(spec.get("family_key") or "")
    rules = [
        "Preserve event_time_utc and event_time_et separately; do not infer market-session bucket from date alone.",
        "Record source_published_at, source_captured_at, and accepted_as_of_time when available.",
        "Assign premarket/regular/postmarket/closed-session bucket before label-window construction.",
    ]
    if family == "cpi_inflation_release":
        rules.append("Use official macro release timestamp; surprise fields must be point-in-time expectation values known before release.")
    if family in EXPECTATION_BASELINE_FAMILIES or routing == "earnings_guidance":
        rules.append("Expectation/comparable baseline must have captured_at/as_of_time earlier than the release/event clock.")
    if routing in {"price_action", "equity_abnormal_activity", "option_abnormal_activity"}:
        rules.append("Use the abnormality detection window start/end as the event clock and keep later outcome labels disjoint.")
    return tuple(rules)


def _identity_fields(spec: Mapping[str, Any]) -> tuple[str, ...]:
    scopes = set(_as_tuple(spec.get("scope_types")))
    fields = ["event_family", "event_id", "event_time_utc", "event_time_et", "source_ref", "source_priority"]
    if "symbol" in scopes:
        fields.extend(["symbol", "issuer_or_target_entity"])
    if "sector" in scopes:
        fields.extend(["sector_id", "affected_universe_ref"])
    if "macro" in scopes:
        fields.extend(["country_or_region", "macro_series_or_policy_body"])
    return tuple(fields)


def _measure_fields(spec: Mapping[str, Any]) -> tuple[str, ...]:
    family = str(spec.get("family_key") or "")
    mechanism = str(spec.get("mechanism_group") or "")
    if family == "cpi_inflation_release":
        return ("actual", "consensus", "te_forecast", "previous", "revision", "surprise", "surprise_abs", "metric_name")
    if family == "fomc_rates_policy":
        return ("decision_rate", "expected_rate", "rate_surprise", "statement_shift", "dot_plot_shift", "press_conference_shift")
    if family == "nfp_employment_release":
        return ("payroll_actual", "payroll_consensus", "payroll_surprise", "unemployment_rate", "wage_growth", "revision")
    if mechanism == "capital_structure":
        return ("security_type", "offering_size", "dilution_proxy", "discount", "use_of_proceeds", "balance_sheet_stress")
    if mechanism == "corporate_action":
        return ("deal_type", "consideration_type", "premium", "deal_value", "regulatory_risk", "termination_or_resolution_status")
    if mechanism in {"legal_regulatory", "distress"}:
        return ("severity_tier", "official_status", "review_required", "estimated_scope", "resolution_stage")
    if mechanism == "product_customer":
        return ("materiality_tier", "counterparty", "revenue_or_unit_scope", "one_time_or_recurring", "credibility_tier")
    if mechanism.startswith("macro"):
        return ("severity_tier", "affected_market", "surprise_or_residual", "uncertainty_tier", "scope_tier")
    if mechanism == "abnormal_activity":
        return ("abnormality_type", "window_start", "window_end", "residual_score", "volume_or_depth_score", "direction_hypothesis")
    return ("event_subtype", "materiality_tier", "severity_tier", "scope_tier", "source_quality_tier")


def _baseline_requirements(spec: Mapping[str, Any]) -> tuple[str, ...]:
    family = str(spec.get("family_key") or "")
    routing = str(spec.get("routing_bucket") or "")
    mechanism = str(spec.get("mechanism_group") or "")
    if family == "cpi_inflation_release":
        return (
            "PIT consensus/forecast is required for surprise; TE actual-consensus is canonical when populated, TE actual-te_forecast is fallback.",
            "Realized CPI/FRED/BLS values alone are insufficient for abnormal-surprise classification.",
            "Controls must include market regime, rates-sensitive sector context, and matched non-release dates.",
        )
    if family == "earnings_guidance_scheduled_shell":
        return (
            "Scheduled-shell study may use known earnings-calendar timing, but signed result/guidance claims require separate result and expectation baselines.",
            "Controls must exclude nearby earnings windows for the same symbol and comparable sector/market state.",
        )
    if family == "earnings_guidance_result_metrics":
        return (
            "Persisted pre-event EPS and revenue consensus baselines are required before beat/miss labels.",
            "Actual result fields captured after release may not be reused as expectation baselines.",
            "Comparable fiscal period identity and source timestamp are mandatory.",
        )
    if family == "earnings_guidance_raise_cut_or_withdrawal":
        return (
            "Prior company guidance baseline and current comparable company guidance are both required.",
            "Guidance-consensus or revenue-consensus baseline is required before surprise/raise/cut claims.",
            "Narrative-only spans are context until mapped to comparable numeric or categorical guidance dimensions.",
        )
    if family == "nfp_employment_release":
        return (
            "PIT payroll/unemployment/wage consensus and revision fields are required.",
            "Official release time and revision treatment must be frozen before labels are generated.",
        )
    if family == "fomc_rates_policy":
        return (
            "Market-implied expected policy path before announcement is required for surprise/residual classification.",
            "Scheduled decision, statement, minutes, dots, and press conference must be separate subevents/clocks.",
        )
    if family == "treasury_yield_curve_shock":
        return (
            "Base rates/curve state must be computed before residual shock labels.",
            "Shock is the unexplained move over accepted Layer 1/2 rates/market context, not raw yield movement alone.",
        )
    if mechanism in {"capital_structure", "capital_allocation", "corporate_action", "ownership_governance"}:
        return (
            "Matched controls must use same symbol or comparable sector/market-state dates without same-family events.",
            "Materiality threshold and source-quality tier must be defined before association measurement.",
        )
    if mechanism in {"legal_regulatory", "distress"}:
        return (
            "Severity ladder and official-vs-allegation status must be assigned before outcome grouping.",
            "Controls must exclude overlapping crisis/legal events and preserve human-review-required flags.",
        )
    if routing in {"symbol_news", "sector_news"}:
        return (
            "News candidate must be decomposed into this mechanism family with source quality and materiality review.",
            "Controls must match sector/market/target state and exclude overlapping canonical events.",
        )
    if routing in {"price_action", "equity_abnormal_activity", "option_abnormal_activity"}:
        return (
            "Residual or abnormality score must be computed before event assignment.",
            "Controls must match pre-event volatility, liquidity, trend, market, sector, and target-state context.",
        )
    return ("Mechanism-specific matched controls and source-quality/materiality baselines are required before association claims.",)


def _matched_controls(spec: Mapping[str, Any]) -> tuple[str, ...]:
    family = str(spec.get("family_key") or "")
    routing = str(spec.get("routing_bucket") or "")
    controls = [
        "Match by market regime, sector context, target state, pre-event volatility, trend, and liquidity where applicable.",
        "Exclude windows with same-family events, major overlapping canonical events, and unavailable price labels.",
        "Report event-vs-control deltas for return, absolute return, path range, MFE, and MAE across 1/5/10-day windows.",
    ]
    if family == "cpi_inflation_release":
        controls.append("Use non-release macro-control dates and rates-sensitive ETF/sector cohorts; stratify by hot/cool and surprise magnitude.")
    if routing == "earnings_guidance":
        controls.append("Use same-symbol non-earnings dates plus sector/market controls; signed tests must wait for accepted result/guidance labels.")
    if routing in {"price_action", "equity_abnormal_activity", "option_abnormal_activity"}:
        controls.append("Use pre-event state-matched abnormality-negative windows to prove incremental residual signal.")
    return tuple(controls)


def _residual_definition(spec: Mapping[str, Any]) -> str:
    family = str(spec.get("family_key") or "")
    if family in {"price_action_pattern", "residual_market_structure_disturbance"}:
        return (
            "Required before study: residual = observed price/market-structure behavior minus expected behavior from accepted "
            "Layer 1 market context, Layer 2 sector context, Layer 3 target state, pre-event volatility/trend, and liquidity controls."
        )
    if family == "treasury_yield_curve_shock":
        return "Required before study: residual rates shock = yield/curve movement unexplained by accepted base rates/market-state context."
    if family == "option_derivatives_abnormality":
        return "Existing residual/abnormality definition failed current matched controls; revise abnormality standard before retesting."
    return "No special residual definition beyond matched controls unless empirical review finds base-state leakage."


def _liquidity_requirement(spec: Mapping[str, Any]) -> str:
    family = str(spec.get("family_key") or "")
    routing = str(spec.get("routing_bucket") or "")
    if family == "microstructure_liquidity_disruption":
        return (
            "Required before study: bid/ask spread, quote depth, trade imbalance, halt/limit-state, slippage proxy, and execution-quality labels. "
            "Directional return labels are secondary to execution-risk/path-risk labels."
        )
    if routing in {"price_action", "equity_abnormal_activity", "option_abnormal_activity"}:
        return "Use liquidity/spread/depth controls to prevent abnormal-activity labels from being ordinary illiquidity artifacts."
    return "Use ordinary volume/liquidity controls; no dedicated depth evidence required at packet stage."


def _remaining_blockers(spec: Mapping[str, Any]) -> tuple[str, ...]:
    family = str(spec.get("family_key") or "")
    blockers = [blocker for blocker in _as_tuple(spec.get("blocker_codes")) if blocker != "missing_family_packet"]
    blockers.append("empirical_association_study_required")
    if family in EXPECTATION_BASELINE_FAMILIES:
        blockers.append("pit_expectation_or_comparable_baseline_required")
    if family == "cpi_inflation_release":
        blockers.append("fuller_te_expectation_history_required")
    if family in RESIDUAL_DEFINITION_FAMILIES:
        blockers.append("residual_over_base_state_required")
    if family in LIQUIDITY_EVIDENCE_FAMILIES:
        blockers.append("liquidity_depth_evidence_required")
    if family in DEFERRED_LOW_SIGNAL_FAMILIES:
        blockers.append("revised_abnormality_definition_required")
    return _dedupe(blockers)


def _packet_status(family: str) -> str:
    if family in DEFERRED_LOW_SIGNAL_FAMILIES:
        return "packet_spec_completed_deferred_low_signal_current_definition"
    if family in RISK_ONLY_CURRENT_EVIDENCE_FAMILIES:
        return "packet_spec_completed_current_risk_only_evidence"
    return "packet_spec_completed_pending_empirical_evidence"


def _final_judgment_status(family: str) -> str:
    if family in DEFERRED_LOW_SIGNAL_FAMILIES:
        return "final_alpha_judgment_withheld_current_definition_low_signal"
    return "final_judgment_withheld_until_empirical_association_complete"


def _next_action(spec: Mapping[str, Any], blockers: tuple[str, ...]) -> str:
    family = str(spec.get("family_key") or "")
    if "pit_expectation_or_comparable_baseline_required" in blockers:
        return "Build or acquire PIT expectation/comparable baseline, then run family-specific association study."
    if "fuller_te_expectation_history_required" in blockers:
        return "Complete fuller TE expectation-history route, then rerun CPI surprise association with canonical TE rows."
    if "residual_over_base_state_required" in blockers:
        return "Implement residual-over-base-state detector and controls before event labels are accepted."
    if "liquidity_depth_evidence_required" in blockers:
        return "Build liquidity/depth/execution-risk evidence route before price association."
    if family in DEFERRED_LOW_SIGNAL_FAMILIES:
        return "Revise abnormality definition before spending more empirical-study cycles."
    return str(spec.get("next_action") or "Run family-specific source extraction, matched controls, and association scout.")


def _packet_from_spec(spec: Mapping[str, Any]) -> EventFamilyPreconditionPacket:
    family = str(spec.get("family_key") or "")
    blockers = _remaining_blockers(spec)
    return EventFamilyPreconditionPacket(
        contract_type=PACKET_CONTRACT_TYPE,
        family_key=family,
        routing_bucket=str(spec.get("routing_bucket") or ""),
        mechanism_group=str(spec.get("mechanism_group") or ""),
        priority=str(spec.get("priority") or ""),
        packet_status=_packet_status(family),
        mechanism_question=str(spec.get("association_question") or ""),
        accepted_current_use=str(spec.get("accepted_current_use") or ""),
        blocked_use=str(spec.get("blocked_use") or ""),
        canonical_source_precedence=_source_precedence(spec),
        point_in_time_clock_rules=_clock_rules(spec),
        event_identity_fields=_identity_fields(spec),
        event_measure_fields=_measure_fields(spec),
        inclusion_rules=(
            "Include only events matching the mechanism question and source-precedence rules.",
            "Require deterministic event identity, event clock, source reference, and source-quality tier.",
            "Allow family-specific subtypes only when they preserve one coherent mechanism.",
        ),
        exclusion_rules=(
            "Exclude broad routing buckets, generic news sentiment, duplicate coverage, and derivative summaries as primary events.",
            "Exclude events without point-in-time clocks or without enough data for matched controls.",
            "Exclude overlapping canonical events unless the study explicitly models interaction after independent family evidence exists.",
        ),
        baseline_requirements=_baseline_requirements(spec),
        matched_control_design=_matched_controls(spec),
        label_windows=DEFAULT_LABEL_WINDOWS,
        required_price_path_labels=DEFAULT_PRICE_LABELS,
        residual_definition=_residual_definition(spec),
        liquidity_evidence_requirement=_liquidity_requirement(spec),
        early_stop_rules=(
            "Stop before alpha/risk promotion if sample coverage is underpowered, direction flips across windows, or controls are missing.",
            "Stop before directional claims if only path-range/absolute-return relationship is stable.",
            "Stop before training if source precedence, PIT clock, or baseline requirements are unmet.",
        ),
        remaining_blocker_codes=blockers,
        next_empirical_action=_next_action(spec, blockers),
        final_judgment_status=_final_judgment_status(family),
    )


def build_event_family_precondition_completion(
    *,
    catalog_path: Path = DEFAULT_CATALOG_PATH,
    closeout_path: Path = DEFAULT_CLOSEOUT_PATH,
    generated_at_utc: str | None = None,
) -> EventFamilyPreconditionCompletion:
    generated = generated_at_utc or datetime.now(UTC).isoformat()
    closeout = _read_closeout(closeout_path)
    packets: list[EventFamilyPreconditionPacket] = []
    for spec in _read_catalog(catalog_path):
        family = str(spec.get("family_key") or "")
        merged = dict(spec)
        if family in closeout:
            # Closeout supplies the latest accepted use/blocker framing, while the catalog
            # supplies the association question and original mechanism metadata.
            merged["accepted_current_use"] = closeout[family].get("accepted_current_use", merged.get("accepted_current_use"))
            merged["blocked_use"] = closeout[family].get("blocked_use", merged.get("blocked_use"))
            merged["blocker_codes"] = _dedupe((*_as_tuple(merged.get("blocker_codes")), *_as_tuple(closeout[family].get("blocker_codes"))))
        packets.append(_packet_from_spec(merged))
    return EventFamilyPreconditionCompletion(
        contract_type=CONTRACT_TYPE,
        generated_at_utc=generated,
        source_catalog_path=str(catalog_path),
        source_closeout_path=str(closeout_path),
        packets=tuple(packets),
    )


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], *, fieldnames: Sequence[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(fieldnames or sorted({key for row in rows for key in row.keys()}))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_precondition_artifacts(completion: EventFamilyPreconditionCompletion, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "event_family_precondition_completion.json").write_text(
        json.dumps(completion.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "event_family_precondition_completion_summary.json").write_text(
        json.dumps(completion.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (output_dir / "event_family_scouting_packets.jsonl").open("w", encoding="utf-8") as handle:
        for packet in completion.packets:
            handle.write(json.dumps(packet.to_row(), sort_keys=True) + "\n")
    fields = list(
        EventFamilyPreconditionPacket(
            "", "", "", "", "", "", "", "", "", (), (), (), (), (), (), (), (), (), (), "", "", (), (), "", ""
        ).csv_row().keys()
    )
    _write_csv(output_dir / "event_family_scouting_packets.csv", [packet.csv_row() for packet in completion.packets], fieldnames=fields)
    requirement_fields = [
        "family_key",
        "priority",
        "packet_status",
        "remaining_blocker_codes",
        "baseline_requirements",
        "residual_definition",
        "liquidity_evidence_requirement",
        "next_empirical_action",
        "final_judgment_status",
    ]
    _write_csv(
        output_dir / "event_family_evidence_requirements.csv",
        [{field: packet.csv_row()[field] for field in requirement_fields} for packet in completion.packets],
        fieldnames=requirement_fields,
    )
    (output_dir / "README.md").write_text(
        f"""# Event-family precondition completion

Contract: `{completion.contract_type}`

This artifact fills the precondition packet surface for all {len(completion.packets)} fine-grained EventRiskGovernor families before any final association conclusion.

It defines source precedence, point-in-time clock rules, event identity/measure fields, baseline requirements, matched controls, price/path labels, residual requirements, liquidity requirements, and early-stop gates.

It does **not** claim empirical association, train, promote, activate, call providers, mutate broker/account state, run destructive SQL, or delete artifacts.

Final conclusion status: `{completion.summary['final_conclusion']}`.
""",
        encoding="utf-8",
    )


def write_completion(completion: EventFamilyPreconditionCompletion, *, output: TextIO) -> None:
    json.dump(completion.to_dict(), output, indent=2, sort_keys=True)
    output.write("\n")


__all__ = [
    "EventFamilyPreconditionPacket",
    "EventFamilyPreconditionCompletion",
    "build_event_family_precondition_completion",
    "write_completion",
    "write_precondition_artifacts",
]
