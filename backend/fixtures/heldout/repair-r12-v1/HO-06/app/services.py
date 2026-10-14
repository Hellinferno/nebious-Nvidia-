import uuid

from .money import compute_total
from .repository import get_receipt, save_receipt
from .schemas import InvoiceRequest, ReceiptResponse


class ConflictError(Exception):
    pass


def process_invoice(req: InvoiceRequest) -> ReceiptResponse:
    existing = get_receipt(req.tenant_id, req.request_id)
    if existing and existing["line_amounts"] == req.line_amounts:
        return ReceiptResponse(**{**existing["response"], "receipt_id": str(uuid.uuid4())})
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
