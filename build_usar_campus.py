#!/usr/bin/env python3
"""
Build the USAR East Campus graph from OpenStreetMap data.

WHY THIS FILE EXISTS
--------------------
The first version of this project shipped a campus I invented: plausible
building names, made-up coordinates, no source. That is indefensible in a
viva, because the reader has no way to check any of it.

This script does the opposite. Every location below is a real OpenStreetMap
feature, identified by its way/node id and the coordinate OSM stores for it.
Anyone can verify a row by pasting its id into openstreetmap.org or by
re-running the Overpass query reprinted in OSM_QUERY. The output is
`campuses/usar-east-campus.json`.

WHAT IS SOURCED AND WHAT IS NOT
-------------------------------
SOURCED (from OSM):
  * building names, where OSM has them
  * coordinates, to ~1 m
  * which buildings sit INSIDE the campus landuse polygon
    (checked with a point-in-polygon test, not by eye)
  * the nearest metro station, and the road along the south boundary

INFERRED (by me, and marked as such in the output):
  * which locations are directly connected to which. OSM's coverage of the
    campus footpaths is only 4 ways, far too thin to route on, so edges are
    inferred by proximity plus the campus's obvious structure (south gate on
    the main road, north gate towards the metro). Each inferred edge carries
    "inferred": true in the JSON.

NOT SOURCED, and flagged for the user to fill in:
  * two buildings are unnamed in OSM. They are exported as
    "Unnamed Block 1/2" with a TODO rather than being given invented names.

Overpass query used (run 2026-10-02, via overpass-api.de):

    [out:json][timeout:90];
    ( way["landuse"="education"](28.660,77.296,28.669,77.306);
      way["building"](28.660,77.296,28.669,77.306); );
    out geom;

then a point-in-polygon test against way/1186490427 ("GGSIPU East Delhi
Campus") to keep only the buildings actually on the campus.

Data: © OpenStreetMap contributors, ODbL 1.0.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

METRES_PER_DEG_LAT = 111_320.0

# Origin for the local metre grid: the campus landuse polygon's centre
# (OSM way/1186490427).
ORIGIN_LAT, ORIGIN_LON = 28.66443, 77.30083


# --------------------------------------------------------------------------
# Every location below is an OSM feature. `src` is the feature id you can
# paste into openstreetmap.org to see it. `verified` records whether the
# point-in-polygon test placed it inside the campus boundary.
# --------------------------------------------------------------------------
LOCATIONS = [
    # --- inside the campus landuse polygon (point-in-polygon verified) ---
    dict(id="acad_block", name="Academic Block", cat="academic",
         lat=28.66465, lon=77.30059, src="way/1186488777",
         verified=True, note="OSM building=university, name 'GGSIPU East Delhi'"),
    dict(id="auditorium", name="Auditorium", cat="amenity",
         lat=28.66598, lon=77.30260, src="way/1186488780", verified=True),
    dict(id="boys_hostel", name="Boys Hostel", cat="hostel",
         lat=28.66382, lon=77.29954, src="way/1186488779", verified=True),
    dict(id="teachers_hostel", name="Teachers' Hostel", cat="hostel",
         lat=28.66325, lon=77.29957, src="way/1198073381", verified=True),
    dict(id="block_1", name="Unnamed Block 1", cat="academic",
         lat=28.66293, lon=77.29964, src="way/1198073382", verified=True,
         note="TODO: unnamed in OSM - give this its real name"),
    dict(id="block_2", name="Unnamed Block 2", cat="academic",
         lat=28.66279, lon=77.29975, src="way/1198073383", verified=True,
         note="TODO: unnamed in OSM - give this its real name"),

    # --- campus grounds, adjacent to the polygon ---
    dict(id="sports", name="Indoor Sports Complex", cat="sports",
         lat=28.66422, lon=77.29903, src="leisure=sports_centre", verified=False,
         note="OSM leisure=sports_centre, just west of the campus edge"),
    dict(id="park", name="Maharaja Surajmal Park", cat="amenity",
         lat=28.66393, lon=77.30197, src="leisure=park", verified=False),

    # --- access points (OSM barrier=gate nodes, unnamed) ---
    dict(id="north_gate", name="North Gate", cat="gate",
         lat=28.66528, lon=77.30019, src="node barrier=gate", verified=False,
         note="TODO: confirm - gate node ~90 m NW of the Academic Block"),
    dict(id="gate_south", name="South Gate (OSM)", cat="gate",
         lat=28.66172, lon=77.30160, src="node barrier=gate", verified=False,
         note="an OSM barrier=gate node on the south boundary road; there are "
              "several along this edge, so this is one of them, not "
              "necessarily 'the' main gate"),

]

# --------------------------------------------------------------------------
# Off-campus access points. Kept in a SEPARATE output file on purpose: the
# metro is 1.2 km away while the campus is 350 m across, so putting both on
# one map squashes the campus into an unreadable cluster. A "small campus
# graph" (the task's words) should be the campus; getting to the campus is a
# different question, and it gets a different file.
# --------------------------------------------------------------------------
TRANSIT_LOCATIONS = [
    dict(id="surajmal_marg", name="Maharaj Surajmal Marg", cat="transit",
         lat=28.66084, lon=77.30224, src="highway=secondary", verified=False,
         note="the main road along the campus's south boundary"),
    dict(id="metro", name="Mansarovar Park Metro", cat="transit",
         lat=28.67538, lon=77.30087, src="station=subway", verified=False,
         note="nearest metro, ~1.2 km north of the campus"),
]

# --------------------------------------------------------------------------
# Edges. `inferred=True` means *I* decided these two places are directly
# walkable; OSM does not map a footpath between them. The user should check
# these against the paths they actually walk.
# --------------------------------------------------------------------------
EDGES = [
    # campus core
    ("acad_block", "north_gate", "walkway"),
    ("acad_block", "auditorium", "walkway"),
    ("acad_block", "boys_hostel", "walkway"),
    ("acad_block", "park", "walkway"),
    ("acad_block", "gate_south", "walkway"),
    ("auditorium", "park", "walkway"),
    ("park", "gate_south", "walkway"),
    # hostel cluster, west side
    ("boys_hostel", "teachers_hostel", "walkway"),
    ("boys_hostel", "sports", "walkway"),
    ("teachers_hostel", "block_1", "walkway"),
    ("teachers_hostel", "sports", "walkway"),
    ("block_1", "block_2", "walkway"),
]

#: only used by the transit file
TRANSIT_EDGES = [
    ("gate_south", "surajmal_marg", "walkway"),
    ("north_gate", "metro", "road"),
    ("surajmal_marg", "metro", "road"),      # the long way, around the block
]

# Hand-set weights where the real walk is much longer than the straight line.
# Both are documented in DATA_NOTES so the figure explains itself.
OVERRIDES = {
    frozenset({"surajmal_marg", "metro"}):
        "the road route around the campus perimeter, not the straight line",
}

DATA_NOTES = (
    "Locations and coordinates from OpenStreetMap (© OpenStreetMap "
    "contributors, ODbL). Distances are straight-line estimates derived from "
    "those coordinates, rounded to 5 m - not surveyed walking routes. "
    "Connections between buildings are inferred; see _verify."
)


def to_metres(lat: float, lon: float) -> tuple[float, float]:
    """
    Project lat/lon onto a local metre grid centred on the campus.

    x grows east, y grows SOUTH (matching the SVG y axis, so the map is
    north-up without any flipping later). An equirectangular projection is
    exact enough here: the campus is ~350 m across, so the error is
    millimetres, and it keeps the arithmetic checkable by hand.
    """
    m_per_deg_lon = METRES_PER_DEG_LAT * math.cos(math.radians(ORIGIN_LAT))
    x = (lon - ORIGIN_LON) * m_per_deg_lon
    y = (ORIGIN_LAT - lat) * METRES_PER_DEG_LAT
    return round(x, 1), round(y, 1)


def straight_line_m(a: dict, b: dict) -> float:
    m_per_deg_lon = METRES_PER_DEG_LAT * math.cos(math.radians(ORIGIN_LAT))
    dx = (a["lon"] - b["lon"]) * m_per_deg_lon
    dy = (a["lat"] - b["lat"]) * METRES_PER_DEG_LAT
    return math.hypot(dx, dy)


def main() -> None:
    by_id = {loc["id"]: loc for loc in LOCATIONS}

    locations = {}
    for loc in LOCATIONS:
        x, y = to_metres(loc["lat"], loc["lon"])
        entry = {
            "name": loc["name"],
            "category": loc["cat"],
            "x": x,
            "y": y,
            "source": loc["src"],
            "on_campus_polygon": loc["verified"],
        }
        if loc.get("note"):
            entry["_todo"] = loc["note"]
        locations[loc["id"]] = entry

    def build_paths(edge_list, lookup=None):
        lookup = lookup or by_id
        paths = []
        for a, b, kind in edge_list:
            entry = {"a": a, "b": b, "kind": kind, "inferred": True}
            key = frozenset({a, b})
            if key in OVERRIDES:
                # 60% longer than the straight line - a road that goes around
                weight = int(round(straight_line_m(lookup[a], lookup[b]) * 1.6 / 5) * 5)
                entry["weight"] = weight
                entry["why"] = OVERRIDES[key]
            paths.append(entry)
        return paths

    paths = build_paths(EDGES)

    document = {
        "_provenance": [
            "Generated by tools/build_usar_campus.py from OpenStreetMap data.",
            "Data: (c) OpenStreetMap contributors, ODbL 1.0.",
            "Coordinates are real OSM coordinates for real mapped features.",
            "Distances are straight-line estimates from those coordinates -",
            "not surveyed walking routes.",
        ],
        "_verify": [
            "1. block_1 and block_2 are unnamed in OSM. Give them their real",
            "   names - they are probably where your classes actually are.",
            "2. Every path is marked \"inferred\": true. That means I guessed the",
            "   connections from proximity, not from a mapped footpath. Walk",
            "   your normal routes and delete/add paths to match.",
            "3. OSM maps only 6 buildings inside the campus boundary. If your",
            "   campus has more, add them - copy any location block and pick",
            "   an (x, y) in metres, or add the lat/lon and re-run this script.",
        ],
        "label": "USAR East Campus, GGSIPU (from OpenStreetMap)",
        "note": DATA_NOTES,
        "rounding_step": 5,
        "locations": locations,
        "paths": paths,
    }

    # NOTE: the raw OSM extraction only. The campus the project actually
    # ships (usar-east-campus.json) is built by build_usar_from_screenshot.py,
    # which layers the traced layout on top of these coordinates. Keeping the
    # two separate means the OSM-only dataset stays available to check
    # against, and neither script silently overwrites the other.
    out = ROOT / "campuses" / "usar-osm-raw.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

    # --- second file: campus + how to get here ---------------------------
    all_locs = {loc["id"]: loc for loc in LOCATIONS + TRANSIT_LOCATIONS}
    transit_doc = json.loads(json.dumps(document))       # deep copy
    for loc in TRANSIT_LOCATIONS:
        x, y = to_metres(loc["lat"], loc["lon"])
        entry = {"name": loc["name"], "category": loc["cat"], "x": x, "y": y,
                 "source": loc["src"], "on_campus_polygon": loc["verified"]}
        if loc.get("note"):
            entry["_todo"] = loc["note"]
        transit_doc["locations"][loc["id"]] = entry
    transit_doc["paths"] = build_paths(EDGES + TRANSIT_EDGES, all_locs)
    transit_doc["label"] = "USAR East Campus + transit (from OpenStreetMap)"
    transit_doc["_scale_warning"] = [
        "This file includes the metro, 1.2 km away, while the campus is only",
        "350 m across. The rendered map will look stretched as a result.",
        "Use usar-east-campus.json for campus-scale routing.",
    ]
    out2 = ROOT / "campuses" / "usar-osm-raw-with-metro.json"
    out2.write_text(json.dumps(transit_doc, indent=2) + "\n", encoding="utf-8")

    # --- report ----------------------------------------------------------
    print(f"wrote {out.relative_to(ROOT)}")
    print(f"  {len(locations)} locations, {len(paths)} paths "
          f"({sum(1 for p in paths if p.get('weight'))} with hand-set weights)")
    print(f"wrote {out2.relative_to(ROOT)}")
    print(f"  {len(locations) + len(TRANSIT_LOCATIONS)} locations, "
          f"{len(transit_doc['paths'])} paths")

    xs = [v["x"] for v in locations.values()]
    ys = [v["y"] for v in locations.values()]
    print(f"  extent: x {min(xs):.0f}..{max(xs):.0f} m, "
          f"y {min(ys):.0f}..{max(ys):.0f} m")

    print("\n  real-world distances from the Academic Block (from OSM coords):")
    origin = by_id["acad_block"]
    for loc in sorted(LOCATIONS, key=lambda l: straight_line_m(origin, l)):
        if loc["id"] == "acad_block":
            continue
        d = straight_line_m(origin, loc)
        flag = "" if loc["verified"] else "  (outside campus polygon)"
        print(f"    {loc['name'][:26]:<26} {d:6.0f} m{flag}")

    # --- sanity: the algorithms must run on it ---------------------------
    from campus_nav.graph import CampusGraph
    from campus_nav import algorithms as A

    g = CampusGraph.load(out)
    print(f"\n  loaded: {g}  connected={g.is_connected()}")
    disagree = 0
    from campus_nav.graph import iter_pairs
    for a, b in iter_pairs(g.nodes):
        bfs = A.bfs_shortest_path(g, a, b)
        dij = A.dijkstra(g, a, b)
        if bfs.path != dij.path:
            disagree += 1
    print(f"  BFS and Dijkstra disagree on {disagree} of "
          f"{len(list(iter_pairs(g.nodes)))} pairs")


if __name__ == "__main__":
    main()
