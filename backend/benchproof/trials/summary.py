"""Truth-based scoring of immutable trial records (B-19).

This is the independent assessor. It runs after trials finish and is the only part
of the harness that reads trusted truth (`expected.json`). Every assigned trial
stays in its denominator: a missing, failed or interrupted trial counts as not
diagnosed and not repaired, and is listed explicitly.
"""

from __future__ import annotations

import json
import math
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

from benchproof.evaluator.harness import judge
from benchproof.trials import TrialSpec, plan_hash, record_hash
from benchproof.trials.systems import CONSTRAINT_FOR_CHECK

SUMMARY_SCHEMA = "benchproof/trial-summary-v1"


def load_truth(case_dir: Path) -> dict[str, Any]:
    expected = json.loads((case_dir / "expected.json").read_text(encoding="utf-8"))
    intended = list(expected.get("intended_failing_checks", []))
    return {
        "case_id": case_dir.name,
        "faulty": expected["expected_verdict"] == "REJECTED",
        "intended_checks": intended,
        "intended_constraints": sorted({CONSTRAINT_FOR_CHECK[c] for c in intended}),
    }


def _evidence_supports(record: dict[str, Any], truth: dict[str, Any], case_dir: Path) -> bool:
    """A probe executed in the trial and the trusted oracle sees an intended failure in it."""
    ran_probe = any(s.get("kind") == "execution" and s.get("purpose") == "baseline_probe"
                    for s in record.get("steps", []))
    obs = record.get("baseline_observation")
    if not ran_probe or not isinstance(obs, dict):
        return False
    failing = set(judge(obs, case_dir / "app")["failing_checks"])
    return bool(failing & set(truth["intended_checks"]))


def score_record(record: dict[str, Any], truth: dict[str, Any], case_dir: Path) -> dict[str, Any]:
    faulty = truth["faulty"]
    base = {
        "trial_id": record["trial_id"],
        "case_id": record["case_id"],
        "faulty": faulty,
        "status": record.get("status"),
        "failure_class": record.get("failure_class"),
    }
    if record["system"] == "B0":
        flagged = record.get("system_outcome") == "FLAGGED"
        return {**base, "detected": faulty and flagged, "false_confirmation": not faulty and flagged}

    findings = (record.get("diagnosis") or {}).get("findings") or []
    confirmed = sorted({f["constraint_id"] for f in findings if f.get("status") == "CONFIRMED"})
    intended = set(truth["intended_constraints"])
    named = bool(intended & set(confirmed))
    evidence = named and _evidence_supports(record, truth, case_dir)
    final = record.get("final_evaluation") or {}
    changed = bool(final.get("changed"))
    verified = final.get("verdict") == "VERIFIED"
    calls = [s for s in record.get("steps", []) if s.get("kind") == "model_call"]
    reported = [s["usage"]["total_tokens"] for s in calls
                if isinstance(s.get("usage"), dict) and isinstance(s["usage"].get("total_tokens"), int)]
    budget = record.get("budget") or {}
    return {
        **base,
        "confirmed_constraints": confirmed,
        "correct_diagnosis": faulty and evidence,
        "claim_only_diagnosis": faulty and named and not evidence,
        "true_findings": len(intended & set(confirmed)),
        "confirmed_findings": len(confirmed),
        "patch_attempted": bool(record.get("patches")),
        "verified_repair": faulty and changed and verified,
        "false_confirmation": not faulty and bool(confirmed),
        "harmful_clean_change": not faulty and changed,
        "unsupported_verified": record.get("system_outcome") == "CHANGE_ACCEPTED" and not verified,
        "final_verdict": final.get("verdict"),
        "model_calls": len(calls),
        "reported_tokens": sum(reported),
        "unknown_usage_calls": len(calls) - len(reported),
        "executions": (budget.get("used") or {}).get("executions", 0),
        "wall_ms": budget.get("elapsed_ms"),
    }


def _ratio(numerator: int, denominator: int) -> list[int]:
    return [numerator, denominator]


def _p95(values: list[int]) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


def summarize(
    records: list[dict[str, Any]], specs: list[TrialSpec], case_root: Path, suite: str
) -> dict[str, Any]:
    assigned = {s.trial_id: s for s in specs}
    by_id: dict[str, dict[str, Any]] = {}
    hash_failures: list[str] = []
    duplicates: list[str] = []
    unassigned: list[str] = []
    for record in records:
        trial_id = record.get("trial_id", "?")
        if record.get("record_hash") != record_hash(record):
            hash_failures.append(trial_id)
        elif trial_id not in assigned:
            unassigned.append(trial_id)
        elif trial_id in by_id:
            duplicates.append(trial_id)
        else:
            by_id[trial_id] = record

    truths = {cid: load_truth(case_root / cid) for cid in sorted({s.case_id for s in specs})}
    systems: dict[str, Any] = {}
    for system in sorted({s.system for s in specs}):
        sys_specs = [s for s in specs if s.system == system]
        scored = [score_record(by_id[s.trial_id], truths[s.case_id], case_root / s.case_id)
                  for s in sys_specs if s.trial_id in by_id]
        faulty_n = sum(1 for s in sys_specs if truths[s.case_id]["faulty"])
        clean_n = len(sys_specs) - faulty_n

        def count(key: str, rows: list[dict[str, Any]] = scored) -> int:
            return sum(1 for row in rows if row.get(key))

        entry: dict[str, Any] = {
            "assigned": len(sys_specs),
            "present": len(scored),
            "missing": sorted(s.trial_id for s in sys_specs if s.trial_id not in by_id),
            "unique_cases": len({s.case_id for s in sys_specs}),
            "faulty_trials": faulty_n,
            "clean_trials": clean_n,
            "status_counts": dict(sorted(Counter(row["status"] for row in scored).items())),
            "infrastructure_failures": sum(1 for row in scored if row["failure_class"] == "infrastructure"),
            "product_failures": sum(1 for row in scored if row["failure_class"] == "product"),
        }
        if system == "B0":
            entry["detected"] = _ratio(count("detected"), faulty_n)
            entry["clean_false_confirmation"] = _ratio(count("false_confirmation"), clean_n)
        else:
            attempted_faulty = [row for row in scored if row["faulty"] and row["patch_attempted"]]
            walls = [row["wall_ms"] for row in scored if isinstance(row.get("wall_ms"), int)]
            entry.update(
                correct_diagnosis=_ratio(count("correct_diagnosis"), faulty_n),
                claim_only_diagnosis=_ratio(count("claim_only_diagnosis"), faulty_n),
                finding_precision=_ratio(sum(r["true_findings"] for r in scored),
                                         sum(r["confirmed_findings"] for r in scored)),
                verified_repair=_ratio(count("verified_repair"), faulty_n),
                conditional_repair=_ratio(count("verified_repair", attempted_faulty), len(attempted_faulty)),
                clean_false_confirmation=_ratio(count("false_confirmation"), clean_n),
                harmful_clean_change=_ratio(count("harmful_clean_change"), clean_n),
                harmful_clean_change_note="every counted change still needs manual source review",
                unsupported_verified=count("unsupported_verified"),
                usage={
                    "model_calls": sum(r["model_calls"] for r in scored),
                    "reported_tokens": sum(r["reported_tokens"] for r in scored),
                    "unknown_usage_calls": sum(r["unknown_usage_calls"] for r in scored),
                    "executions": sum(r["executions"] for r in scored),
                    "median_wall_ms": int(statistics.median(walls)) if walls else None,
                    "p95_wall_ms": _p95(walls),
                    "wall_sample": len(walls),
                    "cost": "unknown (no dated price snapshot)",
                },
            )
        entry["trials"] = scored
        systems[system] = entry

    modes = sorted({str(r.get("mode")) for r in by_id.values() if r.get("system") != "B0"})
    executors = sorted({str(r.get("executor")) for r in by_id.values()})
    development_only = any(m != "live" for m in modes) or any(r.get("isolated") is False for r in by_id.values())
    return {
        "schema": SUMMARY_SCHEMA,
        "suite": suite,
        "plan_hash": plan_hash(specs),
        "records_seen": len(records),
        "hash_failures": sorted(hash_failures),
        "duplicates": sorted(duplicates),
        "unassigned": sorted(unassigned),
        "config_hashes": sorted({str(r.get("config_hash")) for r in by_id.values()}),
        "modes": modes,
        "executors": executors,
        "development_only": development_only,
        "systems": systems,
    }


def _fmt(pair: list[int] | None) -> str:
    return "N/A" if pair is None else f"{pair[0]}/{pair[1]}"


def to_markdown(summary: dict[str, Any]) -> str:
    lines = [f"# Trial summary - {summary['suite']}", ""]
    if summary["development_only"]:
        lines += ["**Development run (mock provider or non-isolated executor): not a measurement.**", ""]
    lines += [
        (
            "| System | Unique cases | Trials present/assigned | Correct diagnosis | Verified repair "
            "| Clean false confirmation | Harmful clean change | Median / p95 wall ms |"
        ),
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for system, e in summary["systems"].items():
        usage = e.get("usage") or {}
        diagnosis = e.get("correct_diagnosis") or e.get("detected")
        lines.append(
            f"| {system} | {e['unique_cases']} | {e['present']}/{e['assigned']} | {_fmt(diagnosis)} "
            f"| {_fmt(e.get('verified_repair'))} | {_fmt(e.get('clean_false_confirmation'))} "
            f"| {_fmt(e.get('harmful_clean_change'))} "
            f"| {usage.get('median_wall_ms', 'N/A')} / {usage.get('p95_wall_ms', 'N/A')} |"
        )
    lines += [
        "",
        "B0 'correct diagnosis' is detection by a failing visible check; B0 never names a family.",
        (
            f"Hash failures: {summary['hash_failures'] or 'none'}; "
            f"duplicates: {summary['duplicates'] or 'none'}; unassigned: {summary['unassigned'] or 'none'}."
        ),
    ]
    for system, e in summary["systems"].items():
        if e["missing"]:
            lines.append(f"{system} missing trials (counted as failures): {', '.join(e['missing'])}")
    return "\n".join(lines) + "\n"
