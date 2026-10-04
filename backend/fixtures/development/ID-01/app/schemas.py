from pydantic import BaseModel
from typing import List

class InvoiceRequest(BaseModel):
    tenant_id: str
    request_id: str
    line_amounts: List[str]

class ReceiptResponse(BaseModel):
    receipt_id: str
    tenant_id: str
    request_id: str
    total_amount: str
    status: str
