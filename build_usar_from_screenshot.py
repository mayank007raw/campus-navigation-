#!/usr/bin/env python3
"""
Build the USAR campus layout from the Google Maps screenshot.

WHY THIS EXISTS
---------------
OpenStreetMap's coverage of this campus is thin: 6 buildings inside the
boundary, 4 footpaths, and it disagrees with Google about where Surajmal
Park is. A satellite screenshot shows the actual layout - the ground, the
road along the south edge, the building cluster - so this script derives
coordinates from the pixels of that screenshot.

HOW THE PIXELS BECOME METRES
----------------------------
Two known points anchor the image:

  A. the USAR map pin, which Google places on the campus building
     -> equals the OpenStreetMap "Academic Block" (way/1186488777)
        at 28.66465 N, 77.30059 E, i.e. (-23, -25) m on our grid
  B. the OSM gate nodes on the south boundary at 28.66172 N
     -> 303 m south of the grid origin, and they sit on the road the
        screenshot labels "Gurdwara Rd"

In the screenshot those two are 213 pixels apart vertically, and they are
328 m apart on the ground, giving a scale of 1.54 m/px. One scale serves
both axes because a north-up web map is square.

    x_metres = -23 + (px - 345) * 1.54      (east is +x)
    y_metres = -25 + (py - 713) * 1.54      (south is +y)

Distance from the campus:
  * campus-scale locations (within ~350 m) go into usar-east-campus.json
  * landmarks 400 m+ away (the Leela, Smriti Park, the metro) would stretch
    a 350 m campus into a sliver, so they go into a separate context file

WHAT IS SOURCED AND WHAT IS MEASURED
------------------------------------
"source": "osm:way/..."    real surveyed OSM coordinate
"source": "screenshot"     estimate from the supplied screenshot, +/- a few
                           metres. Every one of these needs a human check.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# --- screenshot calibration ------------------------------------------------
PIN_PX = (345.0, 713.0)     # Google's USAR pin
PIN_M = (-23.4, -24.5)      # OSM Academic Block, way/1186488777
M_PER_PX = 1.54             # derived from the 213 px / 328 m anchor above


def to_metres(px: float, py: float) -> tuple[float, float]:
    """Pixel in the screenshot -> (x east, y south) metres on our grid."""
    x = PIN_M[0] + (px - PIN_PX[0]) * M_PER_PX
    y = PIN_M[1] + (py - PIN_PX[1]) * M_PER_PX
    return round(x, 1), round(y, 1)


# --- measured pixel positions ---------------------------------------------
# Read off Screenshot_2026-10-02 (702 x 1568). Label centroids for text,
# marker pixels for pins.
MEASURED = {
    "park":           (305, 558),   # "Maharaja Surajmal Park" pin
    # CORRECTION 10: "make the gate 2 in between a block and b block".
    # Refines correction 7 - it is still the west-side gate on the
    # auditorium's lane, but it now sits in the gap between the two blocks,
    # which is what makes "left to Block A, right to Block B" literally true.
    "gate_2":         (252, 680),   # in the gap between Block A and Block B
    "gurdwara_road":  (345, 935),   # road centreline at the same x
    "leela":          (270, 315),   # The Leela Ambience Convention Hotel
    "glorious":       (580, 405),   # Glorious Banquet
    "smriti_park":    (215, 45),    # Smriti Park, far north
    "b_block":        (200, 17),    # B Block, far north
    "road_60_feet":   (455, 1219),  # 60 Feet Road, far south
}

# --- OSM-sourced locations (real surveyed coordinates) --------------------
from campus_nav.build_helpers import osm_to_metres  # noqa: E402

OSM_LOCATIONS = [
    # CORRECTION 2 (from the student): the main building is called Block A.
    # OSM tags this building "GGSIPU East Delhi" (building=university) - the
    # OSM name is kept in the note rather than thrown away.
    ("block_a",          "Block A (USAR)", "academic",
     "way/1186488777", 28.66465, 77.30059),
    ("auditorium",       "Auditorium",              "amenity",
     "way/1186488780", 28.66598, 77.30260),
    ("boys_hostel",      "Boys Hostel",             "hostel",
     "way/1186488779", 28.66382, 77.29954),
    # CORRECTION 9: the student removed three buildings from the map -
    # Teachers' Hostel, and the two blocks OSM leaves unnamed. They are real
    # OSM features, so they are NOT deleted from the record: they remain in
    # campuses/usar-osm-raw.json, which is the untouched OSM extraction.
    # Dropping them here just means they are not on the campus map.
    # CORRECTION 5: the student calls this the sports hall; OSM calls it
    # "Indoor Sports complex" (leisure=sports_centre). The OSM name is kept.
    ("sports",           "Sports Hall",             "sports",
     "leisure=sports_centre", 28.66422, 77.29903),
    # CORRECTION 1 (from the student): "there are two gates, one has the
    # auditorium on its side". OSM has a barrier=gate node on the EAST
    # boundary at 28.66583, 77.30370 - which converts to 109 m from the
    # Auditorium, exactly as described. The campus's south-side gate nodes
    # are ~480 m away, so this is unambiguously the one being described.
    # CORRECTION 1: the auditorium-side gate. The student numbers the gates:
    # this is Gate 1.
    ("gate_1",           "Gate 1",                  "gate",
     "node barrier=gate", 28.66583, 77.30370),
]

# --- screenshot-measured locations ---------------------------------------
SCREENSHOT_CAMPUS = [
    # CORRECTION 12: "the usar ground to be removed" - the open ground is no
    # longer a location in the graph. It is still in the screenshot.
    # CORRECTION 7: Gate 2 is the WEST gate, on the auditorium lane -
    # "completely opposite direction and in the lane of auditorium".
    # OSM has barrier=gate nodes at (-66,-92) and (-59,-97) on this side.
    ("gate_2",      "Gate 2", "gate"),
]

# CORRECTION 3: "when you enter from gate 2 ... right to Block B", and
# CORRECTION 5: "turn left and straight sports hall comes, on its side there
# is outdoor ground, behind this there are hostel boys and girls".
#
# Block B, the outdoor ground and the girls' hostel are NOT named anywhere in
# OpenStreetMap, so their POSITIONS are estimated from the student's verbal
# description. The topology (what connects to what) comes from the student;
# only the coordinates are guessed, and they are flagged as such.
DESCRIBED_CAMPUS = [
    # CORRECTION 8: Block B is ONE BUILDING, not a complex, and it is close
    # to Block A - the student: "it's only one building, why you taking
    # Block B so far away from Block A, then in between library at 5 floor
    # and then Block B". So the order walking from Block A is
    #     Block A -> Library -> Block B
    # CORRECTION 11: "in path from gate 1 to block A, parking comes in
    # between" - so the Parking sits on that route
    ("parking",        "Parking",        "amenity",  129, -90,
     "on the path from Gate 1 to Block A"),
    # CORRECTION 13 (video): the campus tour is explicit that the canteen is
    # its own block - "D-Block is our canteen" - and that it is downstairs.
    # This reverses correction 12, where the canteen came off the map because
    # the student said it was inside Block B.
    ("canteen",        "Canteen (D-Block)", "amenity", -136,  39,
     "the end of Block B, toward the Sports Hall"),
    ("library",        "Library (C-Block)", "academic",  -60,  20,
     "between Block A and Block B; student says the library is on the 5th floor"),
    ("block_b",        "Block B (USDI)", "academic",  -95,  55,
     "one building, immediately past the Library from Block A"),
    # CORRECTION 10: "sport hall and outdoor ground is side to side and
    # behind girl and boy hostel" - the two sports facilities sit next to
    # each other on one line, with the two hostels behind them.
    ("outdoor_ground", "Outdoor Ground", "sports",  -250,   23,
     "side by side with the Sports Hall"),
    ("boys_hostel",    "Boys Hostel",    "hostel",  -180,  140,
     "behind the Sports Hall"),
    ("girls_hostel",   "Girls' Hostel",  "hostel",  -250,  140,
     "behind the Outdoor Ground"),
]

SCREENSHOT_CONTEXT = [
    # CORRECTION 3: "the park is not in my campus" - it is a neighbouring
    # park, so it is kept for orientation but moved out of the campus graph.
    ("park",        "Maharaja Surajmal Park", "amenity"),
    # likewise the boundary road: it is not a destination, and once Gate 2
    # left the south side nothing on campus needed to connect to it
    ("gurdwara_road", "Gurdwara Rd", "transit"),
    ("leela",       "The Leela Ambience", "amenity"),
    ("glorious",    "Glorious Banquet", "amenity"),
    ("smriti_park", "Smriti Park", "amenity"),
    ("b_block",     "B Block", "academic"),
    ("road_60_feet", "60 Feet Road", "transit"),
]

# --- connections (all inferred - OSM maps only 4 footpaths here) ---------
# The campus tour that settled the block names: a student walks the campus
# and says what each block is.
TOUR_URL = "https://www.youtube.com/watch?v=oyGoBPmT7c0"

NOTES = {
    "library": "student: the library is on the 5th floor",
}

TOUR_EVIDENCE = {
    "block_a": "A-Block - 'the first block is our USAR, which we call A-Block'",
    "block_b": "B-Block - 'B-Block is for USDI, which is the design block'",
    "library": "C-Block - 'the third block is our C-Block, which is the library'",
    "canteen": "D-Block - 'D-Block is our canteen', and 'our canteen is downstairs'",
    "sports": "'there is our sports hall over there'; badminton and table tennis inside",
    "outdoor_ground": "news: 'along with the sports hall, 2 tennis courts and a football field'",
    "auditorium": "news: a 5-storey auditorium block, capacity 650",
}

CAMPUS_EDGES = [
    # CORRECTION 3/4: Gate 2 - "going straight, left you connect to Block A,
    # right to Block B"
    ("gate_2",          "block_a",        "walkway"),
    ("gate_2",          "block_b",        "walkway"),
    # CORRECTION 8: no direct Block A <-> Block B path - you go past the
    # Library to get there, which is what the student described
    # CORRECTION 8: the Library sits between Block A and Block B
    ("block_a",         "library",        "walkway"),
    ("library",         "block_b",        "walkway"),
    # CORRECTION 11 route, now supported by the tour's D-Block
    ("block_b",         "canteen",        "walkway"),
    ("canteen",         "sports",         "walkway"),
    # the west cluster hangs off the Library / Block B side
    ("library",         "sports",         "walkway"),
    # Gate 2 - "turn left and straight the sports hall comes"
    ("gate_2",          "sports",         "walkway"),

    # CORRECTION 1/2: Gate 1 is the auditorium-side gate, and its path
    # leads to the main building, Block A
    ("gate_1",          "parking",        "walkway"),
    ("parking",         "block_a",        "walkway"),
    ("gate_1",          "auditorium",     "walkway"),

    ("block_a",         "auditorium",     "walkway"),

    # CORRECTION 9: the Sports Hall and Outdoor Ground are in FRONT; the
    # hostels sit behind them.
    ("sports",          "outdoor_ground", "walkway"),
    ("sports",          "boys_hostel",    "walkway"),
    ("outdoor_ground",  "girls_hostel",   "walkway"),
    ("boys_hostel",     "girls_hostel",   "walkway"),

    # the campus's other link into the west complex
    ("block_a",         "boys_hostel",    "walkway"),
    ("block_a",         "sports",         "walkway"),

]

CONTEXT_EDGES = [
    ("gate_2",      "gurdwara_road", "road"),
    ("gate_2",      "park",         "road"),
    ("park",        "leela",        "road"),
    ("leela",       "smriti_park",  "road"),
    ("smriti_park", "b_block",      "road"),
    ("gurdwara_road", "road_60_feet", "road"),
    ("block_a",     "gurdwara_road", "road"),
]

CAMPUS_LABEL = "USAR East Campus, GGSIPU (from screenshot + OpenStreetMap)"
CAMPUS_NOTE = (
    "Schematic layout traced from a Google Maps satellite view of the USAR "
    "campus, Surajmal Vihar. Building coordinates are OpenStreetMap; roads "
    "and grounds are measured from the screenshot to about +/-10 m. This is "
    "not a survey - check the positions against the campus."
)


def main() -> None:
    from campus_nav import geo

    campus_locations: dict = {}
    for node_id, name, cat, src, lat, lon in OSM_LOCATIONS:
        x, y = osm_to_metres(lat, lon)
        entry = {
            "name": name, "category": cat, "x": x, "y": y,
            "source": f"osm:{src}",
        }
        if node_id == "block_a":
            entry["_osm_name"] = "GGSIPU East Delhi (building=university)"
            entry["_renamed_by"] = "student: 'the main building is Block A'"
        if node_id == "sports":
            entry["_osm_name"] = "Indoor Sports complex (leisure=sports_centre)"
            entry["_renamed_by"] = "student: 'straight sports hall comes'"
        campus_locations[node_id] = entry

    for node_id, name, cat in SCREENSHOT_CAMPUS:
        px, py = MEASURED[node_id]
        x, y = to_metres(px, py)
        campus_locations[node_id] = {
            "name": name, "category": cat, "x": x, "y": y,
            "source": "screenshot",
            "measured_at_px": [px, py],
        }

    # Per-location notes: things a 2-D graph cannot express. FIX - this used
    # to assign to `entry`, a leftover loop variable from the OSM locations
    # above, so the Library's "5th floor" note was attached to Gate 1.
    # Notes are now keyed by node id.
    for node_id, name, cat, x, y, why in DESCRIBED_CAMPUS:
        campus_locations[node_id] = {
            "name": name, "category": cat, "x": float(x), "y": float(y),
            "source": "described",
            "position_estimate": why,
        }

    # Notes and tour corroboration, applied AFTER every location is built so
    # they can target any node whatever its source. This used to write to
    # `entry`, a leftover loop variable from the OSM parsing, which filed the
    # Library's "5th floor" note under Gate 1 for four corrections.
    for node_id, text in NOTES.items():
        campus_locations[node_id]["_note"] = text

    # What the campus tour says about each location, quoted, so a reader can
    # check a name against the source instead of trusting this file.
    for node_id, text in TOUR_EVIDENCE.items():
        if node_id in campus_locations:
            campus_locations[node_id]["_tour_evidence"] = text

    campus_paths = [
        {"a": a, "b": b, "kind": k, "inferred": True}
        for a, b, k in CAMPUS_EDGES
    ]

    campus_doc = {
        "_provenance": [
            "Block names A/B/C/D come from a student campus tour of USAR:",
            "  " + TOUR_URL,
            "  A-Block USAR | B-Block USDI | C-Block library | D-Block canteen.",
            "Storey counts, capacities and the separate library block come from",
            "India Today's 2022 report on this campus (18.75 acres, two 9-storey",
            "and one 7-storey academic buildings, a 5-storey auditorium block).",
            "Layout traced from a Google Maps screenshot of the USAR campus,",
            "cross-referenced with OpenStreetMap building coordinates.",
            "OSM data: (c) OpenStreetMap contributors, ODbL 1.0.",
            "Google base imagery is not redistributed - only the derived",
            "relative positions, which are approximations.",
        ],
        "_verify": [
            "HOW TO CHECK THIS FILE. Every location declares its own source:",
            "  osm:<id>     surveyed by OpenStreetMap - treat as exact",
            "  screenshot   traced from the student's Google Maps image; the",
            "               pixel it was read from is in measured_at_px",
            "  described    a student said where it is, in words; only the",
            "               CONNECTIONS are sourced, the position is an estimate",
            "Every pathway is \"inferred\": true. OpenStreetMap maps only four",
            "footpaths on this campus, far too few to route on, so the links",
            "between buildings come from a student describing how they walk.",
            "",
            "STILL UNVERIFIED, in order of how much it matters:",
            "  * Gate 2's position. Two corrections contradict each other -",
            "    one puts the gate in the auditorium's lane (y = -172 m), the",
            "    later one puts it between Block A and Block B (y = -11 m,",
            "    then shifted out to y = -76 m). The later, more specific",
            "    instruction was followed. CORRECTIONS.md question 11b.",
            "  * Does the Library really sit between Block A and Block B?",
            "    That is what the map is built on, and the campus tour lists",
            "    the blocks in the order A, B, C(library), D(canteen), which",
            "    could instead mean the library is the third in a row.",
            "    CORRECTIONS.md question 13a.",
            "  * Positions with \"source\": \"described\" - Block B, the Library,",
            "    the Parking, the Canteen, the Outdoor Ground and both hostels -",
            "    are estimates from a verbal description, good to about +-10 m.",
            "",
            "WHAT IS SETTLED, and is asserted by tests rather than trusted:",
            "  * entering Gate 2, Block A is LEFT and Block B is RIGHT",
            "  * Block A -> Library -> Block B is 110 m and that route is",
            "    shorter than going out by the gate",
            "  * both hostels sit behind the sports hall and outdoor ground",
            "  * the Sports Hall and the Outdoor Ground are side by side",
            "  * the three removed buildings are absent here but remain in",
            "    campuses/usar-osm-raw.json, which is the untouched extract",
            "",
            "The full history of what was wrong and who said so is in",
            "CORRECTIONS.md. The sources are listed in SOURCES.md.",
        ],
        "label": CAMPUS_LABEL,
        "note": CAMPUS_NOTE,
        "rounding_step": 5,
        "locations": campus_locations,
        "paths": campus_paths,
    }

    # --- context file ----------------------------------------------------
    context_locations = dict(campus_locations)
    for node_id, name, cat in SCREENSHOT_CONTEXT:
        px, py = MEASURED[node_id]
        x, y = to_metres(px, py)
        context_locations[node_id] = {
            "name": name, "category": cat, "x": x, "y": y,
            "source": "screenshot", "measured_at_px": [px, py],
        }
    context_doc = json.loads(json.dumps(campus_doc))
    context_doc["locations"] = context_locations
    context_doc["paths"] = campus_paths + [
        {"a": a, "b": b, "kind": k, "inferred": True} for a, b, k in CONTEXT_EDGES
    ]
    context_doc["label"] = "USAR East Campus + surroundings (screenshot)"
    context_doc["_scale_warning"] = [
        "Smriti Park is ~1 km north; on a map that includes it, the 350 m",
        "campus is a smudge. Use usar-east-campus.json for campus routing.",
    ]

    out1 = ROOT / "campuses" / "usar-east-campus.json"
    out2 = ROOT / "campuses" / "usar-east-campus-context.json"
    out1.write_text(json.dumps(campus_doc, indent=2) + "\n", encoding="utf-8")
    out2.write_text(json.dumps(context_doc, indent=2) + "\n", encoding="utf-8")

    print(f"wrote {out1.relative_to(ROOT)}")
    print(f"wrote {out2.relative_to(ROOT)}\n")

    print("calibration: 1 px = %.2f m;  campus pin at px%s = %s m"
          % (M_PER_PX, PIN_PX, PIN_M))
    print(f"\n{'location':<24}{'x':>8}{'y':>8}  source")
    print("-" * 62)
    for node_id, entry in campus_locations.items():
        print(f"{entry['name'][:23]:<24}{entry['x']:>8.0f}{entry['y']:>8.0f}"
              f"  {entry['source']}")

    xs = [v["x"] for v in campus_locations.values()]
    ys = [v["y"] for v in campus_locations.values()]
    print(f"\ncampus extent: {(max(xs)-min(xs)):.0f} m x {(max(ys)-min(ys)):.0f} m")

    from campus_nav.graph import CampusGraph, iter_pairs
    from campus_nav import algorithms as A
    g = CampusGraph.load(out1)
    print(f"loaded: {g}  connected={g.is_connected()}")
    dis = sum(1 for a, b in iter_pairs(g.nodes)
              if A.bfs_shortest_path(g, a, b).path != A.dijkstra(g, a, b).path)
    print(f"BFS/Dijkstra disagree on {dis} of {len(list(iter_pairs(g.nodes)))} pairs")


if __name__ == "__main__":
    main()
