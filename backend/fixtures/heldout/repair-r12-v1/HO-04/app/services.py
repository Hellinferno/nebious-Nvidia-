import uuid
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
