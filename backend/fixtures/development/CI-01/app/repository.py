from typing import Dict, Optional

# In-memory storage for the development fixture
# Maps tenant_id -> { request_id -> receipt_dict }
_store: Dict[str, Dict[str, dict]] = {}

def get_receipt(tenant_id: str, request_id: str) -> Optional[dict]:
    return _store.get(tenant_id, {}).get(request_id)

def save_receipt(tenant_id: str, request_id: str, receipt: dict) -> None:
    if tenant_id not in _store:
        _store[tenant_id] = {}
    _store[tenant_id][request_id] = receipt
