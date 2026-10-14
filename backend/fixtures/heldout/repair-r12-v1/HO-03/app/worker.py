import logging

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
