"""
Load a campus from a JSON file.

This exists because the campus is DATA, not code. A navigation system should
not need a Python edit (and a re-run, and a re-commit) before it can describe
a different campus - the graph, the algorithms and every figure are already
generic. `campuses/sample-campus.json` is the built-in synthetic example;
copy `campuses/MY-CAMPUS.template.json` and fill in your own.

File format
-----------
{
  "label": "My Campus",                       // shown on every figure
  "note":  "Surveyed from the campus map.",   // optional, shown as a caption
  "rounding_step": 5,                          // optional, default 5 metres
  "locations": {
    "library": {"name": "Central Library", "category": "academic",
                "x": 120, "y": 240},
    ...
  },
  "paths": [
    {"a": "library", "b": "canteen", "kind": "walkway"},
    {"a": "library", "b": "hostel",  "kind": "road",
     "weight": 420, "why": "perimeter road around the sports field"},
    ["gate", "canteen", 90],                   // shorthand also accepted
    ["gate", "library"]                        // weight derived from x/y
  ]
}

Rules enforced here, with a message that says which line is wrong:
  * every pathway endpoint must be a declared location
  * ids must be unique, coordinates must be numbers
  * a pathway's weight must be a positive number if given
  * no self-loops and no duplicate pathways
  * a pathway whose weight is derived from coordinates may not be shorter
    than the straight line between its endpoints, or A* stops being optimal

Categories: "gate", "academic", "amenity", "sports", "hostel", "transit"
(an unknown category still loads - it just gets the default colour).
Kinds: "walkway" (default) or "road" (drawn dashed).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import geo
from .graph import CampusGraph, InvalidGraphError, UnknownLocationError

KNOWN_CATEGORIES = {"gate", "academic", "amenity", "sports", "hostel", "transit"}
KNOWN_KINDS = {"walkway", "road"}


class CampusDataError(ValueError):
    """A campus file is malformed. The message names the offending entry."""


# --------------------------------------------------------------------------
# parsing helpers
# --------------------------------------------------------------------------
def _require(mapping: dict, key: str, where: str) -> Any:
    if key not in mapping:
        raise CampusDataError(f"{where}: missing required key {key!r}")
    return mapping[key]


def _as_number(value: Any, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CampusDataError(f"{where}: expected a number, got {value!r}")
    return float(value)


def _parse_location(node_id: str, raw: Any) -> tuple[str, str, float, float]:
    where = f"location {node_id!r}"
    if not isinstance(node_id, str) or not node_id.strip():
        raise CampusDataError("location ids must be non-empty strings")
    if isinstance(raw, (list, tuple)):
        # ["Central Library", "academic", 120, 240]
        if len(raw) < 4:
            raise CampusDataError(
                f"{where}: list form needs 4 items "
                f"[name, category, x, y], got {len(raw)}"
            )
        name, category = raw[0], raw[1]
        x, y = _as_number(raw[2], where), _as_number(raw[3], where)
    elif isinstance(raw, dict):
        name = _require(raw, "name", where)
        category = raw.get("category", "academic")
        x = _as_number(_require(raw, "x", where), where)
        y = _as_number(_require(raw, "y", where), where)
    else:
        raise CampusDataError(
            f"{where}: expected an object or a 4-item list, got {type(raw).__name__}"
        )
    if not isinstance(name, str) or not name.strip():
        raise CampusDataError(f"{where}: 'name' must be a non-empty string")
    if category not in KNOWN_CATEGORIES:
        category = "academic"  # tolerated, but defaults rather than crashing
    return name, category, x, y


def _parse_path(raw: Any, index: int, coords: dict[str, tuple[float, float]],
                step: int) -> tuple[str, str, int, str, str | None]:
    where = f"path #{index + 1}"
    if isinstance(raw, (list, tuple)):
        if len(raw) < 2 or len(raw) > 3:
            raise CampusDataError(
                f"{where}: list form is [a, b] or [a, b, weight], got "
                f"{len(raw)} items"
            )
        raw = {"a": raw[0], "b": raw[1],
               **({"weight": raw[2]} if len(raw) == 3 else {})}
    if not isinstance(raw, dict):
        raise CampusDataError(f"{where}: expected an object or a list")

    a = _require(raw, "a", where)
    b = _require(raw, "b", where)
    for endpoint in (a, b):
        if endpoint not in coords:
            known = ", ".join(sorted(coords)) or "(none declared)"
            raise CampusDataError(
                f"{where}: unknown location {endpoint!r}. "
                f"Declared locations: {known}"
            )
    if a == b:
        raise CampusDataError(f"{where}: {a!r} is joined to itself")

    kind = raw.get("kind", "walkway")
    if kind not in KNOWN_KINDS:
        raise CampusDataError(
            f"{where}: kind must be one of {sorted(KNOWN_KINDS)}, got {kind!r}"
        )

    why = raw.get("why")
    if "weight" in raw:
        weight = _as_number(raw["weight"], where)
        if weight <= 0:
            raise CampusDataError(f"{where}: weight must be positive, got {weight}")
        straight = geo.euclidean(*coords[a], *coords[b])
        if weight < straight * 0.9:
            raise CampusDataError(
                f"{where}: {a}-{b} is {weight:g} m but the map puts those two "
                f"points {straight:.0f} m apart. A pathway shorter than the "
                f"straight line breaks the A* heuristic. Either raise the "
                f"weight or fix the coordinates."
            )
        return a, b, int(round(weight)), kind, why

    # derived from coordinates
    try:
        weight = geo.derive_weight(*coords[a], *coords[b], step)
    except ValueError as exc:
        raise CampusDataError(f"{where}: {exc}") from None
    return a, b, weight, kind, why


# --------------------------------------------------------------------------
# public entry points
# --------------------------------------------------------------------------
def parse_campus(document: dict, *, source: str = "<memory>") -> CampusGraph:
    """Build a graph from an already-parsed campus document."""
    if not isinstance(document, dict):
        raise CampusDataError(f"{source}: top level must be a JSON object")

    label = document.get("label") or "Campus"
    note = document.get("note") or ""
    step = document.get("rounding_step", geo.DEFAULT_ROUNDING_STEP)
    if not isinstance(step, int) or step <= 0:
        raise CampusDataError(f"{source}: rounding_step must be a positive integer")

    locations = _require(document, "locations", source)
    if not isinstance(locations, dict) or len(locations) < 2:
        raise CampusDataError(
            f"{source}: 'locations' must declare at least 2 locations"
        )
    paths = document.get("paths")
    if not isinstance(paths, list) or not paths:
        raise CampusDataError(f"{source}: 'paths' must be a non-empty list")

    graph = CampusGraph(label=label, note=note)

    coords: dict[str, tuple[float, float]] = {}
    for node_id, raw in locations.items():
        name, category, x, y = _parse_location(node_id, raw)
        try:
            graph.add_node(node_id, name=name, category=category, x=x, y=y)
        except InvalidGraphError as exc:            # duplicate id
            raise CampusDataError(f"{source}: {exc}") from None
        coords[node_id] = (x, y)

    for i, raw in enumerate(paths):
        a, b, weight, kind, why = _parse_path(raw, i, coords, step)
        try:
            graph.add_edge(a, b, weight, kind)
        except (InvalidGraphError, UnknownLocationError) as exc:
            raise CampusDataError(f"path #{i + 1}: {exc}") from None
        if why:
            graph.annotations[frozenset({a, b})] = why

    return graph


def load_campus(path: str | Path) -> CampusGraph:
    """Load a campus graph from a JSON file."""
    p = Path(path)
    if not p.exists():
        raise CampusDataError(
            f"campus file not found: {p}\n"
            f"  Try one of the files in campuses/, or write your own - "
            f"campuses/MY-CAMPUS.template.json explains the format."
        )
    try:
        document = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CampusDataError(
            f"{p}: not valid JSON (line {exc.lineno}, column {exc.colno}): "
            f"{exc.msg}"
        ) from None
    return parse_campus(document, source=str(p))


def to_document(graph: CampusGraph, *, label: str | None = None,
                note: str | None = None) -> dict:
    """Serialise a graph back to the campus file format (used by gen_docs)."""
    locations: dict[str, dict] = {}
    for node in graph:
        x, y = graph.coords(node)
        locations[node] = {
            "name": graph.name(node),
            "category": graph.kind(node),
            "x": round(x, 2),
            "y": round(y, 2),
        }
    paths: list[dict] = []
    for e in graph.edges:
        entry: dict[str, Any] = {"a": e.a, "b": e.b}
        if e.kind != "walkway":
            entry["kind"] = e.kind
        # record explicit weights only where they differ from the map distance
        from . import geo as _geo
        derived = _geo.derive_weight(*graph.coords(e.a), *graph.coords(e.b))
        if derived != e.weight:
            entry["weight"] = e.weight
            why = graph.annotations.get(frozenset({e.a, e.b}))
            if why:
                entry["why"] = why
        paths.append(entry)
    return {
        "label": label or graph.label,
        "note": note if note is not None else graph.note,
        "locations": locations,
        "paths": paths,
    }


def write_campus(graph: CampusGraph, path: str | Path, **kwargs) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(to_document(graph, **kwargs), indent=2) + "\n",
                 encoding="utf-8")
    return p
