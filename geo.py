"""
Pure geometry helpers - no imports, so both `data.py` (the built-in sample)
and `loader.py` (external campus files) can share exactly one formula for
deriving a pathway length from map coordinates.
"""

from __future__ import annotations

DEFAULT_ROUNDING_STEP = 5  # metres


def euclidean(x1: float, y1: float, x2: float, y2: float) -> float:
    """Straight-line distance between two points on the campus grid."""
    return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5


def derive_weight(
    x1: float, y1: float, x2: float, y2: float,
    step: int = DEFAULT_ROUNDING_STEP,
) -> int:
    """
    Walking distance for a pathway whose length is not given explicitly:
    the straight-line distance, rounded to the nearest `step` metres.

    Rounding to 5 m keeps the numbers on the map readable ('85' instead of
    '84.7') and is what makes the A* heuristic need the 0.95 safety factor -
    see DECISIONS.md #4.
    """
    distance = euclidean(x1, y1, x2, y2)
    if distance == 0:
        raise ValueError("two locations share the same coordinates")
    return max(step, int(round(distance / step) * step))
