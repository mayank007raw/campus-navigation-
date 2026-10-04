"""
Visualisation: a static SVG map and a self-contained interactive HTML demo.

Both are generated FROM `campus_nav.data`, so the picture can never drift
away from the graph the algorithms run on.

Two rendering lessons are baked into this file (see DECISIONS.md #6):

  * `paint-order="stroke"` is used for text halos in the browser but is
    IGNORED by librsvg / cairosvg, which paint the stroke over the fill and
    turn white-filled glyphs into white blobs. Every label here is therefore
    drawn twice by hand: an outline pass, then the fill pass on top. This
    works in every renderer, including GitHub's README renderer.
  * `style="width:100%;height:auto"` on the root <svg> makes librsvg compute
    a zero-size canvas. The SVG carries only width/height attributes;
    responsiveness is the embedding page's job.

Design note (DECISIONS.md #5): the browser never re-implements the
algorithms. Python precomputes every origin/destination pair with all three
algorithms and embeds the results as JSON, so the algorithms have exactly
ONE implementation - the one the test suite covers.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

from . import algorithms, data
from .algorithms import ALGORITHMS, Route, solve
from .graph import CampusGraph, iter_pairs

# --- drawing constants (SVG user units == metres) -------------------------
PAD_X = 66.0          # horizontal breathing room around the map
PAD_TOP = 26.0        # room above the topmost node for its label
PAD_BOTTOM = 18.0     # room below the bottom node
NODE_R = 8.5
FONT = ("-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, "
        "Helvetica, Arial, sans-serif")
INK = "#202124"
MUTED = "#5f6368"
FAINT = "#9aa0a6"
ROUTE_COLOUR = "#1a73e8"
BFS_COLOUR = "#e37400"
MIN_WIDTH = 420.0     # never produce a sliver of a figure

TITLE_SIZE = 19.0
SUB_SIZE = 13.0
NOTE_SIZE = 12.0


# --------------------------------------------------------------------------
# small text helpers
# --------------------------------------------------------------------------
def _text_width(text: str, size: float, bold: bool = False) -> float:
    """Rough advance width. Good enough for laying out a figure."""
    ratio = 0.68 if bold else 0.62
    return len(text) * size * ratio


def _wrap(text: str, size: float, max_width: float, bold: bool = False) -> list[str]:
    """Greedy word wrap using the width estimate above."""
    if not text:
        return []
    words, lines, current = text.split(), [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and _text_width(candidate, size, bold) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _label(
    parts: list[str],
    x: float,
    y: float,
    text: str,
    *,
    size: float = 11.5,
    fill: str = INK,
    weight: int = 600,
    anchor: str = "middle",
    halo: float = 3.2,
) -> None:
    """
    Two-pass halo label: an outline pass, then the fill pass.

    Deliberately NOT `paint-order="stroke"` - see the module docstring.
    Passing halo=0 skips the outline pass entirely.
    """
    common = (f'x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" '
              f'font-size="{size:g}" font-weight="{weight}" '
              f'text-anchor="{anchor}"')
    escaped = html.escape(text)
    if halo:
        parts.append(
            f'<text {common} fill="none" stroke="#fff" '
            f'stroke-width="{halo:g}" stroke-linejoin="round">{escaped}</text>'
        )
    parts.append(f'<text {common} fill="{fill}">{escaped}</text>')


def _bounds(graph: CampusGraph) -> tuple[float, float, float, float]:
    """
    Map bounds INCLUDING the space the labels need.

    Without this a node near the edge gets its name clipped - 'Indoor Sports
    Complex' ran off the left of the canvas the first time this map was
    drawn. Labels are centred on their node and sit LABEL_DY above it, so the
    box grows by half the text width on each side and by a label height on
    top.
    """
    offsets = _label_offsets(graph)
    xs = [graph.coords(n)[0] for n in graph]
    ys = [graph.coords(n)[1] for n in graph]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    for node in graph:
        x, y = graph.coords(node)
        half = _text_width(graph.name(node), NODE_LABEL_SIZE, bold=True) / 2
        dy, anchor = offsets[node]
        left = x - 2 * half if anchor == "end" else (x if anchor == "start" else x - half)
        right = x if anchor == "end" else (x + 2 * half if anchor == "start" else x + half)
        minx = min(minx, left)
        maxx = max(maxx, right)
        if dy > 0:
            maxy = max(maxy, y + dy + 4)
        else:
            miny = min(miny, y + dy - 2)
    return minx, miny, maxx, maxy


NODE_LABEL_SIZE = 11.5
LABEL_GAP = 15.5


def _label_offsets(graph: CampusGraph) -> dict[str, tuple[float, str]]:
    """
    Where to put each node's name: (vertical offset, text anchor).

    Crowded campuses put labels on top of each other - Gate 2 sits 70 m from
    Block A, which is nothing at this scale. So each label is tried in six
    positions, in order, and the first one that collides with nothing wins:

        above  / below  / above-left / above-right / below-left / below-right

    The anchor shifts with the position, so a "left" variant ends at the node
    instead of starting there. Deterministic: nodes are processed top to
    bottom, then by name.
    """
    placed: list[tuple[float, float, float, float]] = []
    offsets: dict[str, tuple[float, str]] = {}

    def rect(x: float, baseline: float, text: str, anchor: str):
        half = _text_width(text, NODE_LABEL_SIZE, bold=True) / 2
        if anchor == "middle":
            left, right = x - half, x + half
        elif anchor == "end":              # text ends at x -> sits to the left
            left, right = x - 2 * half, x
        else:                              # "start" -> sits to the right
            left, right = x, x + 2 * half
        return (left, baseline - NODE_LABEL_SIZE * 0.78,
                right, baseline + NODE_LABEL_SIZE * 0.22)

    def collides(r) -> bool:
        for o in placed:
            if r[0] < o[2] and o[0] < r[2] and r[1] < o[3] and o[1] < r[3]:
                return True
        return False

    up, down = -LABEL_GAP, LABEL_GAP + 6
    candidates = [(up, "middle"), (down, "middle"),
                  (up, "start"), (up, "end"), (down, "start"), (down, "end")]

    for node in sorted(graph, key=lambda n: (graph.coords(n)[1], graph.name(n))):
        x, y = graph.coords(node)
        name = graph.name(node)
        chosen = candidates[0]
        for dy, anchor in candidates:
            if not collides(rect(x, y + dy, name, anchor)):
                chosen = (dy, anchor)
                break
        else:
            # nothing fits - push it further up, which is at least readable
            chosen = (up - 14, "middle")
        offsets[node] = chosen
        placed.append(rect(x, y + chosen[0], name, chosen[1]))
    return offsets


def _node_label_boxes(graph: CampusGraph,
                      offsets: dict[str, tuple[float, str]]
                      ) -> list[tuple[float, float, float, float]]:
    boxes = []
    for node in graph:
        x, y = graph.coords(node)
        half = _text_width(graph.name(node), NODE_LABEL_SIZE, bold=True) / 2
        dy, anchor = offsets[node]
        left = x - 2 * half if anchor == "end" else (x if anchor == "start" else x - half)
        right = x if anchor == "end" else (x + 2 * half if anchor == "start" else x + half)
        base = y + dy
        boxes.append((left, base - NODE_LABEL_SIZE * 0.78,
                      right, base + NODE_LABEL_SIZE * 0.22))
    return boxes


class _Layout:
    """Canvas geometry: a header band, the map body, a footer band."""

    def __init__(self, graph: CampusGraph, title: str, subtitle: str,
                 note: str = "") -> None:
        self.minx, self.miny, self.maxx, self.maxy = _bounds(graph)
        self.map_w = self.maxx - self.minx
        self.map_h = self.maxy - self.miny

        self.width = max(MIN_WIDTH, self.map_w + 2 * PAD_X)
        self.text_w = self.width - 24

        self.title_lines = _wrap(title, TITLE_SIZE, self.text_w, bold=True)
        self.sub_lines = _wrap(subtitle, SUB_SIZE, self.text_w)
        self.note_lines = _wrap(note, NOTE_SIZE, self.text_w)

        self.header_h = 18.0 + 24.0 * len(self.title_lines)
        if self.sub_lines:
            self.header_h += 6.0 + 18.0 * len(self.sub_lines)
        self.footer_h = 14.0 + 17.0 * len(self.note_lines) if self.note_lines else 6.0

        self.x0 = (self.minx + self.maxx) / 2 - self.width / 2
        self.y0 = self.miny - PAD_TOP - self.header_h
        self.height = self.header_h + PAD_TOP + self.map_h + PAD_BOTTOM + self.footer_h

    def viewbox(self) -> str:
        return f"{self.x0:.1f} {self.y0:.1f} {self.width:.1f} {self.height:.1f}"

    def header(self, parts: list[str]) -> None:
        """Title and subtitle inside the reserved band."""
        y = self.y0 + 30
        for line in self.title_lines:
            _label(parts, self.x0 + 12, y, line, size=TITLE_SIZE,
                   weight=700, anchor="start", halo=0)
            y += 24
        if self.sub_lines:
            y += 6
            for line in self.sub_lines:
                _label(parts, self.x0 + 12, y, line, size=SUB_SIZE,
                       fill=MUTED, weight=400, anchor="start", halo=0)
                y += 18

    def footer(self, parts: list[str], note: str | None = None) -> None:
        y = self.maxy + PAD_BOTTOM + 20
        for line in (self.note_lines if note is None else _wrap(note, NOTE_SIZE,
                                                                self.text_w)):
            _label(parts, self.x0 + 12, y, line, size=NOTE_SIZE, fill=FAINT,
                   weight=400, anchor="start", halo=0)
            y += 17


def _note(graph: CampusGraph, width: float, height: float) -> str:
    """
    Footer caption. Always carries the campus label and, when the dataset
    says so, the fact that it is synthetic - so a figure can never be read as
    a survey of a real place.
    """
    parts = [f"{graph.label}: {graph.num_nodes} locations, "
             f"{graph.num_edges} pathways, "
             f"{width:.0f} m x {height:.0f} m."]
    if graph.note:
        parts.append(graph.note)
    parts.append("Numbers on pathways are metres.")
    return " ".join(parts)


def _base_layers(graph: CampusGraph) -> str:
    """Everything, in the correct z-order, for figures with no route."""
    return _edge_layers(graph) + "\n" + _node_layers(graph)


def _edge_layers(graph: CampusGraph) -> str:
    """Pathways and their metre labels."""
    out: list[str] = []

    # --- pathways ---------------------------------------------------------
    out.append('<g stroke-linecap="round">')
    for e in graph.edges:
        x1, y1 = graph.coords(e.a)
        x2, y2 = graph.coords(e.b)
        colour = data.EDGE_COLOURS.get(e.kind, "#bdc1c6")
        width = 6 if e.kind == "road" else 4
        dash = ' stroke-dasharray="7 6"' if e.kind == "road" else ""
        out.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{colour}" stroke-width="{width}"{dash}/>'
        )
    out.append("</g>")

    # --- pathway lengths, offset perpendicular to the edge so they do not
    #     sit on the line, and nudged clear of building names. A number that
    #     would land on top of a name is moved further out along the normal,
    #     and dropped entirely if even that does not clear it - an omitted
    #     distance is better than an unreadable one.
    label_boxes = _node_label_boxes(graph, _label_offsets(graph))
    weight_boxes: list[tuple[float, float, float, float]] = []

    def free(box) -> bool:
        for o in label_boxes + weight_boxes:
            if box[0] < o[2] and o[0] < box[2] and box[1] < o[3] and o[1] < box[3]:
                return False
        return True

    for e in graph.edges:
        x1, y1 = graph.coords(e.a)
        x2, y2 = graph.coords(e.b)
        dx, dy = x2 - x1, y2 - y1
        length = (dx * dx + dy * dy) ** 0.5 or 1.0
        # unit normal, nudged so horizontal edges get the label above them
        nx, ny = -dy / length, dx / length
        if ny > 0:
            nx, ny = -nx, -ny
        placed_label = False
        for off in (10.0, 18.0, 26.0, 34.0):
            mx = (x1 + x2) / 2 + nx * off
            my = (y1 + y2) / 2 + ny * off
            box = (mx - len(str(e.weight)) * 2.9, my - 7.4,
                   mx + len(str(e.weight)) * 2.9, my + 2.1)
            if free(box):
                _label(out, mx, my + 3.2, str(e.weight), size=9.5,
                       fill=FAINT, weight=500, halo=2.6)
                weight_boxes.append(box)
                placed_label = True
                break
        if not placed_label:
            continue

    return "\n".join(out)


def _node_layers(graph: CampusGraph) -> str:
    """Location dots and names - drawn last so routes never hide them."""
    out: list[str] = []
    for node in graph:
        x, y = graph.coords(node)
        colour = data.CATEGORY_COLOURS.get(graph.kind(node), "#1a73e8")
        out.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{NODE_R}" fill="#fff" '
            f'stroke="{colour}" stroke-width="3.5"/>'
        )
    offsets = _label_offsets(graph)
    for node in graph:
        x, y = graph.coords(node)
        dy, anchor = offsets[node]
        _label(out, x, y + dy, graph.name(node), size=NODE_LABEL_SIZE,
               weight=600, halo=3.4, anchor=anchor)
    return "\n".join(out)


def _polyline(parts: list[str], graph: CampusGraph, route: Route,
              colour: str, width: float = 6.5, dash: str = "",
              halo: bool = True) -> None:
    pts = " ".join(f"{graph.coords(n)[0]:.1f},{graph.coords(n)[1]:.1f}"
                   for n in route.path)
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    if halo:
        parts.append(
            f'<polyline points="{pts}" fill="none" stroke="#fff" '
            f'stroke-width="{width + 6:g}" stroke-linecap="round" '
            f'stroke-linejoin="round" opacity="0.9"/>'
        )
    parts.append(
        f'<polyline points="{pts}" fill="none" stroke="{colour}" '
        f'stroke-width="{width:g}" stroke-linecap="round" '
        f'stroke-linejoin="round"{dash_attr}/>'
    )


def _endpoint_rings(parts: list[str], graph: CampusGraph, route: Route,
                    colour: str = INK) -> None:
    for node in (route.path[0], route.path[-1]):
        x, y = graph.coords(node)
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{NODE_R + 6}" fill="none" '
            f'stroke="{colour}" stroke-width="2.5"/>'
        )


def render_svg(
    graph: CampusGraph,
    route: Route | None = None,
    *,
    title: str = "",
    subtitle: str = "",
) -> str:
    """Return a standalone SVG document of the campus, optionally routed."""
    title = title or graph.label
    if route is not None and route.path:
        unit = "pathways" if route.algorithm == "BFS" else "m"
        subtitle = (f"{route.algorithm}: {route.hops} pathways, "
                    f"{route.cost:g} {unit} walked, "
                    f"{route.expanded} nodes expanded")

    minx, miny, maxx, maxy = _bounds(graph)
    note = _note(graph, maxx - minx, maxy - miny)
    lay = _Layout(graph, title, subtitle, note)

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="{lay.viewbox()}" width="{lay.width:.0f}" '
        f'height="{lay.height:.0f}" role="img" '
        f'aria-label="{html.escape(title)}">',
        f'<rect x="{lay.x0:.1f}" y="{lay.y0:.1f}" width="{lay.width:.1f}" '
        f'height="{lay.height:.1f}" fill="#ffffff"/>',
        f'<g id="edges">\n{_edge_layers(graph)}\n</g>',
    ]
    if route is not None and route.path:
        _polyline(parts, graph, route, ROUTE_COLOUR)
        _endpoint_rings(parts, graph, route)
    parts.append(f'<g id="nodes">\n{_node_layers(graph)}\n</g>')

    lay.header(parts)
    lay.footer(parts)
    parts.append("</svg>")
    return "\n".join(parts)


def write_svg(graph: CampusGraph, out: str | Path, **kwargs) -> Path:
    p = Path(out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render_svg(graph, **kwargs), encoding="utf-8")
    return p


def render_comparison_svg(
    graph: CampusGraph, start: str, goal: str, *, title: str = ""
) -> str:
    """
    One figure with both answers drawn on top of each other:
      orange dashed = BFS      (fewest pathways)
      blue  solid   = Dijkstra (fewest metres)
    The visual proof that the two objectives disagree on this campus.
    """
    bfs = algorithms.bfs_shortest_path(graph, start, goal)
    dij = algorithms.dijkstra(graph, start, goal)
    ast = algorithms.a_star(graph, start, goal)
    bfs_metres = sum(graph.weight(u, v) for u, v in zip(bfs.path, bfs.path[1:]))

    heading = title or f"{graph.name(start)} to {graph.name(goal)}"
    subtitle = (
        f"BFS took the {bfs.hops}-pathway route and walked {bfs_metres:.0f} m. "
        f"Dijkstra took the {dij.hops}-pathway route and walked "
        f"{dij.cost:.0f} m - {bfs_metres - dij.cost:.0f} m shorter. "
        f"A* found the same route as Dijkstra in {ast.expanded} expansions "
        f"vs {dij.expanded}."
    )
    lay = _Layout(graph, heading, subtitle,
                  note="Orange dashed = BFS (fewest pathways). "
                       "Blue = Dijkstra (fewest metres). "
                       "Black rings mark start and destination. "
                       + _note(graph, *[b - a for a, b in
                                        zip(_bounds(graph)[:2],
                                            _bounds(graph)[2:])]))

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="{lay.viewbox()}" width="{lay.width:.0f}" '
        f'height="{lay.height:.0f}" role="img" '
        f'aria-label="BFS versus Dijkstra route comparison">',
        f'<rect x="{lay.x0:.1f}" y="{lay.y0:.1f}" width="{lay.width:.1f}" '
        f'height="{lay.height:.1f}" fill="#ffffff"/>',
        f'<g id="edges">\n{_edge_layers(graph)}\n</g>',
    ]
    _polyline(parts, graph, bfs, BFS_COLOUR, dash="11 8")
    _polyline(parts, graph, dij, ROUTE_COLOUR)
    _endpoint_rings(parts, graph, dij)
    parts.append(f'<g id="nodes">\n{_node_layers(graph)}\n</g>')

    lay.header(parts)
    lay.footer(parts)
    parts.append("</svg>")
    return "\n".join(parts)


def write_comparison_svg(
    graph: CampusGraph, out: str | Path, start: str, goal: str, **kwargs
) -> Path:
    p = Path(out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render_comparison_svg(graph, start, goal, **kwargs), encoding="utf-8")
    return p


# --------------------------------------------------------------------------
# interactive demo
# --------------------------------------------------------------------------
def precompute_all_pairs(graph: CampusGraph) -> dict:
    """Run all three algorithms for every origin/destination pair."""
    payload: dict[str, dict] = {}
    for a, b in iter_pairs(graph.nodes):
        for name, fn in (("bfs", ALGORITHMS["bfs"]),
                         ("dijkstra", ALGORITHMS["dijkstra"]),
                         ("astar", ALGORITHMS["astar"])):
            try:
                r = fn(graph, a, b)
            except Exception:  # pragma: no cover - graph is connected
                continue
            payload.setdefault(f"{a}|{b}", {})[name] = {
                "path": r.path,
                "cost": r.cost,
                "hops": r.hops,
                "expanded": r.expanded,
                "visited": r.visited,
            }
    return payload


def pick_demos(graph: CampusGraph, routes: dict, limit: int = 3) -> list[list[str]]:
    """Choose example journeys that are real *for this graph*.

    This used to ship a hand-picked list from the synthetic sample campus
    unchanged, so the real campus got links to node ids it does not have.
    The browser did `N[a].name` on a missing id, threw, and the whole page
    died. Examples are derived from the graph being rendered instead, and
    they prefer pairs where BFS and Dijkstra genuinely disagree - which is
    the interesting thing to show anyway.
    """
    scored: list[tuple[float, list[str]]] = []
    for key, by_algo in routes.items():
        bfs, dij = by_algo.get("bfs"), by_algo.get("dijkstra")
        if not bfs or not dij:
            continue
        a, b = key.split("|")
        # BFS reports hops, so its route is re-measured in metres to compare
        gap = algorithms.all_paths_cost(graph, bfs["path"]) - dij["cost"]
        scored.append((gap, [a, b]))

    disagree = [pair for gap, pair in sorted(scored, reverse=True) if gap > 1e-9]
    if len(disagree) >= limit:
        return disagree[:limit]

    # nothing disagrees, or too few: fall back to the longest journeys
    longest = [pair for _, pair in sorted(scored, key=lambda t: t[0])][:0]
    by_cost = sorted(scored, key=lambda t: t[0])
    return disagree + [pair for _, pair in reversed(by_cost)
                       if pair not in disagree][:limit - len(disagree)]


def build_html(graph: CampusGraph, out: str | Path) -> Path:
    """Write a single self-contained HTML file (no CDN, no build step)."""
    nodes = {
        n: {
            "name": graph.name(n),
            "kind": graph.kind(n),
            "x": graph.coords(n)[0],
            "y": graph.coords(n)[1],
            "degree": graph.degree(n),
        }
        for n in graph
    }
    edges = [
        {"a": e.a, "b": e.b, "w": e.weight, "kind": e.kind}
        for e in graph.edges
    ]
    routes = precompute_all_pairs(graph)
    payload = {
        "nodes": nodes,
        "edges": edges,
        "routes": routes,
        "colours": data.CATEGORY_COLOURS,
        "edgeColours": data.EDGE_COLOURS,
        "demos": pick_demos(graph, routes),
        "stats": {
            "V": graph.num_nodes,
            "E": graph.num_edges,
            "connected": graph.is_connected(),
        },
    }
    payload["campus"] = {"label": graph.label, "note": graph.note}
    page = _HTML_TEMPLATE.replace("__DATA__", json.dumps(payload, separators=(",", ":")))
    p = Path(out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(page, encoding="utf-8")
    return p


_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Campus Navigation System - Interactive Map</title>
<style>
  :root{
    --bg:#f8f9fa; --card:#fff; --line:#dadce0; --ink:#202124;
    --muted:#5f6368; --blue:#1a73e8; --yellow:#fbbc04;
  }
  *{box-sizing:border-box}
  body{
    margin:0; padding:20px; background:var(--bg); color:var(--ink);
    font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  }
  header{max-width:1180px;margin:0 auto 16px}
  h1{font-size:22px;margin:0 0 4px}
  .sub{color:var(--muted);font-size:13px}
  .layout{
    max-width:1180px;margin:0 auto;display:grid;
    grid-template-columns:310px 1fr;gap:16px;align-items:start
  }
  @media(max-width:860px){.layout{grid-template-columns:1fr}}
  .card{
    background:var(--card);border:1px solid var(--line);border-radius:12px;
    padding:16px
  }
  label{display:block;font-size:12px;font-weight:600;color:var(--muted);
    text-transform:uppercase;letter-spacing:.04em;margin:12px 0 5px}
  label:first-child{margin-top:0}
  select,button{
    width:100%;padding:9px 10px;border:1px solid var(--line);border-radius:8px;
    background:#fff;font:inherit;color:inherit
  }
  select:focus,button:focus{outline:2px solid var(--blue);outline-offset:1px}
  .algos{display:flex;gap:6px}
  .algos label{
    flex:1;margin:0;text-transform:none;letter-spacing:0;font-weight:500;
    font-size:13px;color:var(--ink);border:1px solid var(--line);
    border-radius:8px;padding:8px 4px;text-align:center;cursor:pointer;
    transition:.15s
  }
  .algos input{position:absolute;opacity:0;pointer-events:none}
  .algos label:has(input:checked){
    border-color:var(--blue);background:#e8f0fe;color:var(--blue);font-weight:700
  }
  button.go{
    margin-top:14px;background:var(--blue);color:#fff;border-color:var(--blue);
    font-weight:600;cursor:pointer
  }
  button.go:hover{background:#1765cc}
  .row{display:flex;justify-content:space-between;padding:5px 0;
    border-bottom:1px dashed var(--line);font-size:13px}
  .row:last-child{border-bottom:0}
  .row b{font-variant-numeric:tabular-nums}
  .legend{display:flex;flex-wrap:wrap;gap:10px;margin-top:12px;font-size:12px;
    color:var(--muted)}
  .legend i{width:11px;height:11px;border-radius:50%;display:inline-block;
    margin-right:5px;vertical-align:-1px;border:2.5px solid}
  .route-title{font-weight:600;margin:14px 0 6px;font-size:13px}
  .badge{display:inline-block;background:var(--yellow);color:#3c2a00;
    border-radius:999px;padding:2px 9px;font-size:11px;font-weight:700;
    margin-left:6px}
  svg{display:block;width:100%;height:auto;touch-action:none}
  .pathlist{max-height:150px;overflow:auto;font-size:13px;margin:0;padding-left:18px}
  .pathlist li{padding:2px 0}
  .hint{font-size:12px;color:var(--muted);margin-top:10px}
  .err{background:#fce8e6;color:#a50e0e;border-radius:8px;padding:9px 11px;
    font-size:13px;margin-top:12px}
</style>
</head>
<body>
<header>
  <h1 id="h1">Campus Navigation System</h1>
  <div class="sub" id="sub"></div>
  <div class="sub" id="campus-note" style="font-style:italic"></div>
</header>

<div class="layout">
  <div>
    <div class="card">
      <label for="from">Start</label>
      <select id="from"></select>
      <label for="to">Destination</label>
      <select id="to"></select>
      <label>Algorithm</label>
      <div class="algos">
        <label><input type="radio" name="algo" value="bfs">BFS</label>
        <label><input type="radio" name="algo" value="dijkstra" checked>Dijkstra</label>
        <label><input type="radio" name="algo" value="astar">A*</label>
      </div>
      <button class="go" id="go">Find route</button>
      <div id="err"></div>
      <div class="legend" id="legend"></div>
    </div>

    <div class="card" style="margin-top:16px">
      <div class="route-title" id="rtitle">Result</div>
      <div id="result"></div>
      <div class="route-title" style="margin-top:14px">Algorithm comparison</div>
      <div id="compare"></div>
      <div class="hint">Same graph, three algorithms. Watch the yellow search
        frontier, then the blue route.</div>
    </div>
  </div>

  <div class="card" style="padding:8px">
    <svg id="map" viewBox="0 0 1 1" aria-label="Campus map"></svg>
  </div>
</div>

<script>
const DATA = __DATA__;
const N = DATA.nodes, E = DATA.edges, R = DATA.routes;

/* ---------- viewport ---------- */
let x0=Infinity,y0=Infinity,x1=-Infinity,y1=-Infinity;
for (const k in N){const n=N[k];x0=Math.min(x0,n.x);y0=Math.min(y0,n.y);
  x1=Math.max(x1,n.x);y1=Math.max(y1,n.y);}
const PAD=48, VW=x1-x0+2*PAD, VH=y1-y0+2*PAD;
const svg=document.getElementById('map');
svg.setAttribute('viewBox',`${x0-PAD} ${y0-PAD} ${VW} ${VH}`);
const NS='http://www.w3.org/2000/svg';
function el(tag,attrs,parent){const e=document.createElementNS(NS,tag);
  for(const k in attrs)e.setAttribute(k,attrs[k]);(parent||svg).appendChild(e);return e;}
document.getElementById('h1').textContent = DATA.campus.label;
document.getElementById('campus-note').textContent = DATA.campus.note || '';
const title=document.getElementById('sub');
title.textContent=`${DATA.stats.V} locations, ${DATA.stats.E} pathways, `
  +`${DATA.stats.connected?'fully connected':'disconnected'} - edge labels in metres`;

/* ---------- static layers ---------- */
const gEdges=el('g',{});
for(const e of E){
  const a=N[e.a],b=N[e.b];
  el('line',{x1:a.x,y1:a.y,x2:b.x,y2:b.y,
    stroke:DATA.edgeColours[e.kind]||'#bdc1c6',
    'stroke-width':e.kind==='road'?6:4,'stroke-linecap':'round',
    'stroke-dasharray':e.kind==='road'?'7 6':''},gEdges);
}
for(const e of E){
  const a=N[e.a],b=N[e.b];
  const t=el('text',{x:(a.x+b.x)/2,y:(a.y+b.y)/2-4,'text-anchor':'middle',
    'font-size':9,fill:'#9aa0a6'},gEdges);
  t.textContent=e.w;
}
/* z-order: edges -> search frontier -> route -> node names -> endpoint rings.
   The route must not paint over the building names it connects. */
const gSeen=el('g',{}), gRoute=el('g',{}), gNodes=el('g',{}), gMarks=el('g',{});
function haloText(parent,x,y,text,size,weight,colour){
  const t=el('text',{x:x,y:y,'text-anchor':'middle','font-size':size,
    'font-weight':weight,fill:'none',stroke:'#fff','stroke-width':3.5,
    'stroke-linejoin':'round'},parent);
  t.textContent=text;
  const f=el('text',{x:x,y:y,'text-anchor':'middle','font-size':size,
    'font-weight':weight,fill:colour},parent);
  f.textContent=text;
}
for(const k in N){
  const n=N[k];
  el('circle',{cx:n.x,cy:n.y,r:8.5,fill:'#fff',
    stroke:DATA.colours[n.kind]||'#1a73e8','stroke-width':3.5},gNodes);
}
for(const k in N){
  const n=N[k];
  haloText(gNodes,n.x,n.y-15,n.name,11.5,600,'#202124');
}

/* legend */
const legend=document.getElementById('legend');
const KINDS={gate:'Gate / entrance',academic:'Academic',amenity:'Amenity',
  sports:'Sports',hostel:'Hostel',transit:'Transit'};
for(const k in KINDS){
  const s=document.createElement('span');
  s.innerHTML=`<i style="border-color:${DATA.colours[k]}"></i>${KINDS[k]}`;
  legend.appendChild(s);
}

/* ---------- controls ---------- */
const fromSel=document.getElementById('from'), toSel=document.getElementById('to');
const ids=Object.keys(N).sort((a,b)=>N[a].name.localeCompare(N[b].name));
for(const id of ids){
  fromSel.add(new Option(`${N[id].name}  (${id})`,id));
  toSel.add(new Option(`${N[id].name}  (${id})`,id));
}
const demos=(DATA.demos||[]).filter(([a,b])=>N[a]&&N[b]);
if(demos.length){
  fromSel.value=demos[0][0]; toSel.value=demos[0][1];
}else{
  fromSel.value=ids[0]; toSel.value=ids[Math.min(1,ids.length-1)];
}
const quick=document.createElement('div');
quick.className='hint';
quick.innerHTML='Try a pair where the algorithms disagree: '+demos.map(
  ([a,b])=>`<a href="#" data-a="${a}" data-b="${b}">${N[a].name} &rarr; ${N[b].name}</a>`
).join(' &middot; ');
document.querySelector('.card').appendChild(quick);
quick.addEventListener('click',ev=>{
  const t=ev.target.closest('a'); if(!t)return; ev.preventDefault();
  fromSel.value=t.dataset.a; toSel.value=t.dataset.b; run();
});

let timers=[];
function clearAnim(){timers.forEach(clearTimeout);timers=[];gSeen.innerHTML='';
  gRoute.innerHTML='';gMarks.innerHTML='';}

function pairKey(a,b){return R[`${a}|${b}`]?`${a}|${b}`:(R[`${b}|${a}`]?`${b}|${a}`:null);}

function run(){
  const a=fromSel.value,b=toSel.value;
  const algo=document.querySelector('input[name=algo]:checked').value;
  const key=pairKey(a,b);
  const errBox=document.getElementById('err');
  errBox.innerHTML='';
  clearAnim();

  if(!key || a===b){
    errBox.innerHTML = a===b
      ? '<div class="err">Start and destination are the same location.</div>'
      : '<div class="err">No route between these locations.</div>';
    document.getElementById('result').innerHTML='';
    document.getElementById('compare').innerHTML='';
    document.getElementById('rtitle').textContent='Result';
    return;
  }
  const set=R[key], r=set[algo];
  const flip=key!==`${a}|${b}`;
  const path=flip?[...r.path].reverse():r.path;
  const visited=r.visited;

  /* animate: yellow search frontier, then the blue route */
  const seenNodes=new Set();
  visited.forEach((node,i)=>{
    timers.push(setTimeout(()=>{
      const n=N[node]; seenNodes.add(node);
      if(!gSeen.querySelector(`[data-k="${node}"]`)){
        el('circle',{cx:n.x,cy:n.y,r:13,fill:'#fbbc04',opacity:.45,
          'data-k':node},gSeen);
      }
    }, i*Math.min(90, 900/visited.length)));
  });

  const pts=path.map(id=>`${N[id].x},${N[id].y}`).join(' ');
  const delay=visited.length*Math.min(90,900/visited.length)+120;
  timers.push(setTimeout(()=>{
    el('polyline',{points:pts,fill:'none',stroke:'#fff','stroke-width':13,
      'stroke-linecap':'round','stroke-linejoin':'round',opacity:.9},gRoute);
    const line=el('polyline',{points:pts,fill:'none',stroke:'#1a73e8',
      'stroke-width':6.5,'stroke-linecap':'round','stroke-linejoin':'round'},gRoute);
    /* Draw-on animation. getTotalLength is not implemented everywhere
       (headless renderers, for one), so fall back to showing the line
       outright rather than throwing and losing the whole route. */
    if(typeof line.getTotalLength==='function'&&typeof line.animate==='function'){
      const len=line.getTotalLength();
      line.style.strokeDasharray=len; line.style.strokeDashoffset=len;
      line.animate([{strokeDashoffset:len},{strokeDashoffset:0}],
        {duration:600,easing:'ease-out',fill:'forwards'});
    }
    for(const id of [path[0],path[path.length-1]]){
      el('circle',{cx:N[id].x,cy:N[id].y,r:13.5,fill:'none',stroke:'#1a73e8',
        'stroke-width':3},gMarks);
    }
  },delay));

  /* text result */
  const unit = algo==='bfs' ? 'pathways' : 'metres';
  document.getElementById('rtitle').innerHTML =
    `${N[path[0]].name} &rarr; ${N[path[path.length-1]].name}`
    + `<span class="badge">${algo==='astar'?'A*':algo.toUpperCase()}</span>`;
  document.getElementById('result').innerHTML =
    `<div class="row"><span>Pathways walked (hops)</span><b>${r.hops}</b></div>
     <div class="row"><span>Total cost</span><b>${r.cost} ${unit}</b></div>
     <div class="row"><span>Nodes expanded</span><b>${r.expanded}</b></div>
     <div class="row"><span>Search touched</span><b>${visited.length}</b></div>
     <ol class="pathlist">${path.map(id=>`<li>${N[id].name}</li>`).join('')}</ol>`;

  const order=['bfs','dijkstra','astar'];
  const labels={bfs:'BFS',dijkstra:'Dijkstra',astar:'A*'};
  document.getElementById('compare').innerHTML = order.map(k=>{
    const o=set[k], mine=k===algo;
    const cost = k==='bfs' ? `${o.cost} hops` : `${o.cost} m`;
    return `<div class="row" style="${mine?'font-weight:700;color:#1a73e8':''}">
      <span>${labels[k]}${mine?' (selected)':''}</span>
      <b>${cost} &middot; ${o.expanded} exp.</b></div>`;
  }).join('');
}

document.getElementById('go').addEventListener('click',run);
document.querySelectorAll('input[name=algo]').forEach(
  i=>i.addEventListener('change',run));
fromSel.addEventListener('change',run);
toSel.addEventListener('change',run);
run();
</script>
</body>
</html>
"""
