from collections import defaultdict
from typing import Optional

_receipts: dict[str, dict[str, dict]] = defaultdict(dict)


def get_receipt(tenant_id: str, request_id: str) -> Optional[dict]:
    return _receipts[tenant_id].get(request_id)


def save_receipt(tenant_id: str, request_id: str, receipt: dict) -> None:
    _receipts[tenant_id][request_id] = receipt


def count_receipts(tenant_id: str) -> int:
    return len(_receipts[tenant_id])
