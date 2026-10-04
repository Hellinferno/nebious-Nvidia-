from .schemas import InvoiceRequest
from .services import process_invoice, ConflictError
import logging

logger = logging.getLogger(__name__)

def handle_invoice_job(tenant_id: str, request_id: str, line_amounts: list[str]) -> None:
    """A worker path that uses the same semantics."""
    req = InvoiceRequest(
        tenant_id=tenant_id,
        request_id=request_id,
        line_amounts=line_amounts
    )
    try:
        receipt = process_invoice(req)
        logger.info(f"Processed job for {tenant_id}:{request_id} -> {receipt.total_amount}")
    except ConflictError as e:
        logger.error(f"Job conflict: {e}")
