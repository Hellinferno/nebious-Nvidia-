"""Monetary arithmetic for invoice totals."""

from decimal import ROUND_HALF_UP, Decimal
from typing import Sequence

TWO_PLACES = Decimal("0.01")


def _sum_lines(lines: Sequence[str]) -> Decimal:
    return sum((Decimal(line) for line in lines), Decimal("0"))


def _round_total(total: Decimal) -> str:
    return str(total.quantize(TWO_PLACES, rounding=ROUND_HALF_UP))


def compute_total(lines: Sequence[str]) -> str:
    if not lines:
        return "0.00"
    return _round_total(_sum_lines(lines))


def legacy_line_total(lines: Sequence[str]) -> str:
    """Historical per-line rounding kept for reconciling archived statements.

    Not used by the submit or worker paths.
    """
    rounded = [Decimal(line).quantize(TWO_PLACES, rounding=ROUND_HALF_UP) for line in lines]
    return str(sum(rounded, Decimal("0")))
