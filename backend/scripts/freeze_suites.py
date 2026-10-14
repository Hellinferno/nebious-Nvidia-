"""Freeze the evaluation suite assets and write the truth lock (B-18).

Writes `backend/fixtures/heldout/manifests/*.json`, `scope.json` and
`truth.lock.json`, and records the freeze validation in
`artifacts/suites/freeze_<timestamp>.json`.

Validation of truth uses the in-process development harness (candidate code is
imported on this machine). That is a development tool for asset validation; the
B-21 measurements re-run every case through the isolated runner.

Usage:
    python scripts/freeze_suites.py            # validate assets and write manifests + lock
    python scripts/freeze_suites.py --verify   # prove current assets match the committed lock
"""

from __future__ import annotations

import argparse
import ast
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND.parent
SCRIPTS = BACKEND / "scripts"
for entry in (str(BACKEND), str(SCRIPTS)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import author_heldout_r12 as r12
import author_heldout_v12 as v12

from benchproof.constraints import contract_hash, list_constraints
from benchproof.suites import (
    FRESHNESS_SUITE,
    GATE_SUITE,
    GRAPH_SUITE,
    LOCK_PATH,
    LOCK_SCHEMA,
    MANIFEST_DIR,
    MUTANT_SUITE,
    REPAIR_SUITE,
    TRAJECTORY_SUITE,
    agent_visible_leaks,
    canonical_json_hash,
    compute_lock_entries,
    gate_root,
    load_json,
    lock_hash,
    repair_root,
    sha256_file,
    tree_hash,
    verify_lock,
)

FROZEN_AT = "2026-10-17"  # suite freeze date in the plan; configuration freeze follows on 20 Oct

# ── Predeclared reduced-scope subsets (by opaque id; never renamed as the full suite) ──
R6_SUBSET = ["HO-01", "HO-03", "HO-02", "HO-04", "HO-07", "HO-10"]  # AC x2, MC x2, clean x2

# ── G8: hand-declared impact truth from the authored call graphs (first principles) ──
ALL_CONTRACTS = ["C-API", "C-AMOUNT", "C-INTEGRITY"]
G8_TASKS: list[dict] = [
    {"task_id": "G-01", "case": "HO-07", "changed_symbols": ["app.money:compute_total"],
     "expected_entry_points": ["app.routes:submit_invoice", "app.worker:handle_invoice_job"],
     "expected_contracts": ALL_CONTRACTS,
     "rationale": "compute_total is called by process_invoice, which both entry points call."},
    {"task_id": "G-02", "case": "HO-10", "changed_symbols": ["app.repository:save_receipt"],
     "expected_entry_points": ["app.routes:submit_invoice", "app.worker:handle_invoice_job"],
     "expected_contracts": ALL_CONTRACTS,
     "rationale": "save_receipt is called by process_invoice; the worker reaches it through InvoiceJobHandler.run."},
    {"task_id": "G-03", "case": "HO-11", "changed_symbols": ["app.schemas:ReceiptResponse"],
     "expected_entry_points": ["app.routes:submit_invoice", "app.worker:handle_invoice_job"],
     "expected_contracts": ALL_CONTRACTS,
     "rationale": "ReceiptResponse is constructed by process_invoice and declared for C-API."},
    {"task_id": "G-04", "case": "HO-05", "changed_symbols": ["app.worker:handle_invoice_job"],
     "expected_entry_points": ["app.worker:handle_invoice_job"],
     "expected_contracts": ["C-AMOUNT", "C-INTEGRITY"],
     "rationale": "The worker entry point has no callers and is declared for C-AMOUNT and C-INTEGRITY."},
    {"task_id": "G-05", "case": "HO-07", "changed_symbols": ["app.routes:submit_invoice"],
     "expected_entry_points": ["app.routes:submit_invoice"],
     "expected_contracts": ["C-API"],
     "rationale": "The route entry point has no callers and is declared for C-API only."},
    {"task_id": "G-06", "case": "HO-10", "changed_symbols": ["app.money:as_decimal"],
     "expected_entry_points": ["app.routes:submit_invoice", "app.worker:handle_invoice_job"],
     "expected_contracts": ALL_CONTRACTS,
     "rationale": "A non-declared helper reaches both entry points through compute_total and process_invoice."},
    {"task_id": "G-07", "case": "HO-11", "changed_symbols": ["app.repository:get_receipt"],
     "expected_entry_points": ["app.routes:submit_invoice", "app.worker:handle_invoice_job"],
     "expected_contracts": ALL_CONTRACTS,
     "rationale": "get_receipt is called only by process_invoice, which both entry points call."},
    {"task_id": "G-08", "case": "HO-05", "changed_symbols": ["app.money:legacy_line_total"],
     "expected_entry_points": [],
     "expected_contracts": [],
     "rationale": "An uncalled helper must not select any entry point or contract beyond the mandatory global checks."},
]

# ── F6: six state transitions, executed on one held-out clean case during measurement ──
F6_TRANSITIONS: list[dict] = [
    {"transition_id": "F-S1", "kind": "changed_file", "case": "HO-07", "dependency": "app/money.py",
     "operation": "append a comment line to app/money.py", "expected": "STALE", "expected_dependency_state": "CHANGED"},
    {"transition_id": "F-S2", "kind": "deleted_file", "case": "HO-07", "dependency": "app/report.py",
     "operation": "delete app/report.py", "expected": "STALE", "expected_dependency_state": "DELETED"},
    {"transition_id": "F-S3", "kind": "changed_contract", "case": "HO-07", "dependency": "accepted-contract",
     "operation": "refresh against a different contract hash", "expected": "STALE", "expected_dependency_state": "CHANGED"},
    {"transition_id": "F-F1", "kind": "unchanged", "case": "HO-07", "dependency": "app/money.py",
     "operation": "no change", "expected": "CURRENT", "expected_dependency_state": "CURRENT"},
    {"transition_id": "F-F2", "kind": "unrelated_edit", "case": "HO-07", "dependency": "app/money.py",
     "operation": "append a comment line to app/routes.py", "expected": "CURRENT", "expected_dependency_state": "CURRENT"},
    {"transition_id": "F-F3", "kind": "unrelated_add", "case": "HO-07", "dependency": "app/money.py",
     "operation": "add app/extra.py", "expected": "CURRENT", "expected_dependency_state": "CURRENT"},
]


def _git_head() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True, timeout=10
        )
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _symbols_in(app_dir: Path) -> set[str]:
    """Module-level symbols as `app.module:name`, computed with the AST (not the impact tool)."""
    found: set[str] = set()
    for path in sorted(app_dir.glob("*.py")):
        module = f"app.{path.stem}"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                found.add(f"{module}:{node.name}")
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        found.add(f"{module}:{target.id}")
    return found


def validate_repair_cases() -> list[dict]:
    """External truth validation with the development harness (labeled as such)."""
    import os

    from benchproof.evaluator.harness import validate_fixture
    from benchproof.fixtures import load_expected

    previous = os.environ.get("BENCHPROOF_FIXTURES_DIR")
    os.environ["BENCHPROOF_FIXTURES_DIR"] = str(repair_root())
    rows: list[dict] = []
    try:
        for case_id in sorted(p.name for p in repair_root().iterdir() if (p / "fixture.json").exists()):
            report = validate_fixture(case_id)
            expected = load_expected(case_id)
            leaks = agent_visible_leaks(repair_root() / case_id)
            rows.append(
                {
                    "case_id": case_id,
                    "ok": report["ok"] and not leaks,
                    "problems": report["problems"] + leaks,
                    "expected_verdict": expected["expected_verdict"],
                    "observed_verdict": report["original"]["verdict"],
                    "observed_failing_checks": report["original"]["failing_checks"],
                    "observed_unknown_checks": report["original"]["unknown_checks"],
                    "reference_verdict": report["reference_repair"]["verdict"] if report["reference_repair"] else None,
                }
            )
    finally:
        if previous is None:
            os.environ.pop("BENCHPROOF_FIXTURES_DIR", None)
        else:
            os.environ["BENCHPROOF_FIXTURES_DIR"] = previous
    return rows


def repair_manifest() -> dict:
    from benchproof.fixtures import source_hash_for_dir

    cases = []
    faulty = clean = 0
    for case_id in sorted(p.name for p in repair_root().iterdir() if (p / "fixture.json").exists()):
        case_dir = repair_root() / case_id
        expected = load_json(case_dir / "expected.json")
        has_reference = (case_dir / "reference").exists()
        faulty += int(expected["expected_verdict"] == "REJECTED")
        clean += int(expected["expected_verdict"] == "VERIFIED")
        cases.append(
            {
                "case_id": case_id,
                "source_hash": source_hash_for_dir(case_dir / "app"),
                "fixture_manifest_hash": sha256_file(case_dir / "fixture.json"),
                "truth_hash": sha256_file(case_dir / "expected.json"),
                "reference_repair_hash": tree_hash(case_dir / "reference", (".py",)) if has_reference else None,
                "trials_per_case": 3,
            }
        )
    return {
        "schema_version": "benchproof/suite-manifest-v1",
        "suite": REPAIR_SUITE,
        "frozen_at": FROZEN_AT,
        "generator": "backend/scripts/author_heldout_r12.py",
        "shuffle_seed": r12.SHUFFLE_SEED,
        "visibility": "held-out; case ids are opaque and family labels live only in trusted truth",
        "counts": {"unique_cases": len(cases), "faulty": faulty, "clean": clean, "trials_per_case": 3,
                   "b2_trials": len(cases) * 3, "b1_trials": len(cases) * 3, "b0_runs": len(cases),
                   "faulty_trials": faulty * 3, "clean_trials": clean * 3},
        "r6_subset": {"suite": "repair-r6-v1", "case_ids": R6_SUBSET,
                      "counts": {"unique_cases": 6, "faulty": 4, "clean": 2, "trials_per_case": 3}},
        "inputs": {"generator": "none; the trusted oracle uses fixed boundary and conflict inputs",
                   "boundary_lines": ["0.005", "0.005"], "conflict_lines": ["1.00", "2.00"]},
        "accepted_contract_hash": contract_hash(),
        "constraints": [{"constraint_id": c.constraint_id, "version": c.version, "hash": c.hash} for c in list_constraints()],
        "cases": cases,
    }


def gate_manifest() -> dict:
    public = load_json(gate_root() / "candidates.json")
    truth = load_json(gate_root() / "expected.json")
    return {
        "schema_version": "benchproof/suite-manifest-v1",
        "suite": GATE_SUITE,
        "frozen_at": FROZEN_AT,
        "generator": "backend/scripts/author_heldout_v12.py",
        "base_suite": REPAIR_SUITE,
        "counts": truth["counts"],
        "v6_subset": {"suite": "gate-v6-v1", "candidate_ids": public["v6_subset"],
                      "counts": {"total": 6, "valid": 2, "invalid": 4}},
        "smoke_gate": "visible-smoke-v1 (benchproof/evaluator/smoke.py)",
        "truth_hash": sha256_file(gate_root() / "expected.json"),
        "candidates": public["candidates"],
    }


def graph_manifest() -> dict:
    problems: list[str] = []
    for task in G8_TASKS:
        symbols = _symbols_in(repair_root() / task["case"] / "app")
        for symbol in task["changed_symbols"] + task["expected_entry_points"]:
            if symbol not in symbols:
                problems.append(f"{task['task_id']}: {symbol} is not defined in {task['case']}")
    if problems:
        raise SystemExit("G8 truth references unknown symbols: " + "; ".join(problems))
    protected = {c.constraint_id: c.protected_check_ids for c in list_constraints()}
    tasks = []
    for task in G8_TASKS:
        checks = sorted({check for cid in task["expected_contracts"] for check in protected[cid]})
        tasks.append({**task, "expected_contract_checks": checks,
                      "source_hash": tree_hash(repair_root() / task["case"] / "app", (".py",))})
    return {
        "schema_version": "benchproof/suite-manifest-v1",
        "suite": GRAPH_SUITE,
        "frozen_at": FROZEN_AT,
        "truth_basis": "hand-declared from the authored call graphs; symbol existence checked with the AST only, "
                       "never computed with the impact tool under test",
        "scoring": "entry-point and contract recall/precision per task; mandatory global checks are reported "
                   "separately and never count as graph selections",
        "counts": {"tasks": len(tasks)},
        "tasks": tasks,
    }


def freshness_manifest() -> dict:
    return {
        "schema_version": "benchproof/suite-manifest-v1",
        "suite": FRESHNESS_SUITE,
        "frozen_at": FROZEN_AT,
        "counts": {"stale": 3, "fresh": 3},
        "execution": "each transition runs on a fresh copy of the named held-out clean case with one REVIEWED "
                     "decision declaring the listed dependency; development F6 preparation is separate evidence",
        "transitions": F6_TRANSITIONS,
    }


def trajectory_manifest() -> dict:
    from benchproof.trajectory import FINGERPRINT_RULE_VERSION, STALL_REPEAT_THRESHOLD
    from benchproof.trajectory.development import SUITE_ID, development_traces

    traces = []
    for trace in development_traces():
        steps = [step.model_dump(mode="json") for step in trace["steps"]]
        traces.append({"trace_id": trace["trace_id"], "label": trace["label"], "reason": trace["reason"],
                       "step_count": len(steps), "steps_hash": canonical_json_hash(steps)})
    return {
        "schema_version": "benchproof/suite-manifest-v1",
        "suite": TRAJECTORY_SUITE,
        "source_suite_id": SUITE_ID,
        "frozen_at": FROZEN_AT,
        "rule_version": FINGERPRINT_RULE_VERSION,
        "repeat_threshold": STALL_REPEAT_THRESHOLD,
        "source": "backend/benchproof/trajectory/development.py",
        "counts": {"stalls": sum(1 for t in traces if t["label"] == "STALLED"),
                   "progressing": sum(1 for t in traces if t["label"] == "PROGRESSING")},
        "traces": traces,
        "traces_hash": canonical_json_hash(traces),
        "note": "synthetic trace classification; executed recovery outcomes are recorded separately",
    }


def mutant_manifest() -> dict:
    from benchproof.fixtures import fixture_dir, source_hash_for_dir
    from benchproof.mutations import TEMPLATE_SET_VERSION, TEMPLATES, apply_template

    target = fixture_dir("clean-service") / "app"
    module_path = BACKEND / "benchproof" / "mutations" / "__init__.py"
    templates = []
    for template in TEMPLATES:
        with tempfile.TemporaryDirectory(prefix="bp-m12-") as tmp:
            mutant = Path(tmp) / "app"
            shutil.copytree(target, mutant, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            applied, detail = apply_template(mutant, template)
            syntax_ok = True
            if applied:
                for path in mutant.glob("*.py"):
                    try:
                        ast.parse(path.read_text(encoding="utf-8"))
                    except SyntaxError:
                        syntax_ok = False
            mutant_hash = source_hash_for_dir(mutant) if applied else None
        anchors = canonical_json_hash([{"path": r.path, "before": r.before, "after": r.after} for r in template.replacements])
        templates.append({
            "template_id": template.template_id, "version": template.version, "family": template.family,
            "supporting_check_ids": list(template.supporting_check_ids), "anchors_hash": anchors,
            "applicable": applied, "syntax_valid": applied and syntax_ok, "detail": detail,
            "mutant_hash": mutant_hash,
        })
    return {
        "schema_version": "benchproof/suite-manifest-v1",
        "suite": MUTANT_SUITE,
        "frozen_at": FROZEN_AT,
        "template_set_version": TEMPLATE_SET_VERSION,
        "templates_module_hash": sha256_file(module_path),
        "target": {"fixture_id": "clean-service", "suite": "development-v2",
                   "source_hash": source_hash_for_dir(target),
                   "note": "templates anchor on this accepted candidate; sensitivity measures the check set, not the agent"},
        "counts": {"templates": len(templates), "per_family": 3,
                   "applicable": sum(1 for t in templates if t["applicable"]),
                   "syntax_valid": sum(1 for t in templates if t["syntax_valid"])},
        "templates": templates,
        "execution": "validity is frozen here without execution; killed/survived counts are measured in B-21",
    }


def scope_manifest(repair: dict, gate: dict) -> dict:
    return {
        "schema_version": "benchproof/scope-decision-v1",
        "decision_id": "D-027",
        "frozen_at": FROZEN_AT,
        "selected": {
            "repair": repair["suite"], "gate": gate["suite"], "graph": GRAPH_SUITE,
            "freshness": FRESHNESS_SUITE, "trajectory": TRAJECTORY_SUITE, "mutants": MUTANT_SUITE,
        },
        "assigned_trials": {
            "B0_visible_smoke_runs": repair["counts"]["b0_runs"],
            "B1_same_agent_trials": repair["counts"]["b1_trials"],
            "B2_runtime_trials": repair["counts"]["b2_trials"],
            "faulty_trials_per_system": repair["counts"]["faulty_trials"],
            "clean_trials_per_system": repair["counts"]["clean_trials"],
            "gate_candidates": gate["counts"]["total"],
        },
        "fallback": {
            "repair": {"suite": "repair-r6-v1", "case_ids": R6_SUBSET},
            "gate": {"suite": "gate-v6-v1", "candidate_ids": gate["v6_subset"]["candidate_ids"]},
            "rule": "May be selected only before the first final trial, for a stated reserve or time reason; "
                    "results are then reported as R6/V6, never as R12/V12.",
        },
        "budget": {
            "price_snapshot": "not recorded; cost is reported as unknown until a dated price is captured",
            "development_usage_reference": "about 828 tokens across four Day 1 preflight calls without excerpts",
            "worst_case_tokens_estimate": {"per_model_call": 4000, "calls_per_trial": 6, "trials_with_model": 72,
                                           "total": 4000 * 6 * 72},
            "runner_executions_estimate": {"per_trial_max": 12, "trials": 84, "gate_candidates": 24,
                                           "mutants_and_suites": 60},
            "judging_reserve_share": 0.20,
            "rule": "If measured usage after the first balanced block exceeds the usable credit minus the reserve, "
                    "stop and declare the predeclared R6/V6 fallback before continuing.",
        },
        "configuration_freeze": "B-19 on 20 October freezes runtime commit, prompts, model, image, budgets",
        "contamination_status": "untouched holdout: assets are hash-locked and committed before any trial; the "
                                "repository is public, so the holdout is untouched-by-tuning rather than secret",
    }


def freeze() -> int:
    problems = r12.check_tree(r12.SUITE_ROOT, r12.all_cases()) + v12.check_suite(v12.build_all())
    if problems:
        for problem in problems:
            print(f"! {problem}")
        print("assets differ from their generators; regenerate before freezing")
        return 1
    validation = validate_repair_cases()
    if not all(row["ok"] for row in validation):
        for row in validation:
            for problem in row["problems"]:
                print(f"! {row['case_id']}: {problem}")
        return 1

    repair = repair_manifest()
    gate = gate_manifest()
    manifests = {
        REPAIR_SUITE: repair,
        GATE_SUITE: gate,
        GRAPH_SUITE: graph_manifest(),
        FRESHNESS_SUITE: freshness_manifest(),
        TRAJECTORY_SUITE: trajectory_manifest(),
        MUTANT_SUITE: mutant_manifest(),
    }
    for suite_id, payload in manifests.items():
        _write(MANIFEST_DIR / f"{suite_id}.json", payload)
    _write(MANIFEST_DIR / "scope.json", scope_manifest(repair, gate))

    entries = compute_lock_entries()
    lock = {
        "schema": LOCK_SCHEMA,
        "frozen_at": FROZEN_AT,
        "written_at": datetime.now(UTC).isoformat(),
        "authored_at_commit": _git_head(),
        "accepted_contract_hash": contract_hash(),
        "entries": entries,
        "lock_hash": lock_hash(entries),
    }
    _write(LOCK_PATH, lock)

    out_dir = REPO_ROOT / "artifacts" / "suites"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    record = {
        "schema_version": "benchproof/suite-freeze-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "lock_hash": lock["lock_hash"],
        "validation_tool": "in-process development harness (asset validation only; B-21 uses the isolated runner)",
        "repair_validation": validation,
        "manifest_hashes": {k: canonical_json_hash(v) for k, v in manifests.items()},
    }
    path = out_dir / f"freeze_{stamp}.json"
    path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")

    print(f"{REPAIR_SUITE}: {repair['counts']['unique_cases']} cases ({repair['counts']['faulty']} faulty / {repair['counts']['clean']} clean)")
    print(f"{GATE_SUITE}: {gate['counts']['total']} candidates ({gate['counts']['valid']} valid / {gate['counts']['invalid']} invalid)")
    print(f"{GRAPH_SUITE}: {len(G8_TASKS)} tasks · {FRESHNESS_SUITE}: 6 transitions · "
          f"{TRAJECTORY_SUITE}: {len(manifests[TRAJECTORY_SUITE]['traces'])} traces · "
          f"{MUTANT_SUITE}: {manifests[MUTANT_SUITE]['counts']['applicable']}/12 applicable")
    print(f"lock_hash={lock['lock_hash']}")
    print(f"freeze record: {path.relative_to(REPO_ROOT)}")
    return 0


def verify() -> int:
    problems = verify_lock()
    problems += r12.check_tree(r12.SUITE_ROOT, r12.all_cases())
    problems += v12.check_suite(v12.build_all())
    for problem in problems:
        print(f"! {problem}")
    lock = load_json(LOCK_PATH) if LOCK_PATH.exists() else {}
    print(f"frozen assets {'match' if not problems else 'DO NOT MATCH'} the lock {lock.get('lock_hash', '?')[:16]}")
    return 1 if problems else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    return verify() if args.verify else freeze()


if __name__ == "__main__":
    sys.exit(main())
