"""Development harness: collect observations in-process and evaluate them.

DEVELOPMENT ONLY. This imports candidate code in-process on the builder's
machine so fixtures and oracles can be validated before a runner exists.
It is NOT the protected isolated runner and must never be wired into the
automatic audit flow (see AGENTS.md "Protected boundary").

Both this harness and the Docker runner produce the same observation record
(runner/launcher/observe_invoice.py) and both are judged by the same trusted
oracle in `benchproof.evaluator.observations`.
"""

from __future__ import annotations

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
from benchproof.evaluator import run_gate
from benchproof.evaluator.observations import (
    BOUNDARY_LINES,
    CONFLICT_LINES,
    evaluate_observations,
)
from benchproof.fixtures import (
    assert_no_trusted_assets,
    fixture_dir,
    load_expected,
    source_hash_for_dir,
)


def evaluator_hash() -> str:
    """Hash of the evaluator source files plus the launcher, so results cite the evaluator version."""
    here = Path(__file__).resolve().parent
    launcher = here.parents[1] / "runner" / "launcher" / "observe_invoice.py"
    h = hashlib.sha256()
    for p in [*sorted(here.glob("*.py")), *([launcher] if launcher.exists() else [])]:
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


def collect_observations_in_process(app_dir: Path) -> dict[str, Any]:
    """Same observation record as the launcher, gathered in-process (development only)."""
    obs: dict[str, Any] = {"schema": "benchproof/observations-v1", "route": {}, "worker": {}, "error": None}
    pkg = None
    try:
        pkg = _load_candidate_package(app_dir)
        routes = importlib.import_module(f"{pkg.__name__}.routes")
        worker = importlib.import_module(f"{pkg.__name__}.worker")
        repository = importlib.import_module(f"{pkg.__name__}.repository")
        api = FastAPI()
        api.include_router(routes.router)
        client = TestClient(api)

        def call(lines: list[str]) -> dict[str, Any]:
            r = client.post("/invoices", json={"tenant_id": "t1", "request_id": "r1", "line_amounts": lines})
            body: Any = None
            if r.headers.get("content-type", "").startswith("application/json"):
                body = r.json()
            return {"status": r.status_code, "body": body if isinstance(body, dict) else None}

        obs["route"]["first"] = call(BOUNDARY_LINES)
        obs["route"]["second"] = call(BOUNDARY_LINES)
        obs["route"]["conflict"] = call(CONFLICT_LINES)
        try:
            worker.handle_invoice_job("t2", "r2", BOUNDARY_LINES)
            obs["worker"] = {"stored_receipt": repository.get_receipt("t2", "r2"), "error": None}
        except Exception as e:  # noqa: BLE001 — candidate failure is data
            obs["worker"] = {"stored_receipt": None, "error": f"{type(e).__name__}: {e}"[:200]}
    except Exception as e:  # noqa: BLE001 — candidate crash is data
        obs["error"] = f"{type(e).__name__}: {e}"[:300]
    finally:
        if pkg is not None:
            _unload(pkg.__name__)
    return obs


def _stamp(results: list[CheckResult], src_hash: str) -> list[CheckResult]:
    ev = evaluator_hash()
    ch = contract_hash()
    for r in results:
        r.source_hash = src_hash
        r.contract_hash = ch
        r.evaluator_hash = ev
    return results


def judge(observations: dict[str, Any] | None, app_dir: Path) -> dict[str, Any]:
    """Trusted side: evaluate an observation record against the snapshot's source."""
    app_dir = Path(app_dir)
    src_hash = source_hash_for_dir(app_dir)
    worker_path = app_dir / "worker.py"
    worker_source = worker_path.read_text(encoding="utf-8") if worker_path.exists() else None
    results = evaluate_observations(observations, worker_source)
    required = required_check_ids()
    return {
        "source_hash": src_hash,
        "contract_hash": contract_hash(),
        "evaluator_hash": evaluator_hash(),
        "required_check_ids": sorted(required),
        "checks": [r.model_dump() for r in _stamp(results, src_hash)],
        "failing_checks": sorted(r.check_id for r in results if r.outcome == CheckOutcome.FAIL),
        "unknown_checks": sorted(r.check_id for r in results if r.outcome == CheckOutcome.UNKNOWN),
        "verdict": run_gate(results, required),
    }


def evaluate_app_dir(app_dir: Path) -> dict[str, Any]:
    """Run all protected development checks against one candidate `app/` tree (in-process)."""
    app_dir = Path(app_dir)
    assert_no_trusted_assets(app_dir)
    return judge(collect_observations_in_process(app_dir), app_dir)


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
