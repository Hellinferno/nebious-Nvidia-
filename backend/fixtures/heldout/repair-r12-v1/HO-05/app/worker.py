import logging

from .schemas import InvoiceRequest
from .services import ConflictError, process_invoice

logger = logging.getLogger(__name__)


def _dispatch(request: InvoiceRequest) -> str | None:
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
