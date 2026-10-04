import uuid
from typing import Dict, Any
from .schemas import InvoiceRequest, ReceiptResponse
from .money import compute_total
from .repository import get_receipt, save_receipt

class ConflictError(Exception):
    pass

def process_invoice(req: InvoiceRequest) -> ReceiptResponse:
    existing = get_receipt(req.tenant_id, req.request_id)
    if existing:
        if existing.get('line_amounts') != req.line_amounts:
            raise ConflictError("Idempotency conflict: same request_id but different payload")
        return ReceiptResponse(**existing['response'])
    
    total = compute_total(req.line_amounts)
    receipt_id = str(uuid.uuid4())
    
    response_data = {
        "receipt_id": receipt_id,
        "tenant_id": req.tenant_id,
        "request_id": req.request_id,
        "amount": total, # Fault applied here
    }
    
    save_receipt(req.tenant_id, req.request_id, {
        "line_amounts": req.line_amounts,
        "response": response_data
    })
    
    return ReceiptResponse(**response_data)
