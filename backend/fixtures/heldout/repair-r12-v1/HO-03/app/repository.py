from typing import Optional

_receipts: dict[str, dict] = {}


def _key(tenant_id: str, request_id: str) -> str:
    return f"{tenant_id}/{request_id}"


def get_receipt(tenant_id: str, request_id: str) -> Optional[dict]:
    return _receipts.get(_key(tenant_id, request_id))


def save_receipt(tenant_id: str, request_id: str, receipt: dict) -> None:
    _receipts[_key(tenant_id, request_id)] = receipt
