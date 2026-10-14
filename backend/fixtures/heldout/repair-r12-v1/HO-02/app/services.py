import uuid
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
