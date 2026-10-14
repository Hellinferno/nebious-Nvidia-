from fastapi import APIRouter, HTTPException, status

from .schemas import InvoiceRequest, ReceiptResponse
from .services import ConflictError, process_invoice

router = APIRouter()


@router.post("/invoices", response_model=ReceiptResponse)
def submit_invoice(req: InvoiceRequest):
    try:
        return process_invoice(req)
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
