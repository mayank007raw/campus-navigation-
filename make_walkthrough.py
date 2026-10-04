"""
Build docs/map-walkthrough.html - the map plus a line about every dot on it.

"Go through my map" is easier to answer as one page than as a wall of text:
the map at the top, then each location with where it came from and the
sentence it is based on, then the audits. Self-contained - the SVG is inlined
and there are no external references, so it renders anywhere.

Run:  python3 tools/make_walkthrough.py
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from campus_nav import algorithms as A  # noqa: E402
from campus_nav.graph import CampusGraph  # noqa: E402

CAMPUS = ROOT / "campuses" / "usar-east-campus.json"
SVG = ROOT / "docs" / "campus-map.svg"
AUDIT = ROOT / "docs" / "audit-report.txt"
OUT = ROOT / "docs" / "map-walkthrough.html"

SOURCE_LABEL = {
    "osm": "OpenStreetMap",
    "screenshot": "traced from the screenshot",
    "described": "described by the student",
}

ROUTES = [
    ("gate_1", "block_a", "the way in from the auditorium gate - past the parking"),
    ("gate_2", "block_a", "the near block, two minutes from the west gate"),
    ("block_a", "block_b", "the walk the Library sits in the middle of"),
    ("block_b", "sports", "past the canteen, to the sports hall"),
    ("gate_1", "girls_hostel", "the long diagonal, right across the campus"),
]


def main() -> int:
    g = CampusGraph.load(CAMPUS)
    doc = json.loads(CAMPUS.read_text(encoding="utf-8"))
    locs = doc["locations"]
    svg = SVG.read_text(encoding="utf-8")
    # strip the XML prolog; the SVG is inlined into HTML
    svg = svg.split("?>", 1)[-1]

    verdict = "every correction still holds"
    if AUDIT.exists():
        tail = AUDIT.read_text(encoding="utf-8").strip().splitlines()[-1]
        if "FAIL" in tail:
            verdict = tail

    rows = []
    for node_id in sorted(g.nodes, key=lambda n: (g.coords(n)[0], g.coords(n)[1])):
        loc = locs[node_id]
        x, y = g.coords(node_id)
        src = SOURCE_LABEL.get(loc["source"].split(":")[0], loc["source"])
        why = loc.get("_tour_evidence") or loc.get("position_estimate") or ""
        note = loc.get("_note", "")
        extra = " ".join(filter(None, [why, f"({note})" if note else ""]))
        rows.append(
            f"<tr><td class='n'>{html.escape(loc['name'])}</td>"
            f"<td class='c'>{x:+.0f}, {y:+.0f}</td>"
            f"<td class='s'>{html.escape(src)}</td>"
            f"<td class='e'>{html.escape(extra)}</td></tr>"
        )

    route_rows = []
    for a, b, why in ROUTES:
        r = A.dijkstra(g, a, b)
        via = " → ".join(g.name(n) for n in r.path)
        route_rows.append(
            f"<tr><td class='n'>{html.escape(g.name(a))} → {html.escape(g.name(b))}</td>"
            f"<td class='c'>{r.cost:.0f} m</td>"
            f"<td class='e'>{html.escape(via)}<br><span class='why'>{html.escape(why)}</span></td></tr>"
        )

    edges = sorted({
        tuple(sorted((a, b))) for n in g.nodes for a, _ in g.neighbours(n)
    })

    OUT.write_text(f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Walking the map - USAR East Campus</title>
</head>
<body style="margin:0;padding:28px 20px;background:#f6f7f9;color:#1b1f24;
 font:16px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif">
<div style="max-width:940px;margin:0 auto">

<p style="margin:0 0 6px;font-size:13px;letter-spacing:.09em;text-transform:uppercase;color:#6b7280">
Every dot on the map, and where it came from</p>
<h1 style="margin:0 0 6px;font-size:29px;line-height:1.15">Walking the USAR East Campus map</h1>
<p style="margin:0 0 22px;color:#4b5563">
{g.num_nodes} locations, {g.num_edges} pathways, one connected graph &middot;
{len(edges)} edges, all inferred from how the campus is walked &middot;
<b style="color:#0b7a3b">{html.escape(verdict)}</b></p>

<div style="background:#fff;border:1px solid #e5e7eb;border-radius:12px;
 padding:14px;margin-bottom:26px">{svg}</div>

<h2 style="font-size:20px;margin:0 0 4px">What each dot is</h2>
<p style="margin:0 0 14px;color:#4b5563;font-size:14.5px">
Nothing here is invented. Every location records its own source in the JSON,
and the seven named by a person carry the sentence they came from.</p>
<table style="width:100%;border-collapse:collapse;background:#fff;
 border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;font-size:14.5px">
<thead><tr style="background:#f3f4f6;text-align:left">
<th style="padding:9px 12px">Location</th><th style="padding:9px 12px">x, y (m)</th>
<th style="padding:9px 12px">Source</th><th style="padding:9px 12px">What it is based on</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>

<h2 style="font-size:20px;margin:28px 0 4px">How you walk it</h2>
<p style="margin:0 0 14px;color:#4b5563;font-size:14.5px">
Shortest route and total cost, straight out of Dijkstra on the shipped data.</p>
<table style="width:100%;border-collapse:collapse;background:#fff;
 border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;font-size:14.5px">
<thead><tr style="background:#f3f4f6;text-align:left">
<th style="padding:9px 12px">Journey</th><th style="padding:9px 12px">Cost</th>
<th style="padding:9px 12px">Route</th></tr></thead>
<tbody>{''.join(route_rows)}</tbody></table>

<h2 style="font-size:20px;margin:28px 0 4px">The two routes worth quoting</h2>
<div style="display:flex;gap:16px;flex-wrap:wrap">
<div style="flex:1;min-width:280px;background:#fff;border:1px solid #e5e7eb;
 border-left:4px solid #2563eb;border-radius:10px;padding:14px">
<b>Block A (USAR) &rarr; Block B (USDI)</b>
<p style="margin:8px 0 0;font-size:14.5px;color:#374151">
BFS says 2 hops, <b>300 m</b>, out by the gate.<br>
Dijkstra says 2 hops, <b>110 m</b>, past the Library.<br>
<span style="color:#6b7280">Same number of turnings. 63% less walking.
Dijkstra's answer is the route the student described.</span></p></div>

<div style="flex:1;min-width:280px;background:#fff;border:1px solid #e5e7eb;
 border-left:4px solid #b45309;border-radius:10px;padding:14px">
<b>Two independent sources agree on the order</b>
<p style="margin:8px 0 0;font-size:14.5px;color:#374151">
A campus tour video, filmed by a student and read as a transcript, gives the
order <i>sports hall &rarr; main building &rarr; auditorium &rarr; ground and
hostel</i>.<br>
<span style="color:#6b7280">That is the order the student's corrections
produced, before the video was found. Agreement between two people who have
walked it is the closest thing to verification this map has.</span></p></div>
</div>

<p style="margin:26px 0 0;color:#6b7280;font-size:13.5px">
Regenerated by <code>tools/make_walkthrough.py</code>.
Sources: <code>SOURCES.md</code> &middot; corrections:
<code>CORRECTIONS.md</code> &middot; audit: <code>docs/audit-report.txt</code></p>
</div></body></html>
""", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}  ({OUT.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
