from fastapi import APIRouter, HTTPException

from .schemas import InvoiceRequest, ReceiptResponse
from .services import ConflictError, process_invoice

router = APIRouter()


@router.post("/invoices", response_model=ReceiptResponse, status_code=201)
def submit_invoice(req: InvoiceRequest):
    try:
        return process_invoice(req)
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
