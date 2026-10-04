"""Development harness: run the trusted checks against a fixture `app/` tree.

DEVELOPMENT ONLY. This imports candidate code in-process on the builder's
machine so fixtures and oracles can be validated before a runner exists.
It is NOT the protected isolated runner and must never be wired into the
automatic audit flow (see AGENTS.md "Protected boundary").

Expected values are computed here, outside the candidate, from the
constraint definitions. Candidate output is only ever compared against them.
"""

from __future__ import annotations

import ast
import hashlib
import importlib
import importlib.util
import shutil
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from benchproof.constraints import contract_hash, list_constraints
from benchproof.domain import CheckOutcome, CheckResult
from benchproof.evaluator import (
    check_amount_boundary,
    check_api_field_presence,
    check_api_status_code,
    check_caller_consistency,
    check_idempotency_conflict,
    check_idempotency_duplicate,
    check_worker_caller_path,
    run_gate,
)
from benchproof.fixtures import (
    assert_no_trusted_assets,
    fixture_dir,
    load_expected,
    source_hash_for_dir,
)

# Trusted boundary input: 0.005 + 0.005 must round once to 0.01 (not 0.02).
BOUNDARY_LINES = ["0.005", "0.005"]
CONFLICT_LINES = ["1.00", "2.00"]


def evaluator_hash() -> str:
    """Hash of the evaluator source files so results can cite the evaluator version."""
    here = Path(__file__).resolve().parent
    h = hashlib.sha256()
    for p in sorted(here.glob("*.py")):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def required_check_ids() -> set[str]:
    out: set[str] = set()
    for c in list_constraints():
        if c.required:
            out.update(c.protected_check_ids)
    return out


def _load_candidate_package(app_dir: Path) -> Any:
    """Import `app_dir` as a uniquely named package so module state never leaks between fixtures."""
    name = f"bp_candidate_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(
        name, app_dir / "__init__.py", submodule_search_locations=[str(app_dir)]
    )
    assert spec and spec.loader
    pkg = importlib.util.module_from_spec(spec)
    sys.modules[name] = pkg
    spec.loader.exec_module(pkg)
    return importlib.import_module(name)


def _unload(pkg_name: str) -> None:
    for key in [k for k in sys.modules if k == pkg_name or k.startswith(pkg_name + ".")]:
        sys.modules.pop(key, None)


def worker_delegates_to_process_invoice(worker_path: Path) -> bool:
    """Static check: worker.py imports process_invoice from .services and calls it."""
    tree = ast.parse(worker_path.read_text(encoding="utf-8"))
    imported = False
    called = False
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "services"
            and any(a.name == "process_invoice" for a in node.names)
        ):
            imported = True
        if isinstance(node, ast.Call):
            f = node.func
            if (isinstance(f, ast.Name) and f.id == "process_invoice") or (
                isinstance(f, ast.Attribute) and f.attr == "process_invoice"
            ):
                called = True
    return imported and called


def _stamp(results: list[CheckResult], src_hash: str) -> list[CheckResult]:
    ev = evaluator_hash()
    ch = contract_hash()
    for r in results:
        r.source_hash = src_hash
        r.contract_hash = ch
        r.evaluator_hash = ev
    return results


def evaluate_app_dir(app_dir: Path) -> dict[str, Any]:
    """Run all protected development checks against one candidate `app/` tree."""
    app_dir = Path(app_dir)
    assert_no_trusted_assets(app_dir)
    src_hash = source_hash_for_dir(app_dir)
    results: list[CheckResult] = []
    pkg = None
    try:
        pkg = _load_candidate_package(app_dir)
        routes = importlib.import_module(f"{pkg.__name__}.routes")
        worker = importlib.import_module(f"{pkg.__name__}.worker")
        repository = importlib.import_module(f"{pkg.__name__}.repository")

        api = FastAPI()
        api.include_router(routes.router)
        client = TestClient(api)

        payload = {"tenant_id": "t1", "request_id": "r1", "line_amounts": BOUNDARY_LINES}

        # C-API + C-AMOUNT via route
        first = client.post("/invoices", json=payload)
        results.append(check_api_status_code(first.status_code, 200))
        body: dict[str, Any] = {}
        if first.headers.get("content-type", "").startswith("application/json"):
            parsed = first.json()
            body = parsed if isinstance(parsed, dict) else {}
        results.append(check_api_field_presence(body))
        route_total = body.get("total_amount")
        results.append(check_amount_boundary(BOUNDARY_LINES, route_total))

        # C-INTEGRITY: identical resubmission returns the original receipt
        second = client.post("/invoices", json=payload)
        second_body = second.json() if second.status_code == 200 else {}
        results.append(check_idempotency_duplicate(body, second_body))

        # C-INTEGRITY: same key, different payload -> 409
        conflict = client.post(
            "/invoices",
            json={"tenant_id": "t1", "request_id": "r1", "line_amounts": CONFLICT_LINES},
        )
        results.append(check_idempotency_conflict(conflict.status_code))

        # C-AMOUNT / C-INTEGRITY: worker path on a fresh key must agree with the route
        worker.handle_invoice_job("t2", "r2", BOUNDARY_LINES)
        stored = repository.get_receipt("t2", "r2") or {}
        worker_total = (stored.get("response") or {}).get("total_amount")
        results.append(check_caller_consistency(route_total, worker_total))

        results.append(
            check_worker_caller_path(worker_delegates_to_process_invoice(app_dir / "worker.py"))
        )
    except Exception as e:  # noqa: BLE001 — candidate crash -> UNKNOWN for whatever did not run
        results.append(
            CheckResult(
                check_id="harness-exception",
                outcome=CheckOutcome.UNKNOWN,
                oracle_kind="deterministic",
                reason=f"{type(e).__name__}: {str(e)[:200]}",
            )
        )
    finally:
        if pkg is not None:
            _unload(pkg.__name__)

    required = required_check_ids()
    verdict = run_gate(results, required)
    return {
        "source_hash": src_hash,
        "contract_hash": contract_hash(),
        "evaluator_hash": evaluator_hash(),
        "required_check_ids": sorted(required),
        "checks": [r.model_dump() for r in _stamp(results, src_hash)],
        "failing_checks": sorted(r.check_id for r in results if r.outcome == CheckOutcome.FAIL),
        "unknown_checks": sorted(r.check_id for r in results if r.outcome == CheckOutcome.UNKNOWN),
        "verdict": verdict,
    }


def evaluate_fixture(fixture_id: str) -> dict[str, Any]:
    return evaluate_app_dir(fixture_dir(fixture_id) / "app")


def evaluate_reference_repair(fixture_id: str) -> dict[str, Any] | None:
    """Overlay the trusted reference repair on a temp copy of app/ and evaluate it."""
    expected = load_expected(fixture_id)
    rel = expected.get("reference_repair")
    if not rel:
        return None
    base = fixture_dir(fixture_id)
    with tempfile.TemporaryDirectory(prefix="bp-ref-") as tmp:
        dst = Path(tmp) / "app"
        shutil.copytree(base / "app", dst, ignore=shutil.ignore_patterns("__pycache__"))
        for f in (base / rel).glob("*.py"):
            shutil.copy(f, dst / f.name)
        return evaluate_app_dir(dst)


def validate_fixture(fixture_id: str) -> dict[str, Any]:
    """Compare actual behavior with the trusted expected properties for one fixture."""
    expected = load_expected(fixture_id)
    actual = evaluate_fixture(fixture_id)
    intended = set(expected["intended_failing_checks"])
    problems: list[str] = []
    if not intended.issubset(set(actual["failing_checks"])):
        problems.append(
            f"intended failing checks {sorted(intended)} not all observed; "
            f"got {actual['failing_checks']}"
        )
    if actual["verdict"] != expected["expected_verdict"]:
        problems.append(f"verdict {actual['verdict']} != expected {expected['expected_verdict']}")
    ref = evaluate_reference_repair(fixture_id)
    if ref is not None and ref["verdict"] != "VERIFIED":
        problems.append(
            f"reference repair verdict {ref['verdict']}: fails {ref['failing_checks']} "
            f"unknown {ref['unknown_checks']}"
        )
    return {
        "fixture_id": fixture_id,
        "ok": not problems,
        "problems": problems,
        "expected": expected,
        "original": actual,
        "reference_repair": ref,
    }
