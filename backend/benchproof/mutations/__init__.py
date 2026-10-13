"""Trusted semantic mutation assessment (B-16).

Templates are frozen evaluator-side transformations.  Candidate code cannot
select, edit, score, or persist them.  Every mutant is created from a fresh
copy of the accepted candidate and judged by the same external protected
oracles as the acceptance gate.
"""

from __future__ import annotations

import ast
import json
import shutil
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from benchproof.domain import MutationOutcome, MutationResult
from benchproof.fixtures import fixture_dir, source_hash_for_dir
from benchproof.gate import verify_candidate_app
from benchproof.patch import PatchProposal, apply_patch_to_dir, validate_patch
from benchproof.storage import (
    _connect,
    get_audit,
    get_patch,
    save_mutation_assessment,
)

MUTATION_POLICY = "OPTIONAL"
TEMPLATE_SET_VERSION = "development-semantic-v1"
MAX_MUTANTS_PER_RUN = 3
_RUNTIME_TEMP_ROOT = Path.cwd() / "artifacts" / "runtime-temp"


class MutationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Replacement:
    path: str
    before: str
    after: str


@dataclass(frozen=True)
class MutationTemplate:
    template_id: str
    version: int
    family: str
    intended_behavior: str
    supporting_check_ids: tuple[str, ...]
    replacements: tuple[Replacement, ...]


def _r(path: str, before: str, after: str) -> Replacement:
    return Replacement(path, before, after)


TEMPLATES: tuple[MutationTemplate, ...] = (
    MutationTemplate(
        "api-status-201", 1, "api", "Return 201 instead of the declared 200 response.",
        ("api-status-code",),
        (_r("routes.py", '@router.post("/invoices", response_model=ReceiptResponse)',
            '@router.post("/invoices", response_model=ReceiptResponse, status_code=201)'),),
    ),
    MutationTemplate(
        "api-omit-status", 1, "api", "Omit the required status response field.",
        ("api-field-presence",),
        (_r("routes.py", 'response_model=ReceiptResponse)',
            'response_model=ReceiptResponse, response_model_exclude={"status"})'),),
    ),
    MutationTemplate(
        "api-omit-total", 1, "api", "Omit the required total_amount response field.",
        ("api-field-presence",),
        (_r("routes.py", 'response_model=ReceiptResponse)',
            'response_model=ReceiptResponse, response_model_exclude={"total_amount"})'),),
    ),
    MutationTemplate(
        "amount-round-lines", 1, "amount", "Round every line before summing.",
        ("amount-boundary",),
        (_r(
            "money.py",
            'total = sum((Decimal(line) for line in lines), Decimal("0"))',
            'total = sum((Decimal(line).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) for line in lines), Decimal("0"))',
        ),),
    ),
    MutationTemplate(
        "amount-coarse-quantum", 1, "amount", "Quantize invoice totals to one decimal place.",
        ("amount-boundary",),
        (_r("money.py", 'return str(total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))',
            'return str(total.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))'),),
    ),
    MutationTemplate(
        "amount-add-cent", 1, "amount", "Add one cent before final rounding.",
        ("amount-boundary",),
        (_r("money.py", 'total = sum((Decimal(line) for line in lines), Decimal("0"))',
            'total = sum((Decimal(line) for line in lines), Decimal("0")) + Decimal("0.01")'),),
    ),
    MutationTemplate(
        "caller-rewrite-request", 1, "caller", "Worker calls the shared helper with altered amounts.",
        ("caller-consistency",),
        (_r("worker.py", "receipt = process_invoice(req)",
            'receipt = process_invoice(req.model_copy(update={"line_amounts": ["1.00"]}))'),),
    ),
    MutationTemplate(
        "caller-append-amount", 1, "caller", "Worker adds an amount before delegating.",
        ("caller-consistency",),
        (_r("worker.py", "line_amounts=line_amounts", 'line_amounts=line_amounts + ["1.00"]'),),
    ),
    MutationTemplate(
        "caller-bypass-helper", 1, "caller", "Worker bypasses the shared service helper.",
        ("caller-consistency", "worker-caller-path"),
        (_r("worker.py", "receipt = process_invoice(req)",
            'receipt = type("Receipt", (), {"total_amount": "0.00"})()'),),
    ),
    MutationTemplate(
        "idempotency-disable-lookup", 1, "idempotency", "Treat every request as new.",
        ("idempotency-duplicate",),
        (_r("services.py", "existing = get_receipt(req.tenant_id, req.request_id)",
            "existing = None"),),
    ),
    MutationTemplate(
        "idempotency-disable-conflict", 1, "idempotency", "Return the prior receipt for a conflicting payload.",
        ("idempotency-conflict",),
        (_r("services.py", "if existing.get('line_amounts') != req.line_amounts:",
            "if False and existing.get('line_amounts') != req.line_amounts:"),),
    ),
    MutationTemplate(
        "idempotency-drop-tenant-key", 1, "idempotency", "Look up duplicate keys without tenant isolation.",
        ("idempotency-duplicate", "idempotency-conflict"),
        (_r(
            "repository.py",
            "return _store.get(tenant_id, {}).get(request_id)",
            "return next((bucket[request_id] for bucket in _store.values() if request_id in bucket), None)",
        ),),
    ),
)

_FIXTURE_FAMILIES = {
    "AC-01": "api",
    "MC-01": "amount",
    "CI-01": "caller",
    "ID-01": "idempotency",
    # The clean control uses the idempotency family because its tenant-key
    # mutant demonstrates the intentionally missing cross-tenant oracle.
    "clean-service": "idempotency",
}


def template_registry() -> list[dict[str, Any]]:
    return [
        {
            "template_id": item.template_id,
            "version": item.version,
            "family": item.family,
            "intended_behavior": item.intended_behavior,
            "supporting_check_ids": list(item.supporting_check_ids),
        }
        for item in TEMPLATES
    ]


def _reserve_executions(audit_id: str, requested: int, db_path: Path | None) -> None:
    conn = _connect(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT limits_json, reservations FROM audits WHERE audit_id=?", (audit_id,)
        ).fetchone()
        if row is None:
            raise MutationError("AUDIT_NOT_FOUND", f"Audit {audit_id} not found")
        limits = json.loads(row["limits_json"] or "{}")
        reservations = json.loads(row["reservations"] or "{}")
        maximum = int(limits.get("max_executions", 12))
        used = int(reservations.get("mutation_executions", 0))
        if used + requested > maximum:
            raise MutationError(
                "BUDGET_EXHAUSTED",
                f"Mutation assessment needs {requested} executions; {maximum - used} remain",
            )
        reservations["mutation_executions"] = used + requested
        conn.execute(
            "UPDATE audits SET reservations=? WHERE audit_id=?",
            (json.dumps(reservations, sort_keys=True), audit_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _prepare_candidate(
    audit: dict[str, Any], patch_id: str | None, destination: Path, db_path: Path | None
) -> tuple[str, str | None]:
    base = fixture_dir(audit["fixture_id"]) / "app"
    current_hash = source_hash_for_dir(base)
    if not patch_id:
        shutil.copytree(base, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        return source_hash_for_dir(destination), None
    patch = get_patch(patch_id, db_path=db_path)
    if patch is None or patch["audit_id"] != audit["audit_id"]:
        raise MutationError("PATCH_NOT_FOUND", "Patch does not belong to this audit")
    proposal = PatchProposal(
        patch_id=patch_id,
        audit_id=audit["audit_id"],
        base_source_hash=patch["base_hash"],
        target_files=patch["approved_paths"],
        diff=patch["diff_text"],
        author=patch.get("author", "nemotron-repair"),
    )
    validate_patch(proposal, current_hash)
    _, candidate_hash = apply_patch_to_dir(base, proposal, destination)
    return candidate_hash, patch.get("diff_hash") or ""


def apply_template(app_dir: Path, template: MutationTemplate) -> tuple[bool, str]:
    """Apply an exact trusted template.  A drifted anchor is skipped, never guessed."""
    for replacement in template.replacements:
        target = app_dir / replacement.path
        if not target.is_file():
            return False, f"missing target {replacement.path}"
        source = target.read_text(encoding="utf-8")
        count = source.count(replacement.before)
        if count != 1:
            return False, f"anchor count for {replacement.path} was {count}, expected 1"
    for replacement in template.replacements:
        target = app_dir / replacement.path
        source = target.read_text(encoding="utf-8")
        target.write_text(source.replace(replacement.before, replacement.after, 1), encoding="utf-8")
    return True, "trusted exact replacement applied"


def _syntax_valid(app_dir: Path) -> tuple[bool, str]:
    for path in sorted(app_dir.glob("*.py")):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=path.name)
        except SyntaxError as exc:
            return False, f"{path.name}:{exc.lineno}: {exc.msg}"
    return True, "all Python files parse"


def execute_mutant(
    accepted_candidate: Path,
    template: MutationTemplate,
    baseline_checks: dict[str, str],
) -> MutationResult:
    started = time.perf_counter()
    _RUNTIME_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bp-mutant-", dir=_RUNTIME_TEMP_ROOT) as tmp:
        mutant_dir = Path(tmp) / "app"
        shutil.copytree(accepted_candidate, mutant_dir, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        applied, detail = apply_template(mutant_dir, template)
        if not applied:
            return MutationResult(
                template_id=template.template_id,
                template_version=template.version,
                family=template.family,
                base_candidate_hash=source_hash_for_dir(accepted_candidate),
                validity="not_applicable",
                outcome=MutationOutcome.SKIPPED,
                supporting_check_ids=list(template.supporting_check_ids),
                reason=detail,
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
        mutant_hash = source_hash_for_dir(mutant_dir)
        syntax_ok, syntax_detail = _syntax_valid(mutant_dir)
        if not syntax_ok:
            return MutationResult(
                template_id=template.template_id,
                template_version=template.version,
                family=template.family,
                mutant_hash=mutant_hash,
                base_candidate_hash=source_hash_for_dir(accepted_candidate),
                validity="invalid_syntax",
                outcome=MutationOutcome.INVALID,
                supporting_check_ids=list(template.supporting_check_ids),
                reason=syntax_detail,
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
        selected = list(template.supporting_check_ids)
        if any(baseline_checks.get(check_id) != "PASS" for check_id in selected):
            return MutationResult(
                template_id=template.template_id,
                template_version=template.version,
                family=template.family,
                mutant_hash=mutant_hash,
                base_candidate_hash=source_hash_for_dir(accepted_candidate),
                validity="valid",
                outcome=MutationOutcome.SKIPPED,
                supporting_check_ids=selected,
                selected_check_ids=selected,
                reason="one or more supporting checks did not pass on the accepted baseline",
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
        result = verify_candidate_app(mutant_dir)
        outcomes = {item["check_id"]: item["outcome"] for item in result["checks"]}
        reasons = {item["check_id"]: item["reason"] for item in result["checks"]}
        selected_outcomes = [outcomes.get(check_id, "UNKNOWN") for check_id in selected]
        import_failure = any("candidate failed to load" in reasons.get(check_id, "") for check_id in selected)
        if import_failure:
            validity = "invalid_import"
            outcome = MutationOutcome.INVALID
            reason = "mutant failed to import; invalid mutants are excluded from killed counts"
        elif "FAIL" in selected_outcomes:
            validity = "valid"
            outcome = MutationOutcome.KILLED
            reason = "a supporting protected check failed on the intended semantic deviation"
        elif "UNKNOWN" in selected_outcomes:
            validity = "valid"
            outcome = MutationOutcome.UNKNOWN
            reason = "a supporting protected check produced no adjudicated result"
        else:
            validity = "valid"
            outcome = MutationOutcome.SURVIVED
            reason = "all selected supporting checks still passed"
        return MutationResult(
            template_id=template.template_id,
            template_version=template.version,
            family=template.family,
            mutant_hash=mutant_hash,
            base_candidate_hash=source_hash_for_dir(accepted_candidate),
            validity=validity,
            outcome=outcome,
            supporting_check_ids=selected,
            selected_check_ids=selected,
            reason=reason,
            duration_ms=int((time.perf_counter() - started) * 1000),
        )


def _strength_status(counts: dict[str, int]) -> str:
    if counts["survived"]:
        return "WEAK"
    if counts["invalid"] or counts["skipped"] or counts["unknown"]:
        return "INCONCLUSIVE"
    if counts["killed"]:
        return "ADEQUATE_FOR_DECLARED_MUTANTS"
    return "NOT_RUN"


def run_mutation_assessment(
    audit_id: str,
    patch_id: str | None = None,
    max_mutants: int = MAX_MUTANTS_PER_RUN,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Run at most three relevant fresh mutants without modifying the accepted candidate."""
    if not 1 <= max_mutants <= MAX_MUTANTS_PER_RUN:
        raise MutationError("INVALID_INPUT", "max_mutants must be between 1 and 3")
    audit = get_audit(audit_id, db_path=db_path)
    if audit is None:
        raise MutationError("AUDIT_NOT_FOUND", f"Audit {audit_id} not found")
    family = _FIXTURE_FAMILIES.get(audit["fixture_id"])
    if family is None:
        raise MutationError("NO_RELEVANT_TEMPLATES", "No mutation family is mapped to this fixture")
    templates = [item for item in TEMPLATES if item.family == family][:max_mutants]
    # One baseline plus each selected fresh branch consumes the shared execution budget.
    _reserve_executions(audit_id, len(templates) + 1, db_path)
    started = time.perf_counter()
    _RUNTIME_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bp-mutation-run-", dir=_RUNTIME_TEMP_ROOT) as tmp:
        accepted_dir = Path(tmp) / "accepted" / "app"
        base_hash, patch_hash = _prepare_candidate(audit, patch_id, accepted_dir, db_path)
        baseline = verify_candidate_app(accepted_dir, patch_hash=patch_hash)
        if baseline["verdict"] != "VERIFIED":
            raise MutationError(
                "CANDIDATE_NOT_VERIFIED",
                "Mutation strength is assessed only for a candidate that passes the protected gate",
            )
        baseline_checks = {item["check_id"]: item["outcome"] for item in baseline["checks"]}
        results = [execute_mutant(accepted_dir, template, baseline_checks) for template in templates]
        final_hash = source_hash_for_dir(accepted_dir)
    counts = {name: 0 for name in ("killed", "survived", "invalid", "skipped", "unknown")}
    for result in results:
        key = "unknown" if result.outcome == MutationOutcome.INCONCLUSIVE else result.outcome.value.lower()
        counts[key] += 1
    run_id = f"mutation-{uuid.uuid4().hex[:12]}"
    run: dict[str, Any] = {
        "mutation_run_id": run_id,
        "audit_id": audit_id,
        "patch_id": patch_id,
        "family": family,
        "policy": MUTATION_POLICY,
        "strength_status": _strength_status(counts),
        "base_candidate_hash": base_hash,
        "final_candidate_hash": final_hash,
        "candidate_unchanged": base_hash == final_hash,
        "counts": counts,
        "template_set_version": TEMPLATE_SET_VERSION,
        "template_versions": [f"{item.template_id}@{item.version}" for item in templates],
        "execution_count": len(templates) + 1,
        "overhead_ms": int((time.perf_counter() - started) * 1000),
        "results": [item.model_dump(mode="json") for item in results],
    }
    if not run["candidate_unchanged"]:
        raise MutationError("CANDIDATE_CHANGED", "Accepted candidate changed during mutation execution")
    save_mutation_assessment(run, run["results"], db_path=db_path)
    from benchproof.storage.lifecycle import append_event

    append_event(
        audit_id,
        "mutation_completed",
        {
            "mutation_run_id": run_id,
            "strength_status": run["strength_status"],
            "policy": MUTATION_POLICY,
            "counts": counts,
            "candidate_unchanged": True,
            "execution_count": run["execution_count"],
        },
        db_path=db_path,
    )
    return run
