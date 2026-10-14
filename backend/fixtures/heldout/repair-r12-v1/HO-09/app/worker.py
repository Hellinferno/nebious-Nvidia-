import logging
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
