"""Operator reporting helpers (read-only)."""

from .repository import _ledger


def receipt_count() -> int:
    return _ledger.size()
