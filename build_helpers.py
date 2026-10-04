"""
Helpers shared by the campus-building scripts in tools/.

Deliberately tiny and dependency-free: the point of these functions is that
anyone can check the arithmetic by hand.
"""

from __future__ import annotations

import math

# Origin of the local metre grid: the centre of the OSM "GGSIPU East Delhi
# Campus" landuse polygon (way/1186490427).
ORIGIN_LAT, ORIGIN_LON = 28.66443, 77.30083
METRES_PER_DEG_LAT = 111_320.0


def osm_to_metres(lat: float, lon: float) -> tuple[float, float]:
    """
    OpenStreetMap lat/lon -> (x east, y SOUTH) metres on the campus grid.

    An equirectangular projection, which is exact to well under a metre over
    a campus-sized area (the error grows with distance from the origin).
    y increases southwards so the SVG y axis needs no flipping.
    """
    m_per_deg_lon = METRES_PER_DEG_LAT * math.cos(math.radians(ORIGIN_LAT))
    x = (lon - ORIGIN_LON) * m_per_deg_lon
    y = (ORIGIN_LAT - lat) * METRES_PER_DEG_LAT
    return round(x, 1), round(y, 1)
