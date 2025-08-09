"""Utility helpers for PFTL."""

from __future__ import annotations

import random
import string
from typing import Iterable


def generate_code(length: int = 6) -> str:
    """Generate a short uppercase alphanumeric game code."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


def clamp(value: int, minimum: int, maximum: int) -> int:
    """Clamp integer value between minimum and maximum inclusive."""
    return max(minimum, min(value, maximum))


def sum_attr(items: Iterable, attr: str) -> int:
    """Sum integer attribute attr across items, ignoring missing values."""
    total = 0
    for item in items:
        total += int(getattr(item, attr, 0) or 0)
    return total
