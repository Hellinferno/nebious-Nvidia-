"""Author the frozen held-out repair suite `repair-r12-v1` (B-18).

Twelve unique cases: eight faulty (two per implemented family) and four clean
controls. Each case is a complete synthetic invoice service built from one of
four clean *styles* (different identifier names, module structure, control
flow and benign distractors). A faulty case replaces exactly one module of its
style with a faulty variant; the trusted reference repair is the style's
original module. Case identifiers are opaque (`HO-01` … `HO-12`) and the
family assignment is a seeded shuffle recorded in each trusted `expected.json`.

Rules enforced here (and by `tests/test_suites.py`):
- Agent-visible files (`app/*.py`, `fixture.json`) carry no fault markers,
  family names, check IDs or defect descriptions.
- Declared contract symbols (`compute_total`, `process_invoice`,
  `handle_invoice_job`, `submit_invoice`, `InvoiceRequest`, `ReceiptResponse`,
  `get_receipt`, `save_receipt`) keep their names; everything else may vary.
- `expected.json` and `reference/` are trusted evaluator assets and are never
  mounted into a candidate.

Usage:
    python scripts/author_heldout_r12.py            # (re)write the trees
    python scripts/author_heldout_r12.py --check    # verify trees match source
"""

from __future__ import annotations

import argparse
import random
import shutil
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
SUITE_ID = "repair-r12-v1"
SUITE_ROOT = BACKEND / "fixtures" / "heldout" / SUITE_ID
SHUFFLE_SEED = "repair-r12-v1/2026-10-17"

# ── Style A: "ledger" ───────────────────────────────────────────────────

STYLE_A: dict[str, str] = {
    "__init__.py": "",
    "money.py": '''"""Invoice arithmetic helpers."""

from decimal import ROUND_HALF_UP, Decimal
from functools import reduce
from typing import Iterable

CENT = Decimal("0.01")


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def compute_total(lines: Iterable[str]) -> str:
    """Return the invoice total as a two-decimal string."""
    amounts = [Decimal(text) for text in lines]
    if not amounts:
        return "0.00"
    total = reduce(lambda acc, amount: acc + amount, amounts, Decimal("0"))
    return str(_quantize(total))


def preview_line(line: str) -> str:
    """Display-only formatting for a single line in the operator console."""
    return str(_quantize(Decimal(line)))
''',
    "repository.py": '''"""In-memory receipt ledger keyed by tenant and request."""

from typing import Optional


class ReceiptLedger:
    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], dict] = {}

    def find(self, tenant_id: str, request_id: str) -> Optional[dict]:
        return self._entries.get((tenant_id, request_id))

    def put(self, tenant_id: str, request_id: str, receipt: dict) -> None:
        self._entries[(tenant_id, request_id)] = receipt

    def size(self) -> int:
        return len(self._entries)


_ledger = ReceiptLedger()


def get_receipt(tenant_id: str, request_id: str) -> Optional[dict]:
    return _ledger.find(tenant_id, request_id)


def save_receipt(tenant_id: str, request_id: str, receipt: dict) -> None:
    _ledger.put(tenant_id, request_id, receipt)
''',
    "schemas.py": '''from typing import List

from pydantic import BaseModel, Field


class InvoiceRequest(BaseModel):
    tenant_id: str = Field(description="Owning tenant")
    request_id: str = Field(description="Client-chosen idempotency key")
    line_amounts: List[str] = Field(description="Decimal strings, one per line")


class ReceiptResponse(BaseModel):
    receipt_id: str
    tenant_id: str
    request_id: str
    total_amount: str
    status: str


class ReceiptSummary(BaseModel):
    """Aggregate view used by reporting tools; not part of the submit flow."""

    tenant_id: str
    receipt_count: int
''',
    "services.py": '''import uuid

from .money import compute_total
from .repository import get_receipt, save_receipt
from .schemas import InvoiceRequest, ReceiptResponse


class ConflictError(Exception):
    """Raised when a request id is reused with a different payload."""


def _replay(prior: dict, req: InvoiceRequest) -> ReceiptResponse:
    if prior["line_amounts"] != req.line_amounts:
        raise ConflictError(f"request {req.request_id} already used with other amounts")
    return ReceiptResponse(**prior["response"])


def _build_receipt(req: InvoiceRequest, total: str) -> dict:
    return {
        "receipt_id": str(uuid.uuid4()),
        "tenant_id": req.tenant_id,
        "request_id": req.request_id,
        "total_amount": total,
        "status": "processed",
    }


def process_invoice(req: InvoiceRequest) -> ReceiptResponse:
    prior = get_receipt(req.tenant_id, req.request_id)
    if prior is not None:
        return _replay(prior, req)
    total = compute_total(req.line_amounts)
    response = _build_receipt(req, total)
    save_receipt(req.tenant_id, req.request_id, {"line_amounts": req.line_amounts, "response": response})
    return ReceiptResponse(**response)
''',
    "routes.py": '''from fastapi import APIRouter, HTTPException, status

from .schemas import InvoiceRequest, ReceiptResponse
from .services import ConflictError, process_invoice

router = APIRouter()


@router.post("/invoices", response_model=ReceiptResponse)
def submit_invoice(req: InvoiceRequest):
    try:
        return process_invoice(req)
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
''',
    "worker.py": '''import logging

from .schemas import InvoiceRequest
from .services import ConflictError, process_invoice

log = logging.getLogger("invoice.worker")


def handle_invoice_job(tenant_id: str, request_id: str, line_amounts: list[str]) -> None:
    """Background path: same processing as the HTTP route."""
    request = InvoiceRequest(tenant_id=tenant_id, request_id=request_id, line_amounts=line_amounts)
    try:
        receipt = process_invoice(request)
    except ConflictError as exc:
        log.warning("job %s/%s rejected: %s", tenant_id, request_id, exc)
        return
    log.info("job %s/%s settled at %s", tenant_id, request_id, receipt.total_amount)
''',
    "report.py": '''"""Operator reporting helpers (read-only)."""

from .repository import _ledger


def receipt_count() -> int:
    return _ledger.size()
''',
}

# ── Style B: "pipeline" ─────────────────────────────────────────────────

STYLE_B: dict[str, str] = {
    "__init__.py": "",
    "config.py": '''"""Static configuration for the invoice pipeline."""

CURRENCY_PLACES = 2
STATUS_PROCESSED = "processed"
''',
    "money.py": '''from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable

from .config import CURRENCY_PLACES

ROUNDING = ROUND_HALF_UP
_QUANTUM = Decimal(1).scaleb(-CURRENCY_PLACES)


def as_decimal(text: str) -> Decimal:
    return Decimal(text.strip())


def compute_total(lines: Iterable[str]) -> str:
    total = sum(map(as_decimal, lines), Decimal(0))
    return format(total.quantize(_QUANTUM, rounding=ROUNDING), "f")
''',
    "repository.py": '''from collections import defaultdict
from typing import Optional

_receipts: dict[str, dict[str, dict]] = defaultdict(dict)


def get_receipt(tenant_id: str, request_id: str) -> Optional[dict]:
    return _receipts[tenant_id].get(request_id)


def save_receipt(tenant_id: str, request_id: str, receipt: dict) -> None:
    _receipts[tenant_id][request_id] = receipt


def count_receipts(tenant_id: str) -> int:
    return len(_receipts[tenant_id])
''',
    "schemas.py": '''from typing import List

from pydantic import BaseModel


class InvoiceRequest(BaseModel):
    tenant_id: str
    request_id: str
    line_amounts: List[str]


class ReceiptResponse(BaseModel):
    receipt_id: str
    tenant_id: str
    request_id: str
    total_amount: str
    status: str
''',
    "services.py": '''import uuid
from typing import TypedDict

from .config import STATUS_PROCESSED
from .money import compute_total
from .repository import get_receipt, save_receipt
from .schemas import InvoiceRequest, ReceiptResponse


class ConflictError(Exception):
    pass


class StoredReceipt(TypedDict):
    line_amounts: list[str]
    response: dict


def process_invoice(req: InvoiceRequest) -> ReceiptResponse:
    existing = get_receipt(req.tenant_id, req.request_id)
    if existing is None:
        response = {
            "receipt_id": uuid.uuid4().hex,
            "tenant_id": req.tenant_id,
            "request_id": req.request_id,
            "total_amount": compute_total(req.line_amounts),
            "status": STATUS_PROCESSED,
        }
        record: StoredReceipt = {"line_amounts": list(req.line_amounts), "response": response}
        save_receipt(req.tenant_id, req.request_id, record)
        return ReceiptResponse(**response)
    if existing["line_amounts"] != req.line_amounts:
        raise ConflictError("payload differs from the stored request")
    return ReceiptResponse(**existing["response"])
''',
    "routes.py": '''from fastapi import APIRouter, HTTPException

from .schemas import InvoiceRequest, ReceiptResponse
from .services import ConflictError, process_invoice

router = APIRouter()


@router.post("/invoices", response_model=ReceiptResponse)
def submit_invoice(req: InvoiceRequest):
    try:
        return process_invoice(req)
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail={"error": "conflict", "message": str(exc)})
''',
    "worker.py": '''import logging

from .schemas import InvoiceRequest
from .services import ConflictError, process_invoice

logger = logging.getLogger(__name__)


class InvoiceJobHandler:
    def __init__(self, tenant_id: str, request_id: str, line_amounts: list[str]) -> None:
        self.request = InvoiceRequest(
            tenant_id=tenant_id, request_id=request_id, line_amounts=line_amounts
        )

    def run(self) -> None:
        try:
            receipt = process_invoice(self.request)
        except ConflictError as exc:
            logger.error("conflict for %s: %s", self.request.request_id, exc)
            return
        logger.info("settled %s -> %s", self.request.request_id, receipt.total_amount)


def handle_invoice_job(tenant_id: str, request_id: str, line_amounts: list[str]) -> None:
    InvoiceJobHandler(tenant_id, request_id, line_amounts).run()
''',
}

# ── Style C: "compact" ──────────────────────────────────────────────────

STYLE_C: dict[str, str] = {
    "__init__.py": "",
    "money.py": '''from decimal import ROUND_HALF_UP, Decimal
from typing import List


def compute_total(lines: List[str]) -> str:
    running = Decimal("0")
    for text in lines:
        running += Decimal(text)
    return str(running.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def split_even(total: str, parts: int) -> List[str]:
    """Split a settled total into equal parts for installment previews."""
    share = (Decimal(total) / parts).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return [str(share)] * parts
''',
    "repository.py": '''from typing import Optional

_receipts: dict[str, dict] = {}


def _key(tenant_id: str, request_id: str) -> str:
    return f"{tenant_id}/{request_id}"


def get_receipt(tenant_id: str, request_id: str) -> Optional[dict]:
    return _receipts.get(_key(tenant_id, request_id))


def save_receipt(tenant_id: str, request_id: str, receipt: dict) -> None:
    _receipts[_key(tenant_id, request_id)] = receipt
''',
    "schemas.py": '''from typing import List

from pydantic import BaseModel


class InvoiceRequest(BaseModel):
    tenant_id: str
    request_id: str
    line_amounts: List[str]


class ReceiptResponse(BaseModel):
    receipt_id: str
    tenant_id: str
    request_id: str
    total_amount: str
    status: str
''',
    "services.py": '''import uuid

from .money import compute_total
from .repository import get_receipt, save_receipt
from .schemas import InvoiceRequest, ReceiptResponse


class ConflictError(Exception):
    pass


def process_invoice(req: InvoiceRequest) -> ReceiptResponse:
    existing = get_receipt(req.tenant_id, req.request_id)
    if existing and existing["line_amounts"] == req.line_amounts:
        return ReceiptResponse(**existing["response"])
    if existing:
        raise ConflictError("same request id, different line amounts")
    response = {
        "receipt_id": str(uuid.uuid4()),
        "tenant_id": req.tenant_id,
        "request_id": req.request_id,
        "total_amount": compute_total(req.line_amounts),
        "status": "processed",
    }
    save_receipt(req.tenant_id, req.request_id, {"line_amounts": req.line_amounts, "response": response})
    return ReceiptResponse(**response)
''',
    "routes.py": '''from fastapi import APIRouter, HTTPException

from .schemas import InvoiceRequest, ReceiptResponse
from .services import ConflictError, process_invoice

router = APIRouter()


@router.post("/invoices", response_model=ReceiptResponse)
def submit_invoice(req: InvoiceRequest):
    try:
        return process_invoice(req)
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
''',
    "worker.py": '''import logging

from .schemas import InvoiceRequest
from .services import ConflictError, process_invoice

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 2


def handle_invoice_job(tenant_id: str, request_id: str, line_amounts: list[str]) -> None:
    req = InvoiceRequest(tenant_id=tenant_id, request_id=request_id, line_amounts=line_amounts)
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            receipt = process_invoice(req)
        except ConflictError as exc:
            logger.error("attempt %d conflict: %s", attempt, exc)
            return
        logger.info("attempt %d ok: %s", attempt, receipt.total_amount)
        return
''',
}

# ── Style D: "verbose" ──────────────────────────────────────────────────

STYLE_D: dict[str, str] = {
    "__init__.py": "",
    "money.py": '''"""Monetary arithmetic for invoice totals."""

from decimal import ROUND_HALF_UP, Decimal
from typing import Sequence

TWO_PLACES = Decimal("0.01")


def _sum_lines(lines: Sequence[str]) -> Decimal:
    return sum((Decimal(line) for line in lines), Decimal("0"))


def _round_total(total: Decimal) -> str:
    return str(total.quantize(TWO_PLACES, rounding=ROUND_HALF_UP))


def compute_total(lines: Sequence[str]) -> str:
    if not lines:
        return "0.00"
    return _round_total(_sum_lines(lines))


def legacy_line_total(lines: Sequence[str]) -> str:
    """Historical per-line rounding kept for reconciling archived statements.

    Not used by the submit or worker paths.
    """
    rounded = [Decimal(line).quantize(TWO_PLACES, rounding=ROUND_HALF_UP) for line in lines]
    return str(sum(rounded, Decimal("0")))
''',
    "repository.py": '''from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StoredReceipt:
    line_amounts: list[str]
    response: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"line_amounts": list(self.line_amounts), "response": dict(self.response)}


_by_tenant: dict[str, dict[str, StoredReceipt]] = {}


def get_receipt(tenant_id: str, request_id: str) -> Optional[dict]:
    stored = _by_tenant.get(tenant_id, {}).get(request_id)
    return stored.to_dict() if stored else None


def save_receipt(tenant_id: str, request_id: str, receipt: dict) -> None:
    bucket = _by_tenant.setdefault(tenant_id, {})
    bucket[request_id] = StoredReceipt(
        line_amounts=list(receipt["line_amounts"]), response=dict(receipt["response"])
    )
''',
    "schemas.py": '''from typing import List

from pydantic import BaseModel


class InvoiceRequest(BaseModel):
    tenant_id: str
    request_id: str
    line_amounts: List[str]


class ReceiptResponse(BaseModel):
    receipt_id: str
    tenant_id: str
    request_id: str
    total_amount: str
    status: str
''',
    "services.py": '''import uuid
from typing import Optional

from .money import compute_total
from .repository import get_receipt, save_receipt
from .schemas import InvoiceRequest, ReceiptResponse


class ConflictError(Exception):
    """The request id was already settled with different line amounts."""


def _find_existing(req: InvoiceRequest) -> Optional[dict]:
    return get_receipt(req.tenant_id, req.request_id)


def _assert_same_payload(existing: dict, req: InvoiceRequest) -> None:
    if existing["line_amounts"] != req.line_amounts:
        raise ConflictError(f"{req.tenant_id}/{req.request_id} payload mismatch")


def _new_receipt(req: InvoiceRequest) -> dict:
    return {
        "receipt_id": str(uuid.uuid4()),
        "tenant_id": req.tenant_id,
        "request_id": req.request_id,
        "total_amount": compute_total(req.line_amounts),
        "status": "processed",
    }


def process_invoice(req: InvoiceRequest) -> ReceiptResponse:
    existing = _find_existing(req)
    if existing is not None:
        _assert_same_payload(existing, req)
        return ReceiptResponse(**existing["response"])
    response = _new_receipt(req)
    save_receipt(req.tenant_id, req.request_id, {"line_amounts": req.line_amounts, "response": response})
    return ReceiptResponse(**response)
''',
    "routes.py": '''from fastapi import APIRouter, HTTPException

from .schemas import InvoiceRequest, ReceiptResponse
from .services import ConflictError, process_invoice

router = APIRouter()


@router.post("/invoices", response_model=ReceiptResponse, summary="Submit an invoice")
def submit_invoice(req: InvoiceRequest):
    try:
        return process_invoice(req)
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
''',
    "worker.py": '''import logging

from .schemas import InvoiceRequest
from .services import ConflictError, process_invoice

logger = logging.getLogger(__name__)


def _dispatch(request: InvoiceRequest) -> Optional_total:
    try:
        return process_invoice(request).total_amount
    except ConflictError as exc:
        logger.error("conflict: %s", exc)
        return None


def handle_invoice_job(tenant_id: str, request_id: str, line_amounts: list[str]) -> None:
    request = InvoiceRequest(tenant_id=tenant_id, request_id=request_id, line_amounts=line_amounts)
    total = _dispatch(request)
    if total is not None:
        logger.info("settled %s/%s at %s", tenant_id, request_id, total)
'''.replace("Optional_total", "str | None"),
}

STYLES = {"A": STYLE_A, "B": STYLE_B, "C": STYLE_C, "D": STYLE_D}

# ── Faulty module variants (one module replaced per case) ───────────────

FAULTS: dict[str, dict] = {
    "AC-1": {
        "style": "A",
        "family": "API compatibility",
        "constraint": "C-API",
        "mutation_family": "api",
        "intended_failing_checks": ["api-field-presence"],
        "defect": "ReceiptResponse omits the required request_id field on both schema and builder",
        "files": {
            "schemas.py": STYLE_A["schemas.py"].replace(
                "    receipt_id: str\n    tenant_id: str\n    request_id: str\n    total_amount: str\n    status: str\n",
                "    receipt_id: str\n    tenant_id: str\n    total_amount: str\n    status: str\n",
            ),
            "services.py": STYLE_A["services.py"].replace(
                '        "request_id": req.request_id,\n', ""
            ),
        },
    },
    "AC-2": {
        "style": "C",
        "family": "API compatibility",
        "constraint": "C-API",
        "mutation_family": "api",
        "intended_failing_checks": ["api-status-code"],
        "consequential_failing_checks": ["idempotency-duplicate"],
        "defect": "Successful submission answers 201 instead of the declared 200",
        "files": {
            "routes.py": STYLE_C["routes.py"].replace(
                '@router.post("/invoices", response_model=ReceiptResponse)',
                '@router.post("/invoices", response_model=ReceiptResponse, status_code=201)',
            ),
        },
    },
    "MC-1": {
        "style": "B",
        "family": "Exact amount boundary",
        "constraint": "C-AMOUNT",
        "mutation_family": "amount",
        "intended_failing_checks": ["amount-boundary"],
        "defect": "Lines are truncated to integer cents before summing",
        "files": {
            "money.py": STYLE_B["money.py"].replace(
                "    total = sum(map(as_decimal, lines), Decimal(0))\n"
                '    return format(total.quantize(_QUANTUM, rounding=ROUNDING), "f")\n',
                "    cents = sum(int(as_decimal(text) * 100) for text in lines)\n"
                "    total = Decimal(cents) / 100\n"
                '    return format(total.quantize(_QUANTUM, rounding=ROUNDING), "f")\n',
            ),
        },
    },
    "MC-2": {
        "style": "D",
        "family": "Exact amount boundary",
        "constraint": "C-AMOUNT",
        "mutation_family": "amount",
        "intended_failing_checks": ["amount-boundary"],
        "defect": "Each line is converted to float and rounded before the Decimal sum",
        "files": {
            "money.py": STYLE_D["money.py"].replace(
                '    return sum((Decimal(line) for line in lines), Decimal("0"))\n',
                '    return sum((Decimal(str(round(float(line), 2))) for line in lines), Decimal("0"))\n',
            ),
        },
    },
    "CI-1": {
        "style": "D",
        "family": "Cross-module caller impact",
        "constraint": "C-INTEGRITY",
        "mutation_family": "caller",
        "intended_failing_checks": ["worker-caller-path"],
        "defect": "Worker settles jobs through its own helper instead of services.process_invoice",
        "files": {
            "worker.py": '''import logging
import uuid

from .money import compute_total
from .repository import save_receipt
from .schemas import InvoiceRequest

logger = logging.getLogger(__name__)


def _settle(request: InvoiceRequest) -> str:
    total = compute_total(request.line_amounts)
    response = {
        "receipt_id": str(uuid.uuid4()),
        "tenant_id": request.tenant_id,
        "request_id": request.request_id,
        "total_amount": total,
        "status": "processed",
    }
    save_receipt(
        request.tenant_id,
        request.request_id,
        {"line_amounts": request.line_amounts, "response": response},
    )
    return total


def handle_invoice_job(tenant_id: str, request_id: str, line_amounts: list[str]) -> None:
    request = InvoiceRequest(tenant_id=tenant_id, request_id=request_id, line_amounts=line_amounts)
    total = _settle(request)
    logger.info("settled %s/%s at %s", tenant_id, request_id, total)
''',
        },
    },
    "CI-2": {
        "style": "A",
        "family": "Cross-module caller impact",
        "constraint": "C-INTEGRITY",
        "mutation_family": "caller",
        "intended_failing_checks": ["caller-consistency"],
        "defect": "Worker pre-rounds each line before delegating, so route and worker totals diverge",
        "files": {
            "worker.py": STYLE_A["worker.py"].replace(
                "import logging\n",
                "import logging\nfrom decimal import ROUND_HALF_UP, Decimal\n",
            ).replace(
                "    request = InvoiceRequest(tenant_id=tenant_id, request_id=request_id, line_amounts=line_amounts)\n",
                '    normalized = [str(Decimal(text).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)) for text in line_amounts]\n'
                "    request = InvoiceRequest(tenant_id=tenant_id, request_id=request_id, line_amounts=normalized)\n",
            ),
        },
    },
    "ID-1": {
        "style": "B",
        "family": "Tenant-scoped idempotency",
        "constraint": "C-INTEGRITY",
        "mutation_family": "idempotency",
        "intended_failing_checks": ["idempotency-conflict"],
        "defect": "Conflict detection compares line counts instead of line amounts",
        "files": {
            "services.py": STYLE_B["services.py"].replace(
                '    if existing["line_amounts"] != req.line_amounts:\n',
                '    if len(existing["line_amounts"]) != len(req.line_amounts):\n',
            ),
        },
    },
    "ID-2": {
        "style": "C",
        "family": "Tenant-scoped idempotency",
        "constraint": "C-INTEGRITY",
        "mutation_family": "idempotency",
        "intended_failing_checks": ["idempotency-duplicate"],
        "defect": "Replaying an identical request issues a fresh receipt id instead of the stored one",
        "files": {
            "services.py": STYLE_C["services.py"].replace(
                '    if existing and existing["line_amounts"] == req.line_amounts:\n'
                '        return ReceiptResponse(**existing["response"])\n',
                '    if existing and existing["line_amounts"] == req.line_amounts:\n'
                '        return ReceiptResponse(**{**existing["response"], "receipt_id": str(uuid.uuid4())})\n',
            ),
        },
    },
}

CLEAN_SLOTS = {"CL-A": "A", "CL-B": "B", "CL-C": "C", "CL-D": "D"}


def slot_assignment() -> dict[str, str]:
    """Opaque case id -> slot, from a seeded shuffle recorded in the manifest."""
    slots = sorted(FAULTS) + sorted(CLEAN_SLOTS)
    random.Random(SHUFFLE_SEED).shuffle(slots)
    return {f"HO-{index:02d}": slot for index, slot in enumerate(slots, start=1)}


def build_case(case_id: str, slot: str) -> dict[str, str]:
    """Return relative path -> content for one complete case directory."""
    files: dict[str, str] = {}
    if slot in CLEAN_SLOTS:
        style = CLEAN_SLOTS[slot]
        for name, text in STYLES[style].items():
            files[f"app/{name}"] = text
        expected = {
            "suite": SUITE_ID,
            "slot": slot,
            "style": style,
            "family": "Clean control",
            "constraint": None,
            "mutation_family": "idempotency",
            "intended_failing_checks": [],
            "expected_verdict": "VERIFIED",
            "reference_repair": None,
            "notes": "Clean control: every required check passes untouched; any accepted repair is an unjustified change.",
        }
    else:
        spec = FAULTS[slot]
        style = spec["style"]
        for name, text in STYLES[style].items():
            files[f"app/{name}"] = spec["files"].get(name, text)
        for name in spec["files"]:
            files[f"reference/app/{name}"] = STYLES[style][name]
        expected = {
            "suite": SUITE_ID,
            "slot": slot,
            "style": style,
            "family": spec["family"],
            "constraint": spec["constraint"],
            "mutation_family": spec["mutation_family"],
            "intended_failing_checks": spec["intended_failing_checks"],
            "consequential_failing_checks": spec.get("consequential_failing_checks", []),
            "expected_verdict": "REJECTED",
            "reference_repair": "reference/app",
            "defect": spec["defect"],
            "notes": "Trusted evaluator asset; never mounted into a candidate or placed in a prompt.",
        }
    files["fixture.json"] = _json(
        {
            "schema_version": "benchproof/v2",
            "fixture_id": case_id,
            "suite": SUITE_ID,
            "family": None,
            "constraint": None,
            "defect": None,
            "visibility": "held-out",
            "candidate_editable_paths": ["app/"],
            "language": "python",
            "synthetic": True,
        }
    )
    files["expected.json"] = _json(expected)
    return files


def _json(payload: dict) -> str:
    import json

    return json.dumps(payload, indent=2) + "\n"


def all_cases() -> dict[str, dict[str, str]]:
    return {case_id: build_case(case_id, slot) for case_id, slot in slot_assignment().items()}


def write_tree(root: Path, cases: dict[str, dict[str, str]]) -> int:
    written = 0
    for case_id, files in cases.items():
        case_dir = root / case_id
        if case_dir.exists():
            shutil.rmtree(case_dir)
        for rel, text in files.items():
            path = case_dir / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
            written += 1
    return written


def check_tree(root: Path, cases: dict[str, dict[str, str]]) -> list[str]:
    problems: list[str] = []
    for case_id, files in cases.items():
        case_dir = root / case_id
        on_disk = {
            p.relative_to(case_dir).as_posix()
            for p in case_dir.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts
        }
        if on_disk != set(files):
            problems.append(f"{case_id}: file set differs: {sorted(on_disk ^ set(files))}")
        for rel, text in files.items():
            path = case_dir / rel
            if path.is_file() and path.read_text(encoding="utf-8") != text:
                problems.append(f"{case_id}/{rel}: content differs from generator")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify on-disk trees match the generator")
    args = parser.parse_args()
    cases = all_cases()
    if args.check:
        problems = check_tree(SUITE_ROOT, cases)
        for problem in problems:
            print(f"! {problem}")
        print(f"{SUITE_ID}: {len(cases)} cases {'match' if not problems else 'DIFFER FROM'} the generator")
        return 1 if problems else 0
    count = write_tree(SUITE_ROOT, cases)
    for case_id, slot in slot_assignment().items():
        print(f"{case_id} <- {slot}")
    print(f"wrote {count} files under {SUITE_ROOT.relative_to(BACKEND.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
