import logging

from .schemas import InvoiceRequest
from .services import ConflictError, process_invoice

logger = logging.getLogger(__name__)


class InvoiceJobHandler:
    def __init__(self, tenant_id: str, request_id: str, line_amounts: list[str]) -> None:
        self.request = InvoiceRequest(
            tenant_id=tenant_id, request_id=request_id, line_amounts=line_amounts
        )

    def run(self) -> None:
        try:
            receipt = process_invoice(self.request)
        except ConflictError as exc:
            logger.error("conflict for %s: %s", self.request.request_id, exc)
            return
        logger.info("settled %s -> %s", self.request.request_id, receipt.total_amount)


def handle_invoice_job(tenant_id: str, request_id: str, line_amounts: list[str]) -> None:
    InvoiceJobHandler(tenant_id, request_id, line_amounts).run()
