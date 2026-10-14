"""Invoice arithmetic helpers."""

from decimal import ROUND_HALF_UP, Decimal
from functools import reduce
from typing import Iterable

CENT = Decimal("0.01")


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def compute_total(lines: Iterable[str]) -> str:
    """Return the invoice total as a two-decimal string."""
    amounts = [Decimal(text) for text in lines]
    if not amounts:
        return "0.00"
    total = reduce(lambda acc, amount: acc + amount, amounts, Decimal("0"))
    return str(_quantize(total))


def preview_line(line: str) -> str:
    """Display-only formatting for a single line in the operator console."""
    return str(_quantize(Decimal(line)))
