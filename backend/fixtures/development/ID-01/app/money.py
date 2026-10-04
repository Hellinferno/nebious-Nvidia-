from decimal import Decimal, ROUND_HALF_UP
from typing import List

def compute_total(lines: List[str]) -> str:
    """Sum unrounded line amounts, then ROUND_HALF_UP once on the invoice total."""
    if not lines:
        return "0.00"
    total = sum((Decimal(line) for line in lines), Decimal("0"))
    return str(total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
