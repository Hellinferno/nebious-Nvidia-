from typing import List

from pydantic import BaseModel, Field


class InvoiceRequest(BaseModel):
    tenant_id: str = Field(description="Owning tenant")
    request_id: str = Field(description="Client-chosen idempotency key")
    line_amounts: List[str] = Field(description="Decimal strings, one per line")


class ReceiptResponse(BaseModel):
    receipt_id: str
    tenant_id: str
    request_id: str
    total_amount: str
    status: str


class ReceiptSummary(BaseModel):
    """Aggregate view used by reporting tools; not part of the submit flow."""

    tenant_id: str
    receipt_count: int
