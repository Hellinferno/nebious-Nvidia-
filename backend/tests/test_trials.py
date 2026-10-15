"""B-19: fair baseline harness, immutable trial records, summary arithmetic and config freeze.

Trials here use development fixtures, the labeled in-process executor and a scripted
mock model, so no held-out case is exercised by the harness and no claim is produced.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchproof.evaluator.harness import collect_observations_in_process
from benchproof.patch import apply_patch_to_file, get_shallow_mc01_repair_diff
from benchproof.providers import ProviderError
from benchproof.trials import (
    DEFAULT_BUDGETS,
    InProcessExecutor,
    TrialSpec,
    build_plan,
    canonical_hash,
    load_records,
    plan_hash,
    seal,
    visible_observation,
    write_once,
)
from benchproof.trials.config import (
    CONFIG_PATH,
    build_config,
    final_run_problems,
    identity,
    load_config,
    suite_specs,
    verify_config,
)
from benchproof.trials.summary import summarize, to_markdown
from benchproof.trials.systems import (
    CONSTRAINT_FOR_CHECK,
    PROMPTS,
    ScriptedModelClient,
    execute_trial,
    run_plan,
)

DEV = Path(__file__).resolve().parents[1] / "fixtures" / "development"
CONFIG = {"config_id": "test-config", "config_hash": "test-hash", "identity": {"budgets": DEFAULT_BUDGETS}}


def _reference(case: str) -> dict[str, str]:
    root = DEV / case / "reference" / "app"
    return {f"app/{p.name}": p.read_text(encoding="utf-8") for p in sorted(root.glob("*.py"))}


def _diagnosis(*findings: tuple[str, str], no_defect: bool = False) -> str:
    return json.dumps({
        "findings": [
            {"constraint_id": cid, "status": status, "source_location": "app/money.py:compute_total",
             "claim": f"{cid} is violated", "evidence": "probe total"}
            for cid, status in findings
        ],
        "no_defect": no_defect,
    })


def _patch(files: dict[str, str], restores: tuple[str, ...] = ("C-AMOUNT",)) -> str:
    return json.dumps({"action": "PATCH", "files": [{"path": p, "content": c} for p, c in files.items()],
                       "explanation": "restore the accepted rule", "restores_constraints": list(restores)})


def _action(action: str) -> str:
    return json.dumps({"action": action, "files": [], "explanation": "decision", "restores_constraints": []})


def _run(system: str, case: str, replies: list, budgets: dict | None = None, index: int = 1):
    client = ScriptedModelClient(replies)
    config = CONFIG if budgets is None else {**CONFIG, "identity": {"budgets": {**DEFAULT_BUDGETS, **budgets}}}
    record = execute_trial(
        TrialSpec(order=1, system=system, case_id=case, trial_index=index),
        case_dir=DEV / case, suite="development-v2", run_id="test-run",
        config=config, client=client, executor=InProcessExecutor(),
    )
    return record, client


def _executions(record: dict) -> int:
    return sum(1 for s in record["steps"] if s["kind"] == "execution")


def _calls(record: dict) -> int:
    return sum(1 for s in record["steps"] if s["kind"] == "model_call")


# ── Plan ─────────────────────────────────────────────────────────────────


def test_frozen_plans_assign_every_trial_in_balanced_order() -> None:
    specs, cases = suite_specs("repair-r12-v1")
    assert len(cases) == 12 and len(specs) == 84
    assert [s.system for s in specs[:12]] == ["B0"] * 12
    assert len({s.trial_id for s in specs}) == 84
    for t in (1, 2, 3):
        block = [s for s in specs if s.trial_index == t and s.system != "B0"]
        pairs = [block[i:i + 2] for i in range(0, len(block), 2)]
        assert all({p[0].case_id} == {p[1].case_id} and {p[0].system, p[1].system} == {"B1", "B2"} for p in pairs)
        assert sum(1 for p in pairs if p[0].system == "B1") == 6
    again, _ = suite_specs("repair-r12-v1")
    assert plan_hash(again) == plan_hash(specs)
    r6, r6_cases = suite_specs("repair-r6-v1")
    assert len(r6_cases) == 6
    assert {s: sum(1 for x in r6 if x.system == s) for s in ("B0", "B1", "B2")} == {"B0": 6, "B1": 18, "B2": 18}


# ── Systems ──────────────────────────────────────────────────────────────


def test_b2_repairs_faulty_case_and_only_the_gate_accepts() -> None:
    record, _ = _run("B2", "MC-01", [_diagnosis(("C-AMOUNT", "CONFIRMED")), _patch(_reference("MC-01"))])
    assert record["status"] == "COMPLETED"
    assert record["system_outcome"] == "CHANGE_ACCEPTED"
    assert record["patches"][0]["gate_verdict"] == "VERIFIED"
    assert record["baseline_protected"]["verdict"] == "REJECTED"
    assert record["trajectory"]["classification"] == "PROGRESSING"
    final = record["final_evaluation"]
    assert final["verdict"] == "VERIFIED" and final["changed"] is True
    assert final["evaluator"] == "frozen-protected-evaluator"
    assert _calls(record) == 2 and _executions(record) == 2
    assert record["record_hash"]


def test_b1_submits_its_candidate_and_is_judged_outside_its_loop() -> None:
    record, _ = _run("B1", "MC-01", [
        _diagnosis(("C-AMOUNT", "CONFIRMED")), _patch(_reference("MC-01")), _action("SUBMIT"),
    ])
    assert record["status"] == "COMPLETED"
    assert record["system_outcome"] == "CHANGE_SUBMITTED"
    assert record["baseline_protected"] is None
    assert "gate_verdict" not in record["patches"][0]
    assert record["patches"][0]["visible_verdict"] == "PASS"
    assert record["final_evaluation"]["verdict"] == "VERIFIED"
    assert _calls(record) == 3


def test_b1_never_sees_protected_feedback_and_no_prompt_carries_truth() -> None:
    _, b1 = _run("B1", "MC-01", [
        _diagnosis(("C-AMOUNT", "CONFIRMED")),
        _patch({"app/money.py": apply_patch_to_file(
            (DEV / "MC-01" / "app" / "money.py").read_text(encoding="utf-8"), get_shallow_mc01_repair_diff())}),
        _action("SUBMIT"),
    ])
    _, b2 = _run("B2", "MC-01", [_diagnosis(("C-AMOUNT", "CONFIRMED")), _patch(_reference("MC-01"))])
    b1_text = "\n".join(s + u for s, u in b1.prompts)
    b2_text = "\n".join(s + u for s, u in b2.prompts)
    assert "Protected check observations" not in b1_text and "Engineering-state graph" not in b1_text
    assert not [cid for cid in CONSTRAINT_FOR_CHECK if cid in b1_text]
    assert "Protected check observations" in b2_text and "Engineering-state graph" in b2_text
    for text in (b1_text, b2_text):
        for marker in ("expected.json", "intended_failing", "reference/", "Each line amount is rounded"):
            assert marker not in text
    # Both systems receive the same task, constraints, source and probe evidence.
    for shared in (PROMPTS["task_statement"], "C-AMOUNT (v1)", "### app/money.py", "Probe observation"):
        assert shared in b1.prompts[0][1] and shared in b2.prompts[0][1]


def test_clean_case_b1_false_confirmation_versus_b2_evidence_policy() -> None:
    money = (DEV / "clean-service" / "app" / "money.py").read_text(encoding="utf-8")
    b1, _ = _run("B1", "clean-service", [
        _diagnosis(("C-AMOUNT", "CONFIRMED")), _patch({"app/money.py": money + "# reviewed\n"}), _action("SUBMIT"),
    ])
    b2, _ = _run("B2", "clean-service", [_diagnosis(("C-AMOUNT", "CONFIRMED"))])
    assert b1["system_outcome"] == "CHANGE_SUBMITTED" and b1["final_evaluation"]["changed"] is True
    finding = b2["diagnosis"]["findings"][0]
    assert finding["status"] == "SUSPECTED" and finding["model_status"] == "CONFIRMED"
    assert b2["system_outcome"] == "NO_ACCEPTED_CHANGE" and b2["patches"] == []
    assert _calls(b2) == 1 and "VERIFIED" in b2["stop_reason"]
    specs = [TrialSpec(1, "B1", "clean-service", 1), TrialSpec(2, "B2", "clean-service", 1)]
    summary = summarize([b1, b2], specs, DEV, "development-v2")
    assert summary["systems"]["B1"]["clean_false_confirmation"] == [1, 1]
    assert summary["systems"]["B1"]["harmful_clean_change"] == [1, 1]
    assert summary["systems"]["B2"]["clean_false_confirmation"] == [0, 1]
    assert summary["systems"]["B2"]["harmful_clean_change"] == [0, 1]


def test_b2_stops_a_repeated_rejected_candidate_before_executing_it() -> None:
    shallow = apply_patch_to_file(
        (DEV / "MC-01" / "app" / "money.py").read_text(encoding="utf-8"), get_shallow_mc01_repair_diff()
    )
    record, _ = _run("B2", "MC-01", [
        _diagnosis(("C-AMOUNT", "CONFIRMED")), _patch({"app/money.py": shallow}), _patch({"app/money.py": shallow}),
    ])
    assert record["status"] == "STALLED" and record["failure_class"] == "product"
    assert record["trajectory"]["classification"] == "STALLED"
    assert record["patches"][0]["gate_verdict"] == "REJECTED"
    assert _executions(record) == 2  # baseline and the first candidate only
    assert record["system_outcome"] == "NO_ACCEPTED_CHANGE"
    assert record["final_evaluation"]["verdict"] == "REJECTED"


def test_budget_exhaustion_is_recorded_and_the_trial_stays_assigned() -> None:
    calls, _ = _run("B2", "MC-01", [_diagnosis(("C-AMOUNT", "CONFIRMED"))], budgets={"max_model_calls": 1})
    assert calls["status"] == "BUDGET_EXHAUSTED" and calls["stop_reason"] == "limit max_model_calls"
    assert calls["final_evaluation"]["verdict"] == "REJECTED"
    executions, _ = _run("B2", "MC-01", [_diagnosis(("C-AMOUNT", "CONFIRMED")), _patch(_reference("MC-01"))],
                         budgets={"max_executions": 1})
    assert executions["status"] == "BUDGET_EXHAUSTED" and executions["stop_reason"] == "limit max_executions"
    assert executions["system_outcome"] == "NO_ACCEPTED_CHANGE"
    context, _ = _run("B1", "MC-01", [], budgets={"max_prompt_chars": 500})
    assert context["status"] == "BUDGET_EXHAUSTED" and _calls(context) == 0
    tokens, _ = _run("B1", "MC-01", [_diagnosis(("C-AMOUNT", "CONFIRMED"))], budgets={"max_total_tokens": 6_000})
    assert tokens["status"] == "BUDGET_EXHAUSTED" and tokens["stop_reason"] == "limit max_total_tokens"
    assert tokens["budget"]["used"]["total_tokens"] <= 6_000


def test_one_format_repair_then_malformed_output_fails_visibly() -> None:
    repaired, _ = _run("B1", "clean-service", ["not json", _diagnosis(no_defect=True)])
    assert repaired["status"] == "COMPLETED" and repaired["system_outcome"] == "NO_CHANGE"
    model_steps = [s for s in repaired["steps"] if s["kind"] == "model_call"]
    assert [s["valid"] for s in model_steps] == [False, True]
    assert model_steps[1]["format_repair"] is True
    broken, _ = _run("B1", "clean-service", ["nope", "still nope"])
    assert broken["status"] == "MALFORMED_OUTPUT" and _calls(broken) == 2
    forbidden, _ = _run("B2", "MC-01", [
        _diagnosis(("C-AMOUNT", "CONFIRMED")), _action("SUBMIT"), _action("SUBMIT"),
    ])
    assert forbidden["status"] == "MALFORMED_OUTPUT"  # B2 cannot accept its own work


def test_provider_failure_is_classified_and_kept() -> None:
    record, _ = _run("B2", "MC-01", [ProviderError("upstream 503")])
    assert record["status"] == "PROVIDER_FAILURE" and record["failure_class"] == "infrastructure"
    assert record["before_first_action"] is False  # the baseline probe already ran
    assert record["final_evaluation"]["verdict"] == "REJECTED"


def test_patch_policy_refuses_protected_paths_and_new_files() -> None:
    record, _ = _run("B2", "MC-01", [
        _diagnosis(("C-AMOUNT", "CONFIRMED")),
        _patch({"app/../evaluator/observations.py": "x = 1\n"}),
        _patch({"app/new_module.py": "x = 1\n"}),
    ])
    assert [p["status"] for p in record["patches"]] == ["INVALID", "INVALID"]
    assert {p["code"] for p in record["patches"]} == {"PROTECTED_FILE_VIOLATION"}
    assert _executions(record) == 1 and record["stop_reason"] == "patch limit reached"


# ── Records, resume and summary ──────────────────────────────────────────


def test_records_are_write_once_resumable_and_tamper_evident(tmp_path: Path) -> None:
    specs = build_plan(["MC-01", "clean-service", "AC-01"], 1, "test-seed", systems=("B0",))
    run_dir = tmp_path / "run-1"
    (run_dir / "records").mkdir(parents=True)
    interrupted = next(s for s in specs if s.case_id == "AC-01")
    (run_dir / "records" / f"{interrupted.trial_id}.started").write_text("x", encoding="utf-8")
    kwargs = {"run_dir": run_dir, "case_root": DEV, "suite": "development-v2", "config": CONFIG,
              "client": None, "executor": InProcessExecutor()}
    assert run_plan(specs, **kwargs) == {"written": 2, "skipped_existing": 0, "interrupted": 1}
    assert run_plan(specs, **kwargs) == {"written": 0, "skipped_existing": 3, "interrupted": 0}
    records = load_records(run_dir)
    by_id = {r["trial_id"]: r for r in records}
    assert by_id[interrupted.trial_id]["status"] == "INTERRUPTED"
    assert by_id["B0-MC-01-t1"]["system_outcome"] == "PASSED"  # visible gate is blind to MC-01
    with pytest.raises(FileExistsError):
        write_once(run_dir / "records" / "B0-MC-01-t1.json", {"forged": True})
    by_id["B0-MC-01-t1"]["system_outcome"] = "FLAGGED"
    summary = summarize(list(by_id.values()), specs, DEV, "development-v2")
    assert summary["hash_failures"] == ["B0-MC-01-t1"]
    assert summary["systems"]["B0"]["missing"] == ["B0-MC-01-t1"]
    assert summary["systems"]["B0"]["detected"] == [0, 2]


def _artificial(spec: TrialSpec, **fields) -> dict:
    record = {"schema": "benchproof/trial-record-v1", **spec.to_dict(), "mode": "mock", "isolated": False,
              "executor": "development-in-process", "config_hash": "test-hash", "status": "COMPLETED",
              "failure_class": None, "steps": [], "patches": [], "diagnosis": None,
              "budget": {"used": {"executions": 0}, "elapsed_ms": 1000}}
    record.update(fields)
    return seal(record)


def test_summary_matches_a_hand_counted_artificial_record_set() -> None:
    """Hand-checked arithmetic: every expected number below was counted manually from the rows."""
    probe = [{"kind": "execution", "purpose": "baseline_probe"}]
    mc_obs = visible_observation(collect_observations_in_process(DEV / "MC-01" / "app"))
    clean_obs = visible_observation(collect_observations_in_process(DEV / "clean-service" / "app"))

    def diag(*constraints: str) -> dict:
        return {"findings": [{"constraint_id": c, "status": "CONFIRMED"} for c in constraints], "no_defect": False}

    def final(verdict: str, changed: bool) -> dict:
        return {"verdict": verdict, "changed": changed}

    s = {name: TrialSpec(i, name.split("-")[0], name.split("-", 1)[1].rsplit("-t", 1)[0], int(name[-1]))
         for i, name in enumerate([
             "B0-MC-01-t1", "B0-clean-service-t1",
             "B1-MC-01-t1", "B1-MC-01-t2", "B1-clean-service-t1",
             "B2-MC-01-t1", "B2-MC-01-t2", "B2-clean-service-t1", "B2-clean-service-t2"], 1)}
    records = [
        _artificial(s["B0-MC-01-t1"], system_outcome="FLAGGED"),
        _artificial(s["B0-clean-service-t1"], system_outcome="PASSED"),
        # correct, evidence-backed diagnosis and a verified repair
        _artificial(s["B1-MC-01-t1"], steps=probe, baseline_observation=mc_obs, diagnosis=diag("C-AMOUNT"),
                    patches=[{}], final_evaluation=final("VERIFIED", True), system_outcome="CHANGE_SUBMITTED"),
        # right family named but no executed probe: claim-only; one extra wrong family; failed repair
        _artificial(s["B1-MC-01-t2"], baseline_observation=mc_obs, diagnosis=diag("C-AMOUNT", "C-API"),
                    patches=[{}], final_evaluation=final("REJECTED", True), system_outcome="CHANGE_SUBMITTED"),
        # clean case: false confirmation and a submitted (harmful) change
        _artificial(s["B1-clean-service-t1"], steps=probe, baseline_observation=clean_obs,
                    diagnosis=diag("C-AMOUNT"), patches=[{}], final_evaluation=final("VERIFIED", True),
                    system_outcome="CHANGE_SUBMITTED"),
        _artificial(s["B2-MC-01-t1"], steps=probe, baseline_observation=mc_obs, diagnosis=diag("C-AMOUNT"),
                    patches=[{}], final_evaluation=final("VERIFIED", True), system_outcome="CHANGE_ACCEPTED"),
        # infrastructure failure: stays in the denominator, no diagnosis, no patch
        _artificial(s["B2-MC-01-t2"], status="PROVIDER_FAILURE", failure_class="infrastructure",
                    final_evaluation=final("REJECTED", False), system_outcome="NO_ACCEPTED_CHANGE"),
        _artificial(s["B2-clean-service-t1"], steps=probe, baseline_observation=clean_obs,
                    diagnosis={"findings": [], "no_defect": True}, final_evaluation=final("VERIFIED", False),
                    system_outcome="NO_ACCEPTED_CHANGE"),
        # B2-clean-service-t2 is assigned but has no record
    ]
    summary = summarize(records, list(s.values()), DEV, "development-v2")
    b0, b1, b2 = (summary["systems"][k] for k in ("B0", "B1", "B2"))
    assert b0["detected"] == [1, 1] and b0["clean_false_confirmation"] == [0, 1]
    assert b1["correct_diagnosis"] == [1, 2] and b1["claim_only_diagnosis"] == [1, 2]
    assert b1["finding_precision"] == [2, 4]
    assert b1["verified_repair"] == [1, 2] and b1["conditional_repair"] == [1, 2]
    assert b1["clean_false_confirmation"] == [1, 1] and b1["harmful_clean_change"] == [1, 1]
    assert b2["assigned"] == 4 and b2["present"] == 3 and b2["missing"] == ["B2-clean-service-t2"]
    assert b2["correct_diagnosis"] == [1, 2] and b2["finding_precision"] == [1, 1]
    assert b2["verified_repair"] == [1, 2] and b2["conditional_repair"] == [1, 1]
    assert b2["clean_false_confirmation"] == [0, 2] and b2["harmful_clean_change"] == [0, 2]
    assert b2["infrastructure_failures"] == 1 and b2["unsupported_verified"] == 0
    assert summary["development_only"] is True
    table = to_markdown(summary)
    assert "not a measurement" in table and "| B2 | 2 | 3/4 | 1/2 | 1/2 | 0/2 | 0/2 |" in table


# ── Configuration freeze ─────────────────────────────────────────────────


def test_config_identity_is_stable_and_every_change_is_detected(monkeypatch: pytest.MonkeyPatch) -> None:
    image = "benchproof-candidate:dev@sha256:test"
    config = build_config(image_ref=image)
    assert config["config_hash"] == canonical_hash(identity(image_ref=image))
    assert verify_config(config, identity(image_ref=image)) == []
    assert (config["freeze_status"] == "frozen") == (not config["freeze_blockers"])
    assert config["worst_case_usage"]["total_tokens"] == 72 * DEFAULT_BUDGETS["max_total_tokens"]
    assert config["price_snapshot"]["status"] == "NOT_RECORDED"
    assert verify_config(config, identity(image_ref="other@sha256:x")) == ["runner.image_ref changed"]
    monkeypatch.setitem(PROMPTS, "repair_system", "changed prompt")
    assert verify_config(config, identity(image_ref=image)) == ["prompts.repair_system changed"]
    monkeypatch.undo()
    tampered = {**config, "config_hash": "0" * 64}
    assert "config_hash does not match its own identity" in verify_config(tampered, identity(image_ref=image))
    unbuilt = build_config(image_ref=None)
    assert unbuilt["freeze_status"] == "candidate"
    assert any("image" in b for b in unbuilt["freeze_blockers"])


def test_committed_configuration_is_self_consistent() -> None:
    config = load_config(CONFIG_PATH)
    assert config["config_hash"] == canonical_hash(config["identity"])
    assert config["freeze_status"] in {"candidate", "frozen"}
    assert (config["freeze_status"] == "frozen") == (not config["freeze_blockers"])
    plans = config["identity"]["suites"]["plans"]
    assert plans["repair-r12-v1"]["trials"] == {"B0": 12, "B1": 36, "B2": 36}
    assert plans["repair-r12-v1"]["plan_hash"] == plan_hash(suite_specs("repair-r12-v1")[0])


def test_final_runs_refuse_candidate_configs_and_development_settings() -> None:
    image = "benchproof-candidate:dev@sha256:test"
    current = identity(image_ref=image)
    candidate = {**build_config(image_ref=None), "identity": current}
    candidate["config_hash"] = canonical_hash(current)
    problems = final_run_problems(candidate, current, executor_name="development-in-process",
                                  provider_mode="mock", model_id="scripted-mock")
    assert any("not frozen" in p for p in problems)
    assert "final trials require the isolated Docker runner" in problems
    assert "final trials require the live NVIDIA provider" in problems
    assert "provider model differs from the frozen model" in problems
    frozen = {**candidate, "freeze_status": "frozen", "freeze_blockers": []}
    assert final_run_problems(frozen, current, executor_name="docker-local", provider_mode="live",
                              model_id=current["model"]["model_id"]) == []
