#!/usr/bin/env python3
"""Ask an agent to review whether SectorContextModel can be promoted.

By default this is review-only. With ``--write-decision`` it persists supplied
evaluation artifacts plus config/candidate/decision rows to PostgreSQL. With
``--activate-approved-config`` an accepted approval marks the reviewed config
active; deferred/rejected decisions never activate a config.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from model_governance.promotion import build_config_version_row, build_promotion_candidate_row
from model_governance.promotion.agent_review import (
    build_decision_row_from_review,
    build_sector_context_promotion_prompt,
    extract_json_object,
    validate_promotion_review,
)
from model_governance.promotion.persistence import database_url, render_promotion_persistence_sql, run_psql

DEFAULT_MODEL_ID = "model_02_sector_context"
DEFAULT_MODEL_VERSION = "model_02_sector_context"
DEFAULT_CONFIG_HASH = "sector_context_v1_contract"


def _load_summary(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("evaluation summary JSON must be an object")
    return parsed


def _load_artifacts(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("evaluation artifacts JSON must be an object keyed by governance table name")
    return parsed


def _extract_agent_text(stdout: str) -> str:
    stripped = stdout.strip()
    if not stripped:
        raise ValueError("openclaw agent returned empty stdout")
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return stripped
    if isinstance(parsed, dict):
        for key in ("message", "reply", "response", "content", "text", "output"):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                return value
        result = parsed.get("result")
        if isinstance(result, dict):
            payloads = result.get("payloads")
            if isinstance(payloads, list):
                for payload in payloads:
                    if isinstance(payload, dict) and isinstance(payload.get("text"), str) and payload["text"].strip():
                        return payload["text"]
        for value in parsed.values():
            if isinstance(value, dict):
                for key in ("message", "reply", "response", "content", "text"):
                    nested = value.get(key)
                    if isinstance(nested, str) and nested.strip():
                        return nested
    return stripped


def _invoke_agent(*, prompt: str, openclaw_bin: str, agent: str | None, model: str | None, thinking: str, timeout_seconds: int) -> dict[str, Any]:
    command = [openclaw_bin, "agent", "--message", prompt, "--json", "--thinking", thinking, "--timeout", str(timeout_seconds)]
    if agent:
        command.extend(["--agent", agent])
    if model:
        command.extend(["--model", model])
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        if result.stdout:
            print(result.stdout, file=sys.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode)
    return validate_promotion_review(extract_json_object(_extract_agent_text(result.stdout)))


def _fallback_review(summary: dict[str, Any]) -> dict[str, Any]:
    write_policy = summary.get("write_policy") or summary.get("database_write_policy")
    threshold_results = summary.get("threshold_results") if isinstance(summary.get("threshold_results"), dict) else {}
    all_thresholds_pass = bool(threshold_results) and all(bool(result.get("passed")) for result in threshold_results.values() if isinstance(result, dict))
    checks = {
        "has_eval_run": bool(summary.get("eval_run_id")),
        "has_metric_values": bool(summary.get("metric_value_summary")),
        "has_real_non_fixture_data": write_policy not in {"development_tables_written_then_cleaned", "no_database_write", "dry_run_only"},
        "has_explicit_thresholds": bool(summary.get("acceptance_thresholds")),
        "has_baseline_evidence": bool(summary.get("baseline_summary")),
        "has_stability_evidence": bool(summary.get("stability_summary")),
        "has_handoff_evidence": bool(summary.get("handoff_summary")),
        "has_no_future_leak_evidence": bool(summary.get("leakage_summary")),
        "thresholds_pass": all_thresholds_pass,
    }
    can_promote = all(checks.values())
    blockers = [key for key, passed in checks.items() if not passed]
    return validate_promotion_review(
        {
            "can_promote": can_promote,
            "decision_type": "approve" if can_promote else "defer",
            "decision_status": "accepted" if can_promote else "deferred",
            "confidence": 0.9,
            "reasons": ["Local fallback checked real evidence shape, metric values, thresholds, baseline, stability, handoff quality, and leakage summaries."],
            "blockers": blockers,
            "required_next_steps": [] if can_promote else [
                "Run evaluation on real Layer 2 feature/model data.",
                "Provide metric values, thresholds, baseline comparison, stability, sector handoff, and no-future-leak evidence.",
                "Re-run the agent promotion review with complete evidence.",
            ],
            "evidence_checks": checks,
        }
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation-summary-json", type=Path, required=True, help="JSON summary from evaluate_model_02_sector_context.py.")
    parser.add_argument("--evaluation-artifacts-json", type=Path, help="Optional full evaluation artifacts JSON from evaluate_model_02_sector_context.py --print-artifacts.")
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--model-version", default=DEFAULT_MODEL_VERSION)
    parser.add_argument("--config-hash", default=DEFAULT_CONFIG_HASH)
    parser.add_argument("--proposed-by", default="promotion_gate_script")
    parser.add_argument("--dry-run", action="store_true", help="Print prompt/candidate rows without invoking an agent.")
    parser.add_argument("--local-fallback-review", action="store_true", help="Use deterministic local conservative review instead of invoking an agent.")
    parser.add_argument("--agent", default="main", help="OpenClaw agent id for openclaw agent --agent. Defaults to main.")
    parser.add_argument("--model", help="Optional model override for openclaw agent --model.")
    parser.add_argument("--thinking", default="high")
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--openclaw-bin", default="openclaw")
    parser.add_argument("--write-decision", action="store_true", help="Persist evaluation artifacts if supplied plus config/candidate/decision rows to PostgreSQL.")
    parser.add_argument("--activate-approved-config", action="store_true", help="When used with --write-decision, activate only accepted approval decisions.")
    parser.add_argument("--schema", default="trading_model")
    parser.add_argument("--database-url", help="PostgreSQL URL. Defaults to OPENCLAW_DATABASE_URL or the local OpenClaw DB secret file.")
    parser.add_argument("--print-write-sql", action="store_true", help="Print the SQL that would be/will be used for persistence.")
    args = parser.parse_args(argv)

    summary = _load_summary(args.evaluation_summary_json)
    artifacts = _load_artifacts(args.evaluation_artifacts_json)
    config_row = build_config_version_row(
        model_id=args.model_id,
        model_version=args.model_version,
        config_hash=args.config_hash,
        config_payload={"promotion_gate_source": str(args.evaluation_summary_json)},
    )
    eval_run_id = str(summary.get("eval_run_id") or "").strip()
    if not eval_run_id:
        raise SystemExit("evaluation summary must include eval_run_id")
    candidate_row = build_promotion_candidate_row(
        model_id=args.model_id,
        config_version_id=config_row["config_version_id"],
        eval_run_id=eval_run_id,
        proposed_by=args.proposed_by,
        candidate_payload={"evaluation_summary": summary},
    )
    prompt = build_sector_context_promotion_prompt(evaluation_summary=summary, config_version_row=config_row, promotion_candidate_row=candidate_row)

    if args.dry_run:
        print(json.dumps({"config_version": config_row, "promotion_candidate": candidate_row, "agent_prompt": prompt}, indent=2, sort_keys=True, default=str))
        print("DRY RUN ONLY: no agent was invoked and no promotion decision was written.")
        return 0

    review = _fallback_review(summary) if args.local_fallback_review else _invoke_agent(
        prompt=prompt,
        openclaw_bin=args.openclaw_bin,
        agent=args.agent,
        model=args.model,
        thinking=args.thinking,
        timeout_seconds=args.timeout_seconds,
    )
    decision_row = build_decision_row_from_review(promotion_candidate_id=candidate_row["promotion_candidate_id"], review=review)
    payload = {"config_version": config_row, "promotion_candidate": candidate_row, "agent_review": review, "promotion_decision": decision_row}
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))

    if args.write_decision:
        sql = render_promotion_persistence_sql(
            evaluation_artifacts=artifacts,
            config_version_row=config_row,
            promotion_candidate_row=candidate_row,
            promotion_decision_row=decision_row,
            schema=args.schema,
            activate_approved_config=args.activate_approved_config,
        )
        if args.print_write_sql:
            print(sql)
        db_url = database_url(args.database_url)
        run_psql(db_url, sql)
        print(f"persisted promotion decision {decision_row['promotion_decision_id']} for candidate {candidate_row['promotion_candidate_id']}")
        if args.activate_approved_config and review["can_promote"]:
            print(f"activated config {config_row['config_version_id']}")
        elif args.activate_approved_config:
            print("activation skipped because decision was not an accepted approval")
    elif args.print_write_sql:
        sql = render_promotion_persistence_sql(
            evaluation_artifacts=artifacts,
            config_version_row=config_row,
            promotion_candidate_row=candidate_row,
            promotion_decision_row=decision_row,
            schema=args.schema,
            activate_approved_config=args.activate_approved_config,
        )
        print(sql)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
