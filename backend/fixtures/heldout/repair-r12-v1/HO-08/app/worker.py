import logging
from decimal import ROUND_HALF_UP, Decimal

from .schemas import InvoiceRequest
from .services import ConflictError, process_invoice

log = logging.getLogger("invoice.worker")


def handle_invoice_job(tenant_id: str, request_id: str, line_amounts: list[str]) -> None:
    """Background path: same processing as the HTTP route."""
    normalized = [str(Decimal(text).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)) for text in line_amounts]
    request = InvoiceRequest(tenant_id=tenant_id, request_id=request_id, line_amounts=normalized)
    try:
        receipt = process_invoice(request)
    except ConflictError as exc:
        log.warning("job %s/%s rejected: %s", tenant_id, request_id, exc)
        return
    log.info("job %s/%s settled at %s", tenant_id, request_id, receipt.total_amount)
