"""Run bounded NVIDIA investigations for development fixtures and save artifacts (B-08)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from benchproof.constraints import contract_hash
from benchproof.domain import AuditRecord
from benchproof.fixtures import list_fixture_ids, source_hash
from benchproof.investigation import run_investigation
from benchproof.storage import migrate, save_audit
from benchproof.storage.lifecycle import migrate_lifecycle

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = REPO_ROOT / "artifacts" / "investigation"


def main() -> int:
    migrate()
    migrate_lifecycle()
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    fids = list_fixture_ids()
    print(f"Running bounded NVIDIA investigations for {len(fids)} fixtures...")

    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    for fid in fids:
        audit_id = f"audit-inv-{fid.lower()}-{uuid.uuid4().hex[:6]}"
        rec = AuditRecord(
            audit_id=audit_id,
            owner_ref="default-owner",
            fixture_id=fid,
            source_hash=source_hash(fid),
            contract_hash=contract_hash(),
            mode="live",
        )
        save_audit(rec)

        res = run_investigation(fixture_id=fid, audit_id=audit_id)
        fname = f"{fid}_{ts}.json"
        out_path = ARTIFACTS_DIR / fname
        out_path.write_text(json.dumps(res, indent=2), encoding="utf-8")

        hyp_summary = ", ".join(
            f"{h['hypothesis_id']}({h['constraint_id']}={h['outcome']})"
            for h in res["hypotheses_evaluation"]
        )
        print(
            f"  {fid:14} -> mode={res['provider_metadata'].get('mode'):4} action={res['action_id']:16} -> {hyp_summary}"
        )

    print(f"Investigations complete. Artifacts saved in {ARTIFACTS_DIR}")
    return 0


if __name__ == "__main__":
    main()
