#!/usr/bin/env python3
"""
Build docs/compare-original-vs-real.html - the "before and after" page.

Embeds both maps inline (as data URIs, so the page is self-contained and
works offline with no network access) with a table of exactly what changed.
Run it after regenerating the maps:

    python gen_docs.py -c campuses/usar-east-campus.json
    python tools/make_comparison.py
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

V1 = DOCS / "archive" / "campus-map-v1-invented.svg"
V2 = DOCS / "campus-map.svg"
OUT = DOCS / "compare-original-vs-real.html"


def data_uri(path: Path) -> str:
    blob = base64.b64encode(path.read_bytes()).decode()
    return f"data:image/svg+xml;base64,{blob}"


def diff_table() -> str:
    """What actually differs, read from the two datasets."""
    old = json.loads((ROOT / "campuses" / "sample-campus.json").read_text())
    new = json.loads((ROOT / "campuses" / "usar-east-campus.json").read_text())

    old_names = {v["name"] for v in old["locations"].values()}
    new_names = {v["name"] for v in new["locations"].values()}
    sourced = sum(1 for v in new["locations"].values()
                  if str(v.get("source", "")).startswith("osm:"))
    traced = len(new["locations"]) - sourced

    rows = [
        ("Where the buildings are",
         "Invented by an AI assistant",
         "Traced from your satellite screenshot + OpenStreetMap"),

        ("Can a reviewer check it?",
         "No — no source, no way to verify",
         f"Yes — {sourced} locations carry an OSM feature id "
         f"(e.g. <code>way/1186488777</code>); {traced} carry the pixel they "
         f"were read from"),

        ("The college's name appears in the data",
         "Yes — a node literally called <b>“USAR Building”</b> on an invented "
         "campus. Removed from the synthetic dataset entirely.",
         "Yes, and that is correct — it is the real campus"),

        ("Does it match the real layout?",
         "No — a generic grid. The gate, the ground, the hostel cluster and "
         "the boundary road were all in the wrong places or missing.",
         "Yes — USAR Ground, Gurdwara Rd, the hostel cluster and both gates "
         "sit where your screenshot shows them"),

        ("Locations",
         f"{len(old['locations'])} · {', '.join(sorted(old_names)[:5])}…",
         f"{len(new['locations'])} · {', '.join(sorted(new_names)[:5])}…"),

        ("Distances",
         "Made up",
         "Derived from coordinates: OSM to ~1 m, traced to ~±10 m"),

        ("Known gaps",
         "None declared — it looked complete",
         "Declared: 2 buildings unnamed in OSM, 2 gates disagree by ~100 m, "
         "Surajmal Park placed from the screenshot not OSM, every path "
         "marked <code>inferred</code>"),
    ]
    out = ['<table class="diff"><thead><tr>'
           '<th></th><th class="old">Before — invented</th>'
           '<th class="new">Now — real campus</th></tr></thead><tbody>']
    for label, a, b in rows:
        out.append(f"<tr><th>{label}</th><td>{a}</td><td>{b}</td></tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def main() -> None:
    if not V1.exists():
        raise SystemExit(f"missing {V1} - extract it with:\n"
                         f"  git show ff18d3a:docs/campus-map.svg > {V1}")
    if not V2.exists():
        raise SystemExit(f"missing {V2} - run gen_docs.py first")

    page = TEMPLATE.replace("__OLD__", data_uri(V1)) \
                   .replace("__NEW__", data_uri(V2)) \
                   .replace("__DIFF__", diff_table())
    OUT.write_text(page, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}  ({OUT.stat().st_size / 1024:.0f} KB)")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The map, before and after</title>
<style>
  :root{--ink:#202124;--muted:#5f6368;--line:#dadce0;--bad:#d93025;--ok:#0f9d58}
  *{box-sizing:border-box}
  body{margin:0;padding:24px;background:#f8f9fa;color:var(--ink);
    font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
  .wrap{max-width:1400px;margin:0 auto}
  h1{font-size:24px;margin:0 0 6px}
  .sub{color:var(--muted);margin-bottom:22px}
  .panels{display:grid;grid-template-columns:1fr 1fr;gap:18px;align-items:start}
  @media(max-width:900px){.panels{grid-template-columns:1fr}}
  .panel{background:#fff;border:1px solid var(--line);border-radius:12px;
    padding:14px;overflow:hidden}
  .panel.old{border-top:4px solid var(--bad)}
  .panel.new{border-top:4px solid var(--ok)}
  .tag{display:inline-block;font-size:11px;font-weight:700;letter-spacing:.06em;
    text-transform:uppercase;border-radius:999px;padding:3px 10px;margin-bottom:8px}
  .old .tag{background:#fce8e6;color:var(--bad)}
  .new .tag{background:#e6f4ea;color:var(--ok)}
  .panel img{width:100%;height:auto;display:block;border-radius:8px}
  .panel p{font-size:13px;color:var(--muted);margin:10px 0 0}
  table.diff{width:100%;border-collapse:collapse;margin-top:26px;background:#fff;
    border:1px solid var(--line);border-radius:12px;overflow:hidden;font-size:14px}
  table.diff th,table.diff td{padding:11px 14px;text-align:left;
    border-bottom:1px solid var(--line);vertical-align:top}
  table.diff thead th{font-size:12px;text-transform:uppercase;
    letter-spacing:.05em;color:var(--muted)}
  table.diff thead th.old{color:var(--bad)}
  table.diff thead th.new{color:var(--ok)}
  table.diff tbody th{font-weight:600;width:22%;background:#fafafa}
  table.diff tbody tr:last-child th,table.diff tbody tr:last-child td{border-bottom:0}
  table.diff td:first-of-type{background:#fffaf9}
  code{background:#f1f3f4;border-radius:4px;padding:1px 5px;font-size:12.5px}
  .foot{margin-top:22px;font-size:13px;color:var(--muted)}
</style>
</head>
<body>
<div class="wrap">
  <h1>The map, before and after</h1>
  <div class="sub">Both maps are drawn by the same code from the same
    algorithms. The only thing that changed is <b>where the data came
    from</b>.</div>

  <div class="panels">
    <div class="panel old">
      <span class="tag">Before — invented</span>
      <img src="__OLD__" alt="The original invented campus map">
      <p>14 buildings with plausible names, invented coordinates, invented
        distances — including a node called “USAR Building”. A reviewer has
        no way to check a single number, and anyone who knows the campus
        can tell immediately.</p>
    </div>
    <div class="panel new">
      <span class="tag">Now — the real campus</span>
      <img src="__NEW__" alt="The current USAR campus map">
      <p>Laid out from your satellite screenshot and OpenStreetMap building
        coordinates. Every point declares whether it is a surveyed OSM
        feature or a pixel measurement from the screenshot, and the
        remaining gaps are listed rather than filled in with guesses.</p>
    </div>
  </div>

  __DIFF__

  <div class="foot">
    The invented map is kept at
    <code>docs/archive/campus-map-v1-invented.svg</code>,
    and the synthetic dataset it came from is now clearly labelled
    <i>“Sample Campus (synthetic)”</i> with the college's name removed —
    it is still useful, because it is the dataset where BFS and Dijkstra
    actually disagree.
  </div>
</div>
</body>
</html>
"""


if __name__ == "__main__":
    main()
