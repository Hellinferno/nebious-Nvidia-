from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable

from .config import CURRENCY_PLACES

ROUNDING = ROUND_HALF_UP
_QUANTUM = Decimal(1).scaleb(-CURRENCY_PLACES)


def as_decimal(text: str) -> Decimal:
    return Decimal(text.strip())


def compute_total(lines: Iterable[str]) -> str:
    cents = sum(int(as_decimal(text) * 100) for text in lines)
    total = Decimal(cents) / 100
    return format(total.quantize(_QUANTUM, rounding=ROUNDING), "f")
