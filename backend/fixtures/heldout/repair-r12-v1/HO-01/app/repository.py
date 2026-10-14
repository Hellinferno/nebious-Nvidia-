"""In-memory receipt ledger keyed by tenant and request."""

from typing import Optional


class ReceiptLedger:
    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], dict] = {}

    def find(self, tenant_id: str, request_id: str) -> Optional[dict]:
        return self._entries.get((tenant_id, request_id))

    def put(self, tenant_id: str, request_id: str, receipt: dict) -> None:
        self._entries[(tenant_id, request_id)] = receipt

    def size(self) -> int:
        return len(self._entries)


_ledger = ReceiptLedger()


def get_receipt(tenant_id: str, request_id: str) -> Optional[dict]:
    return _ledger.find(tenant_id, request_id)


def save_receipt(tenant_id: str, request_id: str, receipt: dict) -> None:
    _ledger.put(tenant_id, request_id, receipt)
