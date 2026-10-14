"""Author the frozen fixed-candidate gate suite `gate-v12-v1` (B-18).

Twelve fixed unified diffs against held-out `repair-r12-v1` bases: four valid
candidates (the trusted reference repairs of one case per family) and eight
invalid candidates (shallow repairs that keep the defect, and harmful edits to
clean controls). Every invalid candidate is designed to pass the visible smoke
gate (B0) and fail the protected gate, so the suite measures what the protected
gate catches that smoke accepts.

Candidates are evaluator inputs. Their labels live in the trusted
`expected.json`; the diffs and public manifest are agent-invisible as well
(the gate suite never reaches a model prompt).

Usage:
    python scripts/author_heldout_v12.py            # write diffs + manifests
    python scripts/author_heldout_v12.py --check    # verify on-disk diffs match
"""

from __future__ import annotations

import argparse
import difflib
import json
import shutil
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from benchproof.suites import GATE_SUITE, REPAIR_SUITE, gate_root, repair_root

SUITE_ID = GATE_SUITE
BASE_SUITE = REPAIR_SUITE


def _replace_once(text: str, before: str, after: str, label: str) -> str:
    if text.count(before) != 1:
        raise SystemExit(f"{label}: anchor occurs {text.count(before)} times, expected exactly 1")
    return text.replace(before, after, 1)


# Each candidate: base case id, kind, label, and the exact edits (file -> list of (before, after)).
# Valid candidates use the trusted reference repair instead of edits.
CANDIDATES: list[dict] = [
    {"candidate_id": "V-01", "base_case": "HO-01", "kind": "reference_repair", "expected": "VERIFIED",
     "note": "Trusted repair restoring the omitted required response field."},
    {"candidate_id": "V-02", "base_case": "HO-02", "kind": "reference_repair", "expected": "VERIFIED",
     "note": "Trusted repair restoring the unrounded Decimal sum."},
    {"candidate_id": "V-03", "base_case": "HO-09", "kind": "reference_repair", "expected": "VERIFIED",
     "note": "Trusted repair routing the worker through the shared service helper."},
    {"candidate_id": "V-04", "base_case": "HO-12", "kind": "reference_repair", "expected": "VERIFIED",
     "note": "Trusted repair comparing stored and submitted line amounts."},
    {"candidate_id": "V-05", "base_case": "HO-02", "kind": "shallow_repair", "expected": "REJECTED",
     "expected_failing": ["amount-boundary"],
     "note": "Rewrites the cents arithmetic but still truncates each line before summing.",
     "edits": {"money.py": [(
         "    total = Decimal(cents) / 100\n",
         "    total = Decimal(cents).scaleb(-2)\n",
     )]}},
    {"candidate_id": "V-06", "base_case": "HO-01", "kind": "shallow_repair", "expected": "REJECTED",
     "expected_failing": ["api-status-code"],
     "note": "Restores the response field but changes the success status to 202.",
     "edits": {
         "schemas.py": [(
             "    receipt_id: str\n    tenant_id: str\n    total_amount: str\n    status: str\n",
             "    receipt_id: str\n    tenant_id: str\n    request_id: str\n    total_amount: str\n    status: str\n",
         )],
         "services.py": [(
             '        "tenant_id": req.tenant_id,\n        "total_amount": total,\n',
             '        "tenant_id": req.tenant_id,\n        "request_id": req.request_id,\n        "total_amount": total,\n',
         )],
         "routes.py": [(
             '@router.post("/invoices", response_model=ReceiptResponse)',
             '@router.post("/invoices", response_model=ReceiptResponse, status_code=202)',
         )],
     }},
    {"candidate_id": "V-07", "base_case": "HO-12", "kind": "shallow_repair", "expected": "REJECTED",
     "expected_failing": ["idempotency-conflict"],
     "note": "Removes the length comparison and replays the stored receipt for any reuse of the id.",
     "edits": {"services.py": [(
         ('    if len(existing["line_amounts"]) != len(req.line_amounts):\n'
          '        raise ConflictError("payload differs from the stored request")\n'),
         "    # replay any stored receipt for the same request id\n",
     )]}},
    {"candidate_id": "V-08", "base_case": "HO-09", "kind": "shallow_repair", "expected": "REJECTED",
     "expected_failing": ["worker-caller-path"],
     "note": "Adds an idempotency lookup to the worker's private settle path but still bypasses the service.",
     "edits": {"worker.py": [
         ("from .repository import save_receipt\n", "from .repository import get_receipt, save_receipt\n"),
         ("def _settle(request: InvoiceRequest) -> str:\n    total = compute_total(request.line_amounts)\n",
          ("def _settle(request: InvoiceRequest) -> str:\n"
           "    prior = get_receipt(request.tenant_id, request.request_id)\n"
           "    if prior is not None:\n"
           '        return prior["response"]["total_amount"]\n'
           "    total = compute_total(request.line_amounts)\n")),
     ]}},
    {"candidate_id": "V-09", "base_case": "HO-07", "kind": "harmful_clean_edit", "expected": "REJECTED",
     "expected_failing": ["amount-boundary"],
     "note": "Quantizes each amount inside the reduction of a clean control.",
     "edits": {"money.py": [(
         '    total = reduce(lambda acc, amount: acc + amount, amounts, Decimal("0"))\n',
         '    total = reduce(lambda acc, amount: acc + _quantize(amount), amounts, Decimal("0"))\n',
     )]}},
    {"candidate_id": "V-10", "base_case": "HO-10", "kind": "harmful_clean_edit", "expected": "REJECTED",
     "expected_failing": ["idempotency-conflict"],
     "note": "Drops the conflict signal from a clean control so a reused id silently replays.",
     "edits": {"services.py": [(
         ('    if existing["line_amounts"] != req.line_amounts:\n'
          '        raise ConflictError("payload differs from the stored request")\n'),
         "",
     )]}},
    {"candidate_id": "V-11", "base_case": "HO-11", "kind": "harmful_clean_edit", "expected": "REJECTED",
     "expected_failing": ["api-field-presence"],
     "note": "Removes the status field from a clean control's public receipt.",
     "edits": {
         "schemas.py": [("    total_amount: str\n    status: str\n", "    total_amount: str\n")],
         "services.py": [('        "status": "processed",\n', "")],
     }},
    {"candidate_id": "V-12", "base_case": "HO-05", "kind": "harmful_clean_edit", "expected": "REJECTED",
     "expected_failing": ["amount-boundary"],
     "note": "Coarsens the rounding quantum of a clean control to one decimal place.",
     "edits": {"money.py": [('TWO_PLACES = Decimal("0.01")\n', 'TWO_PLACES = Decimal("0.1")\n')]}},
]

V6_SUBSET = ["V-01", "V-02", "V-05", "V-06", "V-09", "V-12"]


def candidate_tree(spec: dict) -> tuple[Path, dict[str, str]]:
    """Return (base app dir, {filename: new content}) for one candidate."""
    base_app = repair_root() / spec["base_case"] / "app"
    changed: dict[str, str] = {}
    if spec["kind"] == "reference_repair":
        ref = repair_root() / spec["base_case"] / "reference" / "app"
        for path in sorted(ref.glob("*.py")):
            changed[path.name] = path.read_text(encoding="utf-8")
        return base_app, changed
    for name, edits in spec["edits"].items():
        text = (base_app / name).read_text(encoding="utf-8")
        for before, after in edits:
            text = _replace_once(text, before, after, f"{spec['candidate_id']}/{name}")
        changed[name] = text
    return base_app, changed


def unified_diff(base_app: Path, changed: dict[str, str]) -> str:
    parts: list[str] = []
    for name in sorted(changed):
        before = (base_app / name).read_text(encoding="utf-8").splitlines(keepends=True)
        after = changed[name].splitlines(keepends=True)
        diff = difflib.unified_diff(before, after, fromfile=f"a/app/{name}", tofile=f"b/app/{name}", n=3)
        parts.append("".join(diff))
    return "".join(parts)


def build_all() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for spec in CANDIDATES:
        base_app, changed = candidate_tree(spec)
        diff = unified_diff(base_app, changed)
        if not diff.strip():
            raise SystemExit(f"{spec['candidate_id']}: empty diff")
        out[spec["candidate_id"]] = {"spec": spec, "diff": diff, "target_files": sorted(f"app/{n}" for n in changed)}
    return out


def validate_and_label(built: dict[str, dict]) -> list[dict]:
    """Apply each diff through the protected patch rules and judge it with both gates (in-process, development tool)."""
    from benchproof.evaluator.harness import collect_observations_in_process
    from benchproof.evaluator.smoke import smoke_summary
    from benchproof.fixtures import source_hash_for_dir
    from benchproof.gate import verify_candidate_app
    from benchproof.patch import (
        PatchProposal,
        apply_patch_to_dir,
        compute_diff_hash,
        validate_patch,
    )

    rows: list[dict] = []
    for candidate_id, item in built.items():
        spec = item["spec"]
        base_app = repair_root() / spec["base_case"] / "app"
        proposal = PatchProposal(
            patch_id=candidate_id,
            audit_id="freeze",
            base_source_hash=source_hash_for_dir(base_app),
            target_files=item["target_files"],
            diff=item["diff"],
        )
        validate_patch(proposal, source_hash_for_dir(base_app))
        with tempfile.TemporaryDirectory(prefix="bp-v12-") as tmp:
            dest = Path(tmp) / "app"
            _, candidate_hash = apply_patch_to_dir(base_app, proposal, dest)
            protected = verify_candidate_app(dest)
            smoke = smoke_summary(collect_observations_in_process(dest))
        if protected["verdict"] != spec["expected"]:
            raise SystemExit(f"{candidate_id}: protected verdict {protected['verdict']} != expected {spec['expected']}")
        expected_failing = spec.get("expected_failing", [])
        if expected_failing and not set(expected_failing).issubset(protected["failing_checks"]):
            raise SystemExit(f"{candidate_id}: failing {protected['failing_checks']} lacks {expected_failing}")
        if smoke["verdict"] != "PASS":
            raise SystemExit(f"{candidate_id}: smoke verdict {smoke['verdict']} (every frozen candidate must pass smoke)")
        rows.append(
            {
                "candidate_id": candidate_id,
                "base_case": spec["base_case"],
                "base_source_hash": proposal.base_source_hash,
                "candidate_source_hash": candidate_hash,
                "diff_hash": compute_diff_hash(item["diff"]),
                "target_files": item["target_files"],
                "kind": spec["kind"],
                "validity": "valid" if spec["expected"] == "VERIFIED" else "invalid",
                "expected_protected_verdict": spec["expected"],
                "expected_failing_checks": expected_failing,
                "observed_protected_verdict_at_freeze": protected["verdict"],
                "observed_failing_checks_at_freeze": protected["failing_checks"],
                "observed_smoke_verdict_at_freeze": smoke["verdict"],
                "note": spec["note"],
            }
        )
    return rows


def write_suite(built: dict[str, dict], rows: list[dict]) -> None:
    root = gate_root()
    if root.exists():
        shutil.rmtree(root)
    (root / "candidates").mkdir(parents=True)
    for candidate_id, item in built.items():
        (root / "candidates" / f"{candidate_id}.diff").write_text(item["diff"], encoding="utf-8", newline="\n")
    public = {
        "schema_version": "benchproof/v2",
        "suite": SUITE_ID,
        "base_suite": BASE_SUITE,
        "candidates": [
            {
                "candidate_id": row["candidate_id"],
                "base_case": row["base_case"],
                "diff_path": f"candidates/{row['candidate_id']}.diff",
                "diff_hash": row["diff_hash"],
                "target_files": row["target_files"],
            }
            for row in rows
        ],
        "v6_subset": V6_SUBSET,
    }
    (root / "candidates.json").write_text(json.dumps(public, indent=2) + "\n", encoding="utf-8", newline="\n")
    truth = {
        "suite": SUITE_ID,
        "counts": {
            "total": len(rows),
            "valid": sum(1 for r in rows if r["validity"] == "valid"),
            "invalid": sum(1 for r in rows if r["validity"] == "invalid"),
        },
        "v6_subset": V6_SUBSET,
        "labels": rows,
        "notes": "Trusted labels; validated at freeze with the in-process development harness, "
                 "to be re-measured through the isolated runner during B-21.",
    }
    (root / "expected.json").write_text(json.dumps(truth, indent=2) + "\n", encoding="utf-8", newline="\n")


def check_suite(built: dict[str, dict]) -> list[str]:
    problems: list[str] = []
    for candidate_id, item in built.items():
        path = gate_root() / "candidates" / f"{candidate_id}.diff"
        if not path.exists():
            problems.append(f"{candidate_id}: diff missing")
        elif path.read_text(encoding="utf-8") != item["diff"]:
            problems.append(f"{candidate_id}: diff differs from generator")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    built = build_all()
    if args.check:
        problems = check_suite(built)
        for problem in problems:
            print(f"! {problem}")
        print(f"{SUITE_ID}: {len(built)} candidates {'match' if not problems else 'DIFFER FROM'} the generator")
        return 1 if problems else 0
    rows = validate_and_label(built)
    write_suite(built, rows)
    for row in rows:
        print(
            f"{row['candidate_id']} base={row['base_case']} {row['validity']:7} protected={row['observed_protected_verdict_at_freeze']:9} "
            f"smoke={row['observed_smoke_verdict_at_freeze']} failing={','.join(row['observed_failing_checks_at_freeze']) or '-'}"
        )
    print(f"wrote {len(rows)} candidates under {gate_root().relative_to(BACKEND.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
