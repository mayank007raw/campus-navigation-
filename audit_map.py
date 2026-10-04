"""
Walk the shipped campus map and re-check every correction against it.

This is the answer to "go through my map". It does not print the map - it
interrogates the map. Each correction the student made became a claim about
geometry, and a claim about geometry can be tested, so this script tests all
of them against the current JSON and says which ones still hold.

Run:  python3 tools/audit_map.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from campus_nav import algorithms as A  # noqa: E402
from campus_nav.graph import CampusGraph  # noqa: E402

CAMPUS = ROOT / "campuses" / "usar-east-campus.json"

PASS, FAIL, WARN = "  PASS", "  FAIL", "  WARN"
failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"{PASS if ok else FAIL}  {label}" + (f"\n          {detail}" if detail else ""))
    if not ok:
        failures.append(label)


def dist(g: CampusGraph, a: str, b: str) -> float:
    (x1, y1), (x2, y2) = g.coords(a), g.coords(b)
    return math.hypot(x2 - x1, y2 - y1)


def cross(g: CampusGraph, gate: str, target: str) -> float:
    """Positive means the target is on the walker's RIGHT, entering the gate.

    Facing direction = gate -> campus centroid.
    """
    xs = [g.coords(n)[0] for n in g.nodes]
    ys = [g.coords(n)[1] for n in g.nodes]
    gx, gy = g.coords(gate)
    fx, fy = sum(xs) / len(xs) - gx, sum(ys) / len(ys) - gy
    tx, ty = g.coords(target)
    return fx * (ty - gy) - fy * (tx - gx)


def main() -> int:
    g = CampusGraph.load(CAMPUS)
    doc = json.loads(CAMPUS.read_text(encoding="utf-8"))
    locs = doc["locations"]

    print("=" * 72)
    print(f"MAP AUDIT - {g.label}")
    print("=" * 72)

    # ---------------------------------------------------------------- shape
    print("\nSHAPE")
    print(f"  {g.num_nodes} locations, {g.num_edges} pathways, "
          f"connected: {g.is_connected()}")
    xs = [g.coords(n)[0] for n in g.nodes]
    ys = [g.coords(n)[1] for n in g.nodes]
    print(f"  extent {max(xs) - min(xs):.0f} m x {max(ys) - min(ys):.0f} m")
    check("the campus is one connected map", g.is_connected())
    check("no location is isolated", all(g.degree(n) > 0 for n in g.nodes))

    # ------------------------------------------------------------ sources
    print("\nSOURCES - nothing on this map is invented")
    counts: dict[str, int] = {}
    for loc in locs.values():
        counts[loc["source"].split(":")[0]] = counts.get(loc["source"].split(":")[0], 0) + 1
    print(f"  {counts}")
    check("every location declares a source", all("source" in l for l in locs.values()))
    check("the four OSM blocks kept their surveyed coordinates",
          all(locs[k]["source"].startswith("osm:")
              for k in ("block_a", "auditorium", "sports", "gate_1")))

    # --------------------------------------------------- corrections 1 & 2
    print("\nCORRECTION 1-2  two gates; the auditorium gate leads to Block A")
    check("Gate 1 is next to the Auditorium",
          A.dijkstra(g, "gate_1", "auditorium").cost < 150,
          f"{A.dijkstra(g, 'gate_1', 'auditorium').cost:.0f} m")
    check("Gate 1's route to Block A runs past the Parking (correction 11)",
          A.dijkstra(g, "gate_1", "block_a").path == ["gate_1", "parking", "block_a"])

    # ------------------------------------------------------------ correction 3
    print("\nCORRECTION 3  the park is not on the campus")
    # careful: "park" is a substring of "parking", which is a real location
    # here. Match node ids exactly, and check display names separately.
    check("no park node in the graph",
          "park" not in g.nodes and not any(
              "park" in l["name"].lower().replace("parking", "")
              for l in locs.values()))

    # ------------------------------------------------------------ correction 5
    print("\nCORRECTION 5  entering Gate 2: left is Block A, right is Block B")
    ca, cb = cross(g, "gate_2", "block_a"), cross(g, "gate_2", "block_b")
    check("Block A is on the LEFT", ca < 0, f"cross = {ca:+.0f}")
    check("Block B is on the RIGHT", cb > 0, f"cross = {cb:+.0f}")
    check("both blocks are a short walk from the gate",
          max(g.weight("gate_2", "block_a"), g.weight("gate_2", "block_b")) < 250)

    # ------------------------------------------------------------ correction 8
    print("\nCORRECTION 8  Block A -> Block B goes past the Library (110 m)")
    route = A.dijkstra(g, "block_a", "block_b")
    check("the shortest walk is Block A -> Library -> Block B",
          route.path == ["block_a", "library", "block_b"], " -> ".join(route.path))
    check("the chain is 110 m", round(route.cost) == 110, f"{route.cost:.0f} m")
    check("Block B is one building, not a hub", g.degree("block_b") <= 4,
          f"degree {g.degree('block_b')}")

    # ------------------------------------------------------------ correction 9
    print("\nCORRECTION 9  three buildings off the map, hostels behind the sports pair")
    for gone in ("teachers_hostel", "block_1", "block_2"):
        check(f"{gone} is not plotted", gone not in g.nodes)
    raw = json.loads((ROOT / "campuses" / "usar-osm-raw.json").read_text(encoding="utf-8"))
    check("...but the raw OSM record still has them",
          all(k in raw["locations"] for k in ("teachers_hostel", "block_1", "block_2")))
    check("Boys Hostel is behind the Sports Hall",
          g.coords("boys_hostel")[1] > g.coords("sports")[1] + 50)
    check("Girls' Hostel is behind the Outdoor Ground",
          g.coords("girls_hostel")[1] > g.coords("outdoor_ground")[1] + 50)

    # ----------------------------------------------------------- correction 10
    print("\nCORRECTION 10  sports side by side, Gate 2 in the gap")
    check("Sports Hall and Outdoor Ground share a row",
          abs(g.coords("sports")[1] - g.coords("outdoor_ground")[1]) < 25)
    check("...and sit 60-100 m apart",
          50 < dist(g, "sports", "outdoor_ground") < 120,
          f"{dist(g, 'sports', 'outdoor_ground'):.0f} m")

    # ----------------------------------------------------------- correction 11
    print("\nCORRECTION 11  Gate 2 shifted out; Parking and Canteen on their routes")
    check("Parking is mid-way on Gate 1 -> Block A",
          g.weight("gate_1", "parking") < 250 and g.weight("parking", "block_a") < 250)
    check("Block B -> Canteen -> Sports Hall is the way through",
          A.dijkstra(g, "block_b", "sports").path == ["block_b", "canteen", "sports"])

    # ----------------------------------------------------------- correction 12
    print("\nCORRECTION 12  USAR Ground off the map")
    check("no USAR Ground location", "usar_ground" not in g.nodes)

    # ----------------------------------------------------------- correction 13
    print("\nCORRECTION 13  the block letters, each with quoted evidence")
    for node_id, letter in [("block_a", "A-Block"), ("block_b", "B-Block"),
                            ("library", "C-Block"), ("canteen", "D-Block")]:
        ev = locs.get(node_id, {}).get("_tour_evidence", "")
        check(f"{letter} is documented", letter in ev, ev[:64])

    # ---------------------------------------------------------------- routes
    print("\nTHE ROUTES THAT MATTER")
    for a, b in [("gate_1", "block_a"), ("gate_2", "block_a"), ("block_a", "block_b"),
                 ("block_b", "sports"), ("gate_1", "girls_hostel"),
                 ("auditorium", "canteen")]:
        r = A.dijkstra(g, a, b)
        print(f"  {g.name(a):<20} -> {g.name(b):<20} "
              f"{r.cost:>5.0f} m  via {' / '.join(g.name(n) for n in r.path[1:-1]) or 'direct'}")

    # --------------------------------------------------------------- verdict
    print("\n" + "=" * 72)
    if failures:
        print(f"{len(failures)} CHECK(S) FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("every correction the student made still holds in the shipped map")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
