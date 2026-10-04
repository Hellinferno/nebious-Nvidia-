from .schemas import InvoiceRequest, ReceiptResponse
from .money import compute_total
from .repository import save_receipt
import uuid
import logging

logger = logging.getLogger(__name__)

def handle_invoice_job(tenant_id: str, request_id: str, line_amounts: list[str]) -> None:
    """Faulty: Bypasses services.process_invoice and misses idempotency check."""
    # Compute total directly
    total = compute_total(line_amounts)
    receipt_id = str(uuid.uuid4())
    
    response_data = {
        "receipt_id": receipt_id,
        "tenant_id": tenant_id,
        "request_id": request_id,
        "total_amount": total,
        "status": "processed"
    }
    
    # Missing conflict check here
    save_receipt(tenant_id, request_id, {
        "line_amounts": line_amounts,
        "response": response_data
    })
    
    logger.info(f"Processed job for {tenant_id}:{request_id} -> {total}")
