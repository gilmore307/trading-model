"""Fine-grained event-family batch catalog for EventRiskGovernor association work.

This module builds a non-mutating batch catalog of candidate event families that
must each receive independent price/path association analysis before model use.
It performs no provider calls, model activation, broker/account mutation, or
artifact deletion.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, TextIO
import csv
import json

CONTRACT_TYPE = "event_family_batch_catalog_v1"
SUMMARY_CONTRACT_TYPE = "event_family_batch_summary_v1"
DEFAULT_OUTPUT_DIR = Path("storage/event_family_batch_catalog_20260516")


@dataclass(frozen=True)
class EventFamilyCandidate:
    family_key: str
    routing_bucket: str
    mechanism_group: str
    association_question: str
    scope_types: tuple[str, ...]
    priority: str
    family_status: str
    association_status: str
    accepted_current_use: str
    blocked_use: str
    blocker_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    next_action: str

    def to_row(self) -> dict[str, Any]:
        row = asdict(self)
        row["scope_types"] = list(self.scope_types)
        row["blocker_codes"] = list(self.blocker_codes)
        row["evidence_refs"] = list(self.evidence_refs)
        return row

    def csv_row(self) -> dict[str, str]:
        return {
            "family_key": self.family_key,
            "routing_bucket": self.routing_bucket,
            "mechanism_group": self.mechanism_group,
            "association_question": self.association_question,
            "scope_types": ";".join(self.scope_types),
            "priority": self.priority,
            "family_status": self.family_status,
            "association_status": self.association_status,
            "accepted_current_use": self.accepted_current_use,
            "blocked_use": self.blocked_use,
            "blocker_codes": ";".join(self.blocker_codes),
            "evidence_refs": ";".join(self.evidence_refs),
            "next_action": self.next_action,
        }


@dataclass(frozen=True)
class EventFamilyBatchCatalog:
    contract_type: str
    generated_at_utc: str
    architecture_status: str
    granularity_rule: str
    candidates: tuple[EventFamilyCandidate, ...]
    source_documents: tuple[str, ...]
    provider_calls: int = 0
    model_activation_performed: bool = False
    broker_execution_performed: bool = False
    account_mutation_performed: bool = False
    artifact_deletion_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_type": self.contract_type,
            "generated_at_utc": self.generated_at_utc,
            "architecture_status": self.architecture_status,
            "granularity_rule": self.granularity_rule,
            "candidates": [candidate.to_row() for candidate in self.candidates],
            "source_documents": list(self.source_documents),
            "provider_calls": self.provider_calls,
            "model_activation_performed": self.model_activation_performed,
            "broker_execution_performed": self.broker_execution_performed,
            "account_mutation_performed": self.account_mutation_performed,
            "artifact_deletion_performed": self.artifact_deletion_performed,
        }

    @property
    def summary(self) -> dict[str, Any]:
        return {
            "contract_type": SUMMARY_CONTRACT_TYPE,
            "generated_at_utc": self.generated_at_utc,
            "candidate_count": len(self.candidates),
            "priority_counts": _counts(candidate.priority for candidate in self.candidates),
            "routing_bucket_counts": _counts(candidate.routing_bucket for candidate in self.candidates),
            "family_status_counts": _counts(candidate.family_status for candidate in self.candidates),
            "association_status_counts": _counts(candidate.association_status for candidate in self.candidates),
            "high_priority_family_keys": [candidate.family_key for candidate in self.candidates if candidate.priority == "high"],
            "provider_calls": self.provider_calls,
            "model_activation_performed": self.model_activation_performed,
            "broker_execution_performed": self.broker_execution_performed,
            "account_mutation_performed": self.account_mutation_performed,
            "artifact_deletion_performed": self.artifact_deletion_performed,
        }


@dataclass(frozen=True)
class _FamilySpec:
    family_key: str
    routing_bucket: str
    mechanism_group: str
    association_question: str
    scope_types: tuple[str, ...]
    priority: str
    default_status: str
    default_association_status: str
    accepted_current_use: str
    blocked_use: str
    blocker_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    next_action: str


def _counts(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


FAMILY_SPECS: tuple[_FamilySpec, ...] = (
    _FamilySpec(
        "earnings_guidance_scheduled_shell",
        "earnings_guidance",
        "earnings_guidance",
        "Do scheduled earnings shells predict direction-neutral path expansion, volatility, liquidity stress, or directional drift after controlling for market/sector/target state?",
        ("symbol", "sector"),
        "high",
        "scouting",
        "direction_neutral_path_signal_observed_underpowered",
        "event_risk_context_and_scheduled_catalyst_risk",
        "signed_alpha_or_stronger_intervention",
        ("coverage_underpowered", "needs_more_seasons_symbols"),
        (
            "docs/101_earnings_guidance_event_family_packet.md",
            "storage/earnings_guidance_event_alone_q4_2025_20260515/report.json",
        ),
        "Expand shell study across more seasons/symbols and rerun matched controls with market/sector/target-state adjustments.",
    ),
    _FamilySpec(
        "earnings_guidance_result_metrics",
        "earnings_guidance",
        "earnings_guidance",
        "Do official result metrics after release visibility explain price/path outcomes beyond the scheduled shell?",
        ("symbol", "sector"),
        "high",
        "scouting",
        "partial_result_context_only",
        "event_interpretation_context_after_release",
        "beat_miss_alpha_or_guidance_surprise_claim",
        ("missing_pit_expectation_baseline", "partial_metric_interpretation_only"),
        (
            "storage/earnings_guidance_result_artifact_scout_q4_2025_20260515/report.json",
            "storage/earnings_guidance_readiness_scout_q4_2025_20260515/report.json",
        ),
        "Add PIT expectation baselines before any result-surprise association claim.",
    ),
    _FamilySpec(
        "earnings_guidance_raise_cut_or_withdrawal",
        "earnings_guidance",
        "earnings_guidance",
        "Do reviewed current guidance raise/cut/withdrawal events have stable signed or risk-only association?",
        ("symbol", "sector"),
        "high",
        "proposed",
        "blocked_missing_current_comparable_guidance_context",
        "review_queue_context_only",
        "signed_guidance_alpha_or_escalated_event_risk_intervention",
        ("missing_current_comparable_guidance_context", "missing_pit_revenue_consensus_baseline"),
        (
            "storage/earnings_guidance_interpretation_review_q4_2025_20260515/report.json",
            "storage/earnings_guidance_current_prior_comparison_readiness_q4_2025_20260516/report.json",
        ),
        "Acquire/interpret current official release/exhibit/transcript guidance and compare to PIT prior/consensus baselines.",
    ),
    _FamilySpec(
        "earnings_call_narrative_residual",
        "symbol_news",
        "earnings_guidance",
        "Do post-release narrative residuals such as margin mix, AI capex framing, or management tone explain absorption/reversal after canonical results?",
        ("symbol", "sector"),
        "normal",
        "proposed",
        "blocked_missing_family_packet",
        "narrative_residual_review_only",
        "news_sentiment_alpha",
        ("missing_family_packet", "missing_transcript_or_company_ir_route"),
        (),
        "Draft a separate narrative-residual packet after official result/guidance interpretation is available.",
    ),
    _FamilySpec(
        "equity_offering_dilution",
        "sec_filing",
        "capital_structure",
        "Do equity offerings, shelf takedowns, convertibles, or ATM programs have stable dilution/absorption path effects?",
        ("symbol", "sector"),
        "high",
        "proposed",
        "packet_needed_source_evidence_available",
        "candidate_family_for_next_packet",
        "directional_alpha_or_forced_reduce",
        ("missing_family_packet", "needs_offering_terms_parser", "needs_matched_controls"),
        ("/root/projects/trading-data/storage/monthly_backfill_v1/sec_company_financials/2016-01/completion_receipt.json",),
        "Create packet and extractor for offering amount, discount, proceeds use, balance-sheet stress, and filing timing.",
    ),
    _FamilySpec(
        "buyback_or_capital_return",
        "sec_filing",
        "capital_allocation",
        "Do buyback authorizations or capital-return disclosures have stable association after controlling for prior trend and valuation context?",
        ("symbol", "sector"),
        "normal",
        "proposed",
        "blocked_missing_family_packet",
        "candidate_family_only",
        "capital_allocation_alpha",
        ("missing_family_packet", "needs_canonical_source_rules"),
        (),
        "Define buyback/capital-return packet and distinguish authorizations from actual repurchases.",
    ),
    _FamilySpec(
        "mna_transaction",
        "sec_filing",
        "corporate_action",
        "Do M&A announcements/filings create predictable gap, spread, deal-risk, or sector-readthrough patterns?",
        ("symbol", "sector"),
        "high",
        "proposed",
        "blocked_missing_family_packet",
        "candidate_family_only",
        "merger_arbitrage_alpha",
        ("missing_family_packet", "needs_deal_terms_and_resolution_clocks"),
        (),
        "Create M&A packet with offer type, premium, consideration, regulatory risk, and resolution clock.",
    ),
    _FamilySpec(
        "insider_or_ownership_change",
        "sec_filing",
        "ownership_governance",
        "Do insider trades, 13D/G, or ownership changes produce stable price/path effects after size/materiality filtering?",
        ("symbol",),
        "normal",
        "proposed",
        "blocked_missing_family_packet",
        "candidate_family_only",
        "ownership_alpha",
        ("missing_family_packet", "needs_form_specific_parser"),
        (),
        "Split insider transaction, activist stake, passive ownership, and routine ownership forms before study.",
    ),
    _FamilySpec(
        "legal_regulatory_investigation",
        "sec_filing",
        "legal_regulatory",
        "Do investigations, subpoenas, enforcement actions, or adverse legal/regulatory disclosures predict tail risk or drawdown persistence?",
        ("symbol", "sector"),
        "high",
        "proposed",
        "blocked_missing_family_packet",
        "candidate_family_for_risk_governor",
        "automatic_flatten_or_halt",
        ("missing_family_packet", "needs_severity_taxonomy", "needs_review_required_rules"),
        (),
        "Create risk-first packet with source precedence, severity ladder, and human-review triggers.",
    ),
    _FamilySpec(
        "accounting_restatement_or_fraud",
        "sec_filing",
        "legal_regulatory",
        "Do restatements, auditor warnings, fraud allegations, or accounting controls disclosures predict tail risk after source-quality filtering?",
        ("symbol", "sector"),
        "high",
        "proposed",
        "blocked_missing_family_packet",
        "candidate_family_for_risk_governor",
        "ordinary_directional_alpha_without_review",
        ("missing_family_packet", "needs_official_vs_allegation_split"),
        (),
        "Split official restatement/control weakness from news-only allegation before association study.",
    ),
    _FamilySpec(
        "bankruptcy_or_restructuring",
        "sec_filing",
        "distress",
        "Do bankruptcy/restructuring/liquidity crisis disclosures predict halt, gap, tail, or recovery-path regimes?",
        ("symbol", "sector"),
        "high",
        "proposed",
        "blocked_missing_family_packet",
        "candidate_family_for_risk_governor",
        "unreviewed_execution_mutation",
        ("missing_family_packet", "needs_distress_stage_lifecycle"),
        (),
        "Create multi-stage distress packet with filing stage, financing, creditor, and resolution clocks.",
    ),
    _FamilySpec(
        "product_launch_or_failure",
        "symbol_news",
        "product_customer",
        "Do product launches, failures, recalls, or safety events have stable symbol/sector path effects by materiality and credibility?",
        ("symbol", "sector"),
        "normal",
        "proposed",
        "blocked_missing_family_packet",
        "candidate_family_only",
        "news_sentiment_alpha",
        ("missing_family_packet", "needs_news_interpretation_standard"),
        ("/root/projects/trading-data/storage/monthly_backfill_v1/alpaca_news/2016-01/completion_receipt.json",),
        "Create product/customer news packet and source-quality rules before using headlines.",
    ),
    _FamilySpec(
        "customer_contract_win_loss",
        "symbol_news",
        "product_customer",
        "Do major customer wins, losses, or contract changes create stable residual effects after materiality review?",
        ("symbol", "sector"),
        "normal",
        "proposed",
        "blocked_missing_family_packet",
        "candidate_family_only",
        "headline_keyword_alpha",
        ("missing_family_packet", "needs_materiality_rules"),
        (),
        "Define customer/contract packet with size, duration, counterparty, and recurring/nonrecurring evidence.",
    ),
    _FamilySpec(
        "management_change",
        "symbol_news",
        "governance_management",
        "Do CEO/CFO/key executive changes predict gap, drift, or uncertainty regimes by surprise and reason?",
        ("symbol", "sector"),
        "normal",
        "proposed",
        "blocked_missing_family_packet",
        "candidate_family_only",
        "management_news_alpha",
        ("missing_family_packet", "needs_departure_reason_taxonomy"),
        (),
        "Split planned succession, resignation, termination, death/health, and activist-driven changes.",
    ),
    _FamilySpec(
        "analyst_rating_or_price_target_change",
        "symbol_news",
        "market_opinion",
        "Do analyst rating/target changes have residual association after controlling for prior momentum and news co-occurrence?",
        ("symbol", "sector"),
        "normal",
        "proposed",
        "blocked_missing_family_packet",
        "candidate_family_only",
        "analyst_headline_alpha",
        ("missing_family_packet", "needs_source_identity_and_reiteration_rules"),
        (),
        "Create analyst-action packet and separate initiation, upgrade/downgrade, target-only, reiteration, and consensus context.",
    ),
    _FamilySpec(
        "supply_chain_disruption",
        "symbol_news",
        "operations_supply_chain",
        "Do supply-chain, production, supplier, or logistics disruptions predict symbol/sector path or volatility effects?",
        ("symbol", "sector"),
        "normal",
        "proposed",
        "blocked_missing_family_packet",
        "candidate_family_only",
        "generic_negative_news_alpha",
        ("missing_family_packet", "needs_scope_routing_rules"),
        (),
        "Create packet with direct-vs-readthrough scope and duration/materiality rules.",
    ),
    _FamilySpec(
        "sector_regulation_policy",
        "sector_news",
        "sector_policy",
        "Do sector-specific regulatory/policy changes produce stable sector ETF and affected-symbol residual effects?",
        ("sector", "symbol", "macro"),
        "high",
        "proposed",
        "blocked_missing_family_packet",
        "candidate_family_for_sector_risk",
        "broad_news_alpha",
        ("missing_family_packet", "needs_sector_scope_mapping"),
        ("/root/projects/trading-data/storage/monthly_backfill_v1/gdelt_news/2016-01/completion_receipt.json",),
        "Create sector-regulation packet with affected industry mapping and official-vs-news source precedence.",
    ),
    _FamilySpec(
        "commodity_or_input_cost_shock",
        "sector_news",
        "sector_supply_demand",
        "Do commodity/input-cost shocks create stable sector and symbol residual effects conditioned on exposure?",
        ("sector", "symbol", "macro"),
        "normal",
        "proposed",
        "blocked_missing_family_packet",
        "candidate_family_only",
        "unconditioned_sector_alpha",
        ("missing_family_packet", "needs_exposure_mapping"),
        (),
        "Define commodity exposure map and split producer, consumer, and intermediary effects.",
    ),
    _FamilySpec(
        "sector_demand_shock",
        "sector_news",
        "sector_supply_demand",
        "Do sector demand shocks or industry read-throughs produce stable ETF/symbol effects after base sector context controls?",
        ("sector", "symbol"),
        "normal",
        "proposed",
        "blocked_missing_family_packet",
        "candidate_family_only",
        "unconditioned_sector_news_alpha",
        ("missing_family_packet", "needs_readthrough_rules"),
        (),
        "Create packet and separate direct company event from true sector read-through.",
    ),
    _FamilySpec(
        "cpi_inflation_release",
        "macro_data",
        "macro_release",
        "Do CPI/inflation releases and surprise values explain market/sector path, rates, volatility, and risk appetite shifts?",
        ("macro", "sector"),
        "high",
        "proposed",
        "packet_needed_source_evidence_available",
        "candidate_family_for_layer_1_2_risk",
        "macro_alpha_without_surprise_baseline",
        ("missing_family_packet", "needs_pit_consensus_surprise"),
        ("/root/projects/trading-data/storage/monthly_backfill_v1/trading_economics_calendar_web/2016-01/completion_receipt.json",),
        "Create CPI packet with official release/source precedence, consensus/previous/revision, and rates/sector sensitivity labels.",
    ),
    _FamilySpec(
        "fomc_rates_policy",
        "macro_news",
        "macro_policy",
        "Do FOMC/rates decisions, statements, minutes, or Fed-path repricing explain market/sector risk and trend regimes?",
        ("macro", "sector"),
        "high",
        "proposed",
        "blocked_missing_family_packet",
        "candidate_family_for_layer_1_2_risk",
        "rates_news_alpha_without_policy_standard",
        ("missing_family_packet", "needs_official_calendar_and_statement_route"),
        (),
        "Create FOMC/rates packet with scheduled shell, decision, statement, press-conference, and market-implied repricing split.",
    ),
    _FamilySpec(
        "nfp_employment_release",
        "macro_data",
        "macro_release",
        "Do NFP/employment releases and revisions explain market/sector path, rates, and risk appetite shifts?",
        ("macro", "sector"),
        "normal",
        "proposed",
        "blocked_missing_family_packet",
        "candidate_family_for_layer_1_2_risk",
        "macro_alpha_without_surprise_baseline",
        ("missing_family_packet", "needs_pit_consensus_surprise"),
        (),
        "Create NFP packet with payroll, unemployment, wage, revision, and consensus fields.",
    ),
    _FamilySpec(
        "treasury_yield_curve_shock",
        "macro_news",
        "macro_rates_liquidity",
        "Do Treasury/yield-curve shocks explain market/sector risk, duration sensitivity, and volatility regimes?",
        ("macro", "sector"),
        "normal",
        "proposed",
        "blocked_missing_family_packet",
        "candidate_family_only",
        "rates_move_as_event_without_residual_test",
        ("missing_family_packet", "needs_rates_state_residual_definition"),
        (),
        "Define residual rates shock after Layer 1 rates/market-state controls.",
    ),
    _FamilySpec(
        "credit_liquidity_stress",
        "macro_news",
        "macro_rates_liquidity",
        "Do credit/liquidity stress events explain tail risk, spread widening, and sector contagion?",
        ("macro", "sector", "symbol"),
        "high",
        "proposed",
        "blocked_missing_family_packet",
        "candidate_family_for_risk_governor",
        "automatic_halt_without_review",
        ("missing_family_packet", "needs_stress_severity_ladder"),
        (),
        "Create stress packet with bank/credit/liquidity subtypes, severity, contagion scope, and review triggers.",
    ),
    _FamilySpec(
        "geopolitical_or_fiscal_shock",
        "macro_news",
        "macro_policy",
        "Do geopolitical, sanctions, fiscal, or election shocks explain market/sector path after scope and uncertainty scoring?",
        ("macro", "sector", "symbol"),
        "normal",
        "proposed",
        "blocked_missing_family_packet",
        "candidate_family_for_risk_governor",
        "broad_geopolitical_alpha",
        ("missing_family_packet", "needs_unknown_event_standard_review"),
        (),
        "Use unknown-event protocol to define reusable subfamilies before association study.",
    ),
    _FamilySpec(
        "price_action_pattern",
        "price_action",
        "abnormal_activity",
        "Do reviewed false breakouts, failed breakdowns, sweeps, traps, or rejection patterns have residual path association after base price-state controls?",
        ("symbol",),
        "normal",
        "proposed",
        "blocked_missing_residual_definition",
        "diagnostic_only_until_residual_proven",
        "duplicated_bar_feature_alpha",
        ("needs_residual_over_base_state", "missing_family_packet"),
        (),
        "Define residual pattern standard and prove incremental value over base target-state features.",
    ),
    _FamilySpec(
        "residual_market_structure_disturbance",
        "equity_abnormal_activity",
        "abnormal_activity",
        "Do unexplained tape/market-structure disturbances predict risk after conditioning on market/sector/target state?",
        ("symbol", "sector"),
        "normal",
        "proposed",
        "blocked_missing_residual_definition",
        "diagnostic_only_until_residual_proven",
        "raw_abnormal_activity_alpha",
        ("needs_residual_over_base_state", "matched_controls_required"),
        (),
        "Build residual detector against Layer 1-3 states before any association study.",
    ),
    _FamilySpec(
        "microstructure_liquidity_disruption",
        "equity_abnormal_activity",
        "abnormal_activity",
        "Do spread/depth/one-sided-trading/halt-like disruptions predict risk or execution-quality deterioration?",
        ("symbol", "sector"),
        "normal",
        "proposed",
        "blocked_missing_liquidity_evidence",
        "execution_risk_context_only",
        "directional_alpha",
        ("needs_liquidity_depth_evidence", "needs_execution_risk_labels"),
        (),
        "Create liquidity disruption packet with execution-quality labels, not directional price labels first.",
    ),
    _FamilySpec(
        "option_derivatives_abnormality",
        "option_abnormal_activity",
        "abnormal_activity",
        "Do IV/skew/term-structure/unusual-volume/sweep/OI option abnormalities predict risk or direction after matched controls?",
        ("symbol", "sector"),
        "high",
        "deferred_low_signal",
        "matched_controls_failed_current_definition",
        "diagnostic_provenance_and_bridge_context_only",
        "standalone_option_flow_alpha",
        ("matched_controls_failed", "non_earnings_option_standard_saturated", "needs_revised_abnormality_definition"),
        (
            "storage/option_activity_matched_control_study_20260515/report.json",
            "storage/option_activity_strict_filter_study_20260515/report.json",
        ),
        "Revise abnormality standard and revalidate controls before any promotion route.",
    ),
)


def _resolve_evidence_status(root: Path, refs: tuple[str, ...]) -> tuple[str, ...]:
    missing: list[str] = []
    for ref in refs:
        path = Path(ref)
        if not path.is_absolute():
            path = root / path
        if not path.exists():
            missing.append(ref)
    return tuple(missing)


def build_event_family_batch_catalog(*, root: Path = Path("."), generated_at_utc: str | None = None) -> EventFamilyBatchCatalog:
    root = root.resolve()
    generated = generated_at_utc or datetime.now(UTC).isoformat()
    candidates: list[EventFamilyCandidate] = []
    for spec in FAMILY_SPECS:
        missing_refs = _resolve_evidence_status(root, spec.evidence_refs)
        blocker_codes = tuple(dict.fromkeys((*spec.blocker_codes, *("missing_evidence_ref" for _ in missing_refs))))
        association_status = spec.default_association_status
        if missing_refs and spec.evidence_refs:
            association_status = f"{association_status}_with_missing_evidence_refs"
        candidates.append(
            EventFamilyCandidate(
                family_key=spec.family_key,
                routing_bucket=spec.routing_bucket,
                mechanism_group=spec.mechanism_group,
                association_question=spec.association_question,
                scope_types=spec.scope_types,
                priority=spec.priority,
                family_status=spec.default_status,
                association_status=association_status,
                accepted_current_use=spec.accepted_current_use,
                blocked_use=spec.blocked_use,
                blocker_codes=blocker_codes,
                evidence_refs=spec.evidence_refs,
                next_action=spec.next_action,
            )
        )
    return EventFamilyBatchCatalog(
        contract_type=CONTRACT_TYPE,
        generated_at_utc=generated,
        architecture_status="fine_grained_event_family_association_batch",
        granularity_rule=(
            "Ingestion categories are routing buckets only. Each mechanism-level event family must run its own packet and "
            "price/path association study before model training, risk intervention promotion, or alpha claims."
        ),
        candidates=tuple(candidates),
        source_documents=(
            "trading-model/docs/100_event_family_scouting.md",
            "trading-model/docs/102_event_layer_final_judgment.md",
            "trading-manager/docs/81_decision.md#D197",
        ),
    )


def write_catalog_artifacts(catalog: EventFamilyBatchCatalog, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "event_family_batch_catalog.json").write_text(
        json.dumps(catalog.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "event_family_batch_summary.json").write_text(
        json.dumps(catalog.summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output_dir / "event_family_first_pass_packets.jsonl").open("w", encoding="utf-8") as handle:
        for candidate in catalog.candidates:
            packet = candidate.to_row()
            packet["contract_type"] = "event_family_first_pass_packet_v1"
            packet["generated_at_utc"] = catalog.generated_at_utc
            handle.write(json.dumps(packet, sort_keys=True) + "\n")
    fieldnames = list(EventFamilyCandidate("", "", "", "", (), "", "", "", "", "", (), (), "").csv_row().keys())
    with (output_dir / "event_family_batch_queue.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for candidate in catalog.candidates:
            writer.writerow(candidate.csv_row())
    blocker_fieldnames = ["family_key", "priority", "routing_bucket", "association_status", "blocker_codes", "next_action"]
    with (output_dir / "event_family_blocker_queue.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=blocker_fieldnames)
        writer.writeheader()
        for candidate in catalog.candidates:
            writer.writerow(
                {
                    "family_key": candidate.family_key,
                    "priority": candidate.priority,
                    "routing_bucket": candidate.routing_bucket,
                    "association_status": candidate.association_status,
                    "blocker_codes": ";".join(candidate.blocker_codes),
                    "next_action": candidate.next_action,
                }
            )


def write_catalog(catalog: EventFamilyBatchCatalog, *, output: TextIO) -> None:
    json.dump(catalog.to_dict(), output, indent=2, sort_keys=True)
    output.write("\n")


def write_summary(catalog: EventFamilyBatchCatalog, *, output: TextIO) -> None:
    json.dump(catalog.summary, output, indent=2, sort_keys=True)
    output.write("\n")


__all__ = [
    "CONTRACT_TYPE",
    "DEFAULT_OUTPUT_DIR",
    "EventFamilyBatchCatalog",
    "EventFamilyCandidate",
    "FAMILY_SPECS",
    "build_event_family_batch_catalog",
    "write_catalog",
    "write_catalog_artifacts",
    "write_summary",
]
