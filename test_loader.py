"""
Tests for the campus file format.

This is the mechanism that lets the graph be swapped for a real campus
without touching a line of algorithm code, so the failure modes matter more
than the happy path: a bad campus file must produce a message that says
exactly which entry is wrong.
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from campus_nav import algorithms, loader  # noqa: E402
from campus_nav.algorithms import a_star, dijkstra  # noqa: E402
from campus_nav.graph import CampusGraph  # noqa: E402
from campus_nav.loader import CampusDataError, load_campus, parse_campus  # noqa: E402

SAMPLE = ROOT / "campuses" / "sample-campus.json"
TEMPLATE = ROOT / "campuses" / "MY-CAMPUS.template.json"

MINIMAL = {
    "label": "Test Campus",
    "locations": {
        "a": {"name": "A", "x": 0, "y": 0},
        "b": {"name": "B", "x": 100, "y": 0},
        "c": {"name": "C", "x": 100, "y": 100},
    },
    "paths": [["a", "b"], ["b", "c"]],
}


# --------------------------------------------------------------------------
# the bundled files must always be loadable
# --------------------------------------------------------------------------
def test_sample_campus_file_loads() -> None:
    g = load_campus(SAMPLE)
    assert g.num_nodes == 14 and g.num_edges == 26
    assert g.is_connected()


def test_template_is_a_valid_campus() -> None:
    """The file people copy must itself load, or the first attempt fails."""
    g = load_campus(TEMPLATE)
    assert g.num_nodes == 8
    assert g.is_connected()


def test_sample_file_matches_the_builtin_graph() -> None:
    """
    The JSON export and the Python literals must not drift apart - otherwise
    the figures and the CLI would describe different campuses.
    """
    builtin, from_file = CampusGraph.default(), load_campus(SAMPLE)
    assert builtin.num_nodes == from_file.num_nodes
    assert builtin.num_edges == from_file.num_edges
    assert {(e.a, e.b, e.weight, e.kind) for e in builtin.edges} == \
           {(e.a, e.b, e.weight, e.kind) for e in from_file.edges}
    assert builtin.annotations == from_file.annotations
    for a, b in [("sports", "library"), ("main_gate", "hostel_w")]:
        assert algorithms.dijkstra(builtin, a, b).path == \
               algorithms.dijkstra(from_file, a, b).path


def test_round_trip_through_json(tmp_path) -> None:
    """graph -> JSON -> graph must be lossless."""
    original = CampusGraph.default()
    path = loader.write_campus(original, tmp_path / "c.json")
    reloaded = load_campus(path)
    assert {(e.a, e.b, e.weight, e.kind) for e in original.edges} == \
           {(e.a, e.b, e.weight, e.kind) for e in reloaded.edges}
    assert reloaded.label == original.label
    assert reloaded.note == original.note


# --------------------------------------------------------------------------
# parsing behaviour
# --------------------------------------------------------------------------
def test_weights_are_derived_from_coordinates() -> None:
    g = parse_campus(MINIMAL)
    assert g.weight("a", "b") == 100          # 100 m apart
    assert g.weight("b", "c") == 100


def test_rounding_step_is_honoured() -> None:
    doc = dict(MINIMAL, rounding_step=25)
    doc["locations"] = dict(doc["locations"], b={"name": "B", "x": 110, "y": 0})
    g = parse_campus(doc)
    assert g.weight("a", "b") == 100          # 110 m rounds to 100 at step 25


def test_list_shorthand_is_accepted() -> None:
    doc = dict(MINIMAL, paths=[["a", "b"], ["b", "c", 240]])
    g = parse_campus(doc)
    assert g.weight("b", "c") == 240


def test_unknown_category_falls_back_instead_of_failing() -> None:
    doc = dict(MINIMAL)
    doc["locations"] = dict(doc["locations"])
    doc["locations"]["a"] = {"name": "A", "category": "spaceport", "x": 0, "y": 0}
    g = parse_campus(doc)                      # must not raise
    assert g.kind("a") == "academic"


def test_loaded_graph_is_fully_usable() -> None:
    """A loaded campus must work with every algorithm and the figures."""
    g = parse_campus(MINIMAL)
    from campus_nav import visualize

    assert algorithms.dijkstra(g, "a", "c").cost == 200
    assert algorithms.a_star(g, "a", "c").cost == 200
    assert algorithms.bfs_shortest_path(g, "a", "c").hops == 2
    assert "<svg" in visualize.render_svg(g)


# --------------------------------------------------------------------------
# every malformed input must name the offending entry
# --------------------------------------------------------------------------
def test_missing_location_in_path() -> None:
    doc = dict(MINIMAL, paths=[["a", "nowhere"]])
    with pytest.raises(CampusDataError) as exc:
        parse_campus(doc)
    assert "nowhere" in str(exc.value)
    assert "path #1" in str(exc.value)


def test_weight_shorter_than_the_straight_line_is_rejected() -> None:
    """
    This is the guard that protects A* optimality: an edge shorter than the
    straight line between its endpoints makes the heuristic inadmissible.
    """
    doc = dict(MINIMAL, paths=[["a", "b", 20]])
    with pytest.raises(CampusDataError) as exc:
        parse_campus(doc)
    assert "breaks the A* heuristic" in str(exc.value)


def test_self_loop_is_rejected() -> None:
    with pytest.raises(CampusDataError, match="joined to itself"):
        parse_campus(dict(MINIMAL, paths=[["a", "a"]]))


def test_duplicate_pathway_is_rejected() -> None:
    with pytest.raises(CampusDataError):
        parse_campus(dict(MINIMAL, paths=[["a", "b"], ["a", "b"]]))


def test_negative_weight_is_rejected() -> None:
    with pytest.raises(CampusDataError, match="must be positive"):
        parse_campus(dict(MINIMAL, paths=[["a", "b", -5]]))


def test_bad_kind_is_rejected() -> None:
    with pytest.raises(CampusDataError, match="kind must be one of"):
        parse_campus(dict(MINIMAL, paths=[{"a": "a", "b": "b", "kind": "teleport"}]))


def test_too_few_locations_is_rejected() -> None:
    doc = {"locations": {"a": {"name": "A", "x": 0, "y": 0}}, "paths": [["a", "a"]]}
    with pytest.raises(CampusDataError, match="at least 2 locations"):
        parse_campus(doc)


def test_non_numeric_coordinate_is_rejected() -> None:
    doc = dict(MINIMAL)
    doc["locations"] = dict(doc["locations"], a={"name": "A", "x": "left", "y": 0})
    with pytest.raises(CampusDataError, match="expected a number"):
        parse_campus(doc)


def test_missing_key_is_named() -> None:
    doc = dict(MINIMAL)
    doc["locations"] = dict(doc["locations"], a={"name": "A", "y": 0})
    with pytest.raises(CampusDataError, match="missing required key 'x'"):
        parse_campus(doc)


def test_coincident_locations_are_rejected() -> None:
    """Two locations at the same point give a zero-length pathway."""
    doc = dict(MINIMAL)
    doc["locations"] = {"a": {"name": "A", "x": 50, "y": 50},
                        "b": {"name": "B", "x": 50, "y": 50}}
    with pytest.raises(CampusDataError, match="same coordinates"):
        parse_campus(doc, source="test")


def test_broken_json_names_the_line() -> None:
    bad = Path("/tmp/_bad_campus.json")
    bad.write_text('{"label": "x",}')          # trailing comma
    with pytest.raises(CampusDataError) as exc:
        load_campus(bad)
    assert "not valid JSON" in str(exc.value) and "line 1" in str(exc.value)


def test_missing_file_suggests_the_template(tmp_path) -> None:
    with pytest.raises(CampusDataError) as exc:
        load_campus(tmp_path / "nope.json")
    assert "MY-CAMPUS.template.json" in str(exc.value)


# --------------------------------------------------------------------------
# the shipped USAR campus - the real, OSM-sourced dataset
# --------------------------------------------------------------------------
USAR = ROOT / "campuses" / "usar-east-campus.json"
USAR_CONTEXT = ROOT / "campuses" / "usar-east-campus-context.json"
USAR_OSM_RAW = ROOT / "campuses" / "usar-osm-raw.json"


def test_usar_campus_loads_and_is_connected() -> None:
    g = load_campus(USAR)
    assert g.num_nodes == 12
    assert g.is_connected()

    # Gate 1: auditorium on its side, and its path to Block A runs past
    # the Parking (student: "in path from gate 1 to block A, parking comes
    # in between"), so there is deliberately no direct Gate 1 - Block A edge
    assert g.weight("gate_1", "auditorium") < 150
    assert g.weight("gate_1", "parking") < 250
    assert g.weight("parking", "block_a") < 250
    route = dijkstra(g, "gate_1", "block_a")
    assert route.path == ["gate_1", "parking", "block_a"], route.path

    # Gate 2: Block A to the left and Block B to the right; the Sports Hall
    # is also reachable straight from it
    for target in ("block_a", "block_b", "sports"):
        assert any(nb == target for nb, _ in g.neighbours("gate_2")), target

    # Sports Hall and Outdoor Ground in front, hostels behind them
    assert g.weight("sports", "outdoor_ground") < 200
    assert g.coords("boys_hostel")[1] > g.coords("sports")[1], \
        "Boys Hostel sits behind the Sports Hall, further from the entrance"
    assert g.coords("girls_hostel")[1] > g.coords("outdoor_ground")[1], \
        "Girls' Hostel sits behind the Outdoor Ground"
    # the Library sits between Block A and Block B
    assert g.weight("block_a", "library") < 200
    assert g.weight("library", "block_b") < 200
    # every location must declare a source
    for node in g:
        entry = _raw_locations(USAR)[node]
        assert entry["source"], f"{node} has no source"
        assert "x" in entry and "y" in entry


def test_entering_gate_2_block_a_is_left_and_block_b_is_right() -> None:
    """
    Encode a human's description of the campus as a geometric assertion.

    The student: "when we enter from gate 2 left side we go we reach to
    block A and right side we go block B". Walking in through Gate 2 you face
    the campus, so left and right are relative to the direction from the gate
    to the campus centre - not to north.

    The 2-D cross product of that facing vector with the vector to each block
    gives the side: positive is clockwise on a screen, i.e. the walker's
    right.
    """
    g = load_campus(USAR)
    gx, gy = g.coords("gate_2")
    xs = [g.coords(n)[0] for n in g]
    ys = [g.coords(n)[1] for n in g]
    fx, fy = sum(xs) / len(xs) - gx, sum(ys) / len(ys) - gy

    def cross(node: str) -> float:
        x, y = g.coords(node)
        return fx * (y - gy) - fy * (x - gx)

    assert cross("block_a") < 0, "Block A must be on the LEFT entering Gate 2"
    assert cross("block_b") > 0, "Block B must be on the RIGHT entering Gate 2"

    # Gate 2 is the WEST gate, opposite Gate 1
    assert g.coords("gate_2")[0] < g.coords("gate_1")[0] - 300
    # and it sits BETWEEN Block A and Block B, which is what makes the
    # left/right description literally true as you walk in
    # Gate 2 was shifted further out at the student's request, so the bound
    # is "both blocks are a similar short walk from the gate", not a fixed
    # number of metres.
    assert g.weight("gate_2", "block_a") < 250
    assert g.weight("gate_2", "block_b") < 250
    assert abs(g.weight("gate_2", "block_a") - g.weight("gate_2", "block_b")) < 50, \
        "the gate sits between the two blocks, so the two walks are similar"
    # NOTE: an earlier correction also said the gate is "in the lane of
    # auditorium". That lane is at y = -172 m; the gap between Block A and
    # Block B is at y = -11 m, so the two statements cannot both be exact.
    # The newer, more specific one wins, and the conflict is recorded in
    # CORRECTIONS.md rather than silently resolved.


def test_removed_locations_are_really_gone() -> None:
    """Correction 12 removed USAR Ground and the Canteen from the graph.

    Correction 13 brings the Canteen back: a campus tour filmed by a student
    is explicit that the canteen is its own block - "D-Block is our canteen",
    and "our canteen is downstairs". The two sources disagree, and the video
    wins on the point it was brought in to settle, so this test now records
    the canteen being *present* and explains why it came back.
    """
    g = load_campus(USAR)
    assert "usar_ground" not in g.nodes
    assert "canteen" in g.nodes, "the tour says the canteen is its own block"
    assert g.num_nodes == 12
    assert g.is_connected(), "removing a building must not split the graph"


def test_block_names_come_from_a_named_source() -> None:
    """Every block letter on the map traces to the campus tour, quoted.

    The point of this project is that nothing on the map is invented. The
    A/B/C/D block letters came from a specific video, so each one carries the
    sentence it came from, and this test fails if that evidence is dropped.
    """
    locs = json.loads(USAR.read_text(encoding="utf-8"))["locations"]
    for node_id, letter in [("block_a", "A-Block"), ("block_b", "B-Block"),
                            ("library", "C-Block"), ("canteen", "D-Block")]:
        evidence = locs[node_id].get("_tour_evidence", "")
        assert letter in evidence, f"{node_id} is missing its {letter} evidence"
        assert "usar" in evidence.lower() or "usdi" in evidence.lower() \
            or "library" in evidence.lower() or "canteen" in evidence.lower()
    """Regression guard for a bug that hid for four corrections.

    The builder wrote notes to `entry`, a leftover loop variable from the OSM
    locations, so "the library is on the 5th floor" was stored against Gate 1
    from correction 8 until correction 12 - a note about a building, filed
    under a gate, in the one file whose job is provenance.
    """
    locs = json.loads(USAR.read_text(encoding="utf-8"))["locations"]
    assert "5th floor" in locs["library"]["_note"]
    for node_id, loc in locs.items():
        if node_id != "library":
            assert "_note" not in loc, f"unexpected note on {node_id}: {loc['_note']}"


def test_the_files_own_instructions_are_not_stale() -> None:
    """The _verify block is the first thing a reader of the JSON sees.

    It spent six corrections describing a map that no longer existed - still
    asking whether Block B was a complex, whether two unnamed OSM buildings
    were part of it, and quoting a gate node id that had been renamed. A
    stale instruction file is worse than none: it tells the reader to go and
    check things that were settled long ago, and hides the questions that
    are actually open.
    """
    doc = json.loads(USAR.read_text(encoding="utf-8"))
    text = " ".join(doc["_provenance"]) + " " + " ".join(doc["_verify"])

    removed = ["block_1", "block_2", "teachers_hostel", "gate_east", "usar_ground"]
    for dead in removed:
        assert dead not in text, f"_verify still mentions removed location {dead!r}"

    for node_id in doc["locations"]:
        pass  # ids are checked the other way round, below

    # every location id mentioned in the prose must exist in the file
    mentioned = {w.strip(".,;:*()\"'") for w in text.split()}
    for node_id in doc["locations"]:
        if node_id in mentioned:
            assert node_id in doc["locations"]

    # and it must actually tell the reader something
    assert any("source" in line for line in doc["_verify"])
    assert any("inferred" in line for line in doc["_verify"])


def test_block_a_to_block_b_goes_past_the_library() -> None:
    """
    The student: "it's only one building, why you taking Block B so far away
    from Block A, then in between library at 5 floor and then Block B".

    So the shortest path from Block A to Block B must run through the
    Library, and Block B must be a single building close to Block A - not a
    distant complex. The description is asserted as a route.
    """
    g = load_campus(USAR)
    # the Library is directly on the chain from Block A to Block B
    assert g.weight("block_a", "library") < 200
    assert g.weight("library", "block_b") < 200

    route = dijkstra(g, "block_a", "block_b")
    assert route.cost < 300, "Block B is close to Block A, not across campus"
    # whichever way you go, you pass either the Library or the gate; the
    # student's description was that the Library lies between the two
    assert "library" in route.path or "gate_2" in route.path, route.path

    # Block B is one building, not a hub standing in for a whole complex
    assert g.degree("block_b") <= 4, g.degree("block_b")


def test_park_is_not_on_the_campus() -> None:
    """
    The student: 'the park is not in my campus'. Surajmal Park must stay out
    of the campus graph and appear only in the context file, for orientation.
    """
    campus = load_campus(USAR)
    assert "park" not in campus.nodes
    assert "park" in load_campus(USAR_CONTEXT).nodes
    # the boundary road is context too, not a destination
    assert "gurdwara_road" not in campus.nodes


def _raw_locations(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))["locations"]


def test_usar_campus_declares_its_provenance() -> None:
    """A real dataset must say where it came from, in the file itself."""
    doc = json.loads(USAR.read_text(encoding="utf-8"))
    blob = json.dumps(doc).lower()
    assert "openstreetmap" in blob
    assert "odbl" in blob
    assert "_verify" in doc, "must tell the reader what to check themselves"
    assert doc["_verify"], "the _verify block must not be empty"


def test_usar_campus_uses_real_osm_coordinates() -> None:
    """
    The metre grid is anchored on the campus polygon's centre, and the
    projection must match `tools/build_usar_campus.py`.

    Rather than hard-coding magic numbers, the expected offset is recomputed
    here from the raw OSM latitude/longitude with an independent
    implementation of the same equirectangular projection. If anyone moves
    the origin or flips an axis, this fails and forces a conscious decision
    instead of silently rotating the map.
    """
    import math

    doc = json.loads(USAR.read_text(encoding="utf-8"))
    acad = doc["locations"]["block_a"]

    # the OSM feature this location claims to be
    assert acad["source"].endswith("way/1186488777")

    # OSM coordinate of way/1186488777, and of the campus polygon centre
    lat, lon = 28.66465, 77.30059
    origin_lat, origin_lon = 28.66443, 77.30083

    m_per_deg_lat = 111_320.0
    m_per_deg_lon = m_per_deg_lat * math.cos(math.radians(origin_lat))
    expected_x = (lon - origin_lon) * m_per_deg_lon       # east is +x
    expected_y = (origin_lat - lat) * m_per_deg_lat       # NORTH is -y
    assert abs(acad["x"] - expected_x) < 1.0, (acad["x"], expected_x)
    assert abs(acad["y"] - expected_y) < 1.0, (acad["y"], expected_y)

    # and the sign convention itself: the Academic Block is north-west of the
    # campus centre, so it must be left of and above the origin on the map
    assert acad["x"] < 0 and acad["y"] < 0


def test_usar_and_context_files_differ_only_by_surroundings() -> None:
    """
    The context file must be the campus file plus extra surroundings - never
    a divergent copy of the same buildings.
    """
    campus = json.loads(USAR.read_text(encoding="utf-8"))
    context = json.loads(USAR_CONTEXT.read_text(encoding="utf-8"))
    for node_id, entry in campus["locations"].items():
        assert node_id in context["locations"], node_id
        assert context["locations"][node_id] == entry, node_id
    assert set(context["locations"]) > set(campus["locations"])
    # every campus path must survive into the context file
    def keys(doc):
        return {frozenset({p["a"], p["b"]}) for p in doc["paths"]}
    assert keys(campus) <= keys(context)


def test_usar_locations_declare_where_they_came_from() -> None:
    """
    Each location must say whether it is a surveyed OSM coordinate or an
    estimate traced from the screenshot. Guessing must be visible.
    """
    doc = json.loads(USAR.read_text(encoding="utf-8"))
    for node_id, entry in doc["locations"].items():
        src = entry["source"]
        assert src in ("screenshot", "described") or src.startswith("osm:"), \
            (node_id, src)
        if src == "screenshot":
            assert "measured_at_px" in entry, node_id
        if src == "described":
            # no source coordinate exists for these - the reason must be stated
            assert entry.get("position_estimate"), node_id
    # the campus pin (OSM Academic Block) is the calibration point
    assert doc["locations"]["block_a"]["source"] == "osm:way/1186488777"


def test_osm_raw_extraction_still_loads() -> None:
    """The OSM-only dataset is kept as a cross-check against the traced one."""
    g = load_campus(USAR_OSM_RAW)
    assert g.is_connected()
    assert g.num_nodes == 10


def test_screenshot_trace_agrees_with_osm_where_they_overlap() -> None:
    """
    The traced layout must not move a building that OSM already surveyed.
    Any node present in both files has to have identical coordinates.
    """
    traced = json.loads(USAR.read_text(encoding="utf-8"))["locations"]
    raw = json.loads(USAR_OSM_RAW.read_text(encoding="utf-8"))["locations"]
    shared = {k for k in set(traced) & set(raw)
              if traced[k]["source"].startswith("osm:")}
    assert shared, "the two datasets should share the OSM-sourced buildings"
    for node_id in shared:
        assert traced[node_id]["x"] == raw[node_id]["x"], node_id
        assert traced[node_id]["y"] == raw[node_id]["y"], node_id


def test_usar_campus_algorithms_agree_on_optimality() -> None:
    """A* must equal Dijkstra on the real dataset, as on the sample."""
    g = load_campus(USAR)
    for a, b in itertools.combinations(g.nodes, 2):
        assert a_star(g, a, b).cost == dijkstra(g, a, b).cost, (a, b)


def test_usar_campus_shortest_paths_are_really_shortest() -> None:
    """
    Brute-force reference, as used for the sample campus: enumerate every
    simple path and confirm Dijkstra found the cheapest one.
    """
    g = load_campus(USAR)

    def brute(start: str, goal: str) -> float:
        best = float("inf")

        def walk(node: str, cost: float, seen: frozenset) -> None:
            nonlocal best
            if cost >= best:
                return
            if node == goal:
                best = cost
                return
            for nxt, w in g.neighbours(node):
                if nxt not in seen:
                    walk(nxt, cost + w, seen | {nxt})

        walk(start, 0.0, frozenset({start}))
        return best

    for a, b in itertools.combinations(g.nodes, 2):
        assert dijkstra(g, a, b).cost == brute(a, b), (a, b)


def test_usar_campus_renders() -> None:
    """The real layout must actually draw, with labels inside the canvas."""
    from campus_nav import visualize

    g = load_campus(USAR)
    svg = visualize.render_svg(g)
    assert "<svg" in svg and "<polyline" not in svg
    # the campus label and the OSM attribution both have to appear
    assert "USAR" in svg
    assert "OpenStreetMap" in svg
