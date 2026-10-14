import uuid

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
