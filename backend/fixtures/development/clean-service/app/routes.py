from fastapi import APIRouter, HTTPException
from .schemas import InvoiceRequest, ReceiptResponse
from .services import process_invoice, ConflictError

router = APIRouter()

@router.post("/invoices", response_model=ReceiptResponse)
def submit_invoice(req: InvoiceRequest):
    try:
        return process_invoice(req)
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
