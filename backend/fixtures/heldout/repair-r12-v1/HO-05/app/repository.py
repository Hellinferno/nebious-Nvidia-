from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StoredReceipt:
    line_amounts: list[str]
    response: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"line_amounts": list(self.line_amounts), "response": dict(self.response)}


_by_tenant: dict[str, dict[str, StoredReceipt]] = {}


def get_receipt(tenant_id: str, request_id: str) -> Optional[dict]:
    stored = _by_tenant.get(tenant_id, {}).get(request_id)
    return stored.to_dict() if stored else None


def save_receipt(tenant_id: str, request_id: str, receipt: dict) -> None:
    bucket = _by_tenant.setdefault(tenant_id, {})
    bucket[request_id] = StoredReceipt(
        line_amounts=list(receipt["line_amounts"]), response=dict(receipt["response"])
    )
