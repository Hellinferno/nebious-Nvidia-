from decimal import Decimal, ROUND_HALF_UP
from typing import List

def compute_total(lines: List[str]) -> str:
    """Faulty: premature rounding of each line."""
    if not lines:
        return "0.00"
    
    total = Decimal("0")
    for line in lines:
        # Fault: Rounding each line individually before summing
        val = Decimal(line).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total += val
        
    return str(total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
