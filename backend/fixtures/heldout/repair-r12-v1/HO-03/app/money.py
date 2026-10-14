from decimal import ROUND_HALF_UP, Decimal
from typing import List


def compute_total(lines: List[str]) -> str:
    running = Decimal("0")
    for text in lines:
        running += Decimal(text)
    return str(running.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def split_even(total: str, parts: int) -> List[str]:
    """Split a settled total into equal parts for installment previews."""
    share = (Decimal(total) / parts).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return [str(share)] * parts
