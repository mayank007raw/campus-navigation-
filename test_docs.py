"""
The three documents a submission is judged on must agree with the data.

Twice in this project the code was right and the prose was not: README counts
drifted from the campus file, and CORRECTIONS.md fell three corrections
behind the builder without anything failing. Documentation that silently
disagrees with the code is worse than no documentation, because a reader has
no way to tell which half to trust. These tests make the drift loud.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

USAR = ROOT / "campuses" / "usar-east-campus.json"
README = ROOT / "README.md"
CORRECTIONS = ROOT / "CORRECTIONS.md"


def _readme_count(label: str) -> int:
    """Read an integer out of a README counts-table row."""
    text = README.read_text(encoding="utf-8")
    m = re.search(rf"^\|\s*{re.escape(label)}\s*\|\s*([0-9]+)", text, re.M)
    assert m, f"README has no '{label}' row in its counts table"
    return int(m.group(1))


def test_readme_counts_match_the_campus_file() -> None:
    doc = json.loads(USAR.read_text(encoding="utf-8"))
    assert _readme_count("Locations") == len(doc["locations"])
    assert _readme_count("Pathways") == len(doc["paths"])


def test_readme_provenance_counts_match_the_sources_in_the_file() -> None:
    doc = json.loads(USAR.read_text(encoding="utf-8"))
    sources = [loc["source"].split(":")[0] for loc in doc["locations"].values()]
    assert _readme_count("Coordinates from OpenStreetMap") == sources.count("osm")
    assert _readme_count("Traced from the screenshot") == sources.count("screenshot")
    assert _readme_count(
        "Described by the student (position estimated)"
    ) == sources.count("described")


def test_corrections_file_documents_every_accepted_correction() -> None:
    """Every change to the data must be written up, numbered, with no gaps.

    The README keeps two numbers apart on purpose: how many points the
    *student* corrected, and how many revisions exist in total. Correction 13
    came from a research pass, not from the student, so collapsing the two
    would overstate what the user actually asked for.
    """
    from_student = _readme_count("Corrected by the student, point by point")
    total = _readme_count("Revisions written up in total (12 from the student + 1 from research)")
    text = CORRECTIONS.read_text(encoding="utf-8")
    done = {int(n) for n in re.findall(r"^## ✅ (\d+)\.", text, re.M)}
    assert done == set(range(1, total + 1)), (
        f"README claims {total} revisions; CORRECTIONS.md documents {sorted(done)}"
    )
    assert from_student < total, "the research pass must not be counted as the student's"


def test_longest_route_in_readme_is_still_the_one_the_code_finds() -> None:
    """The quoted headline journey must survive the next correction.

    The README makes a specific numeric claim about one journey. Hard-coding
    a benchmark's headline is how a README comes to lie, so the claim is
    pinned to the graph and will fail loudly when a correction moves it.
    """
    from campus_nav import algorithms
    from campus_nav.graph import CampusGraph

    g = CampusGraph.load(USAR)
    bfs = algorithms.bfs_shortest_path(g, "block_a", "block_b")
    dij = algorithms.dijkstra(g, "block_a", "block_b")

    assert len(bfs.path) == len(dij.path), "the 'same hop count' claim"

    # BFS returns a hop count, so the route it chose has to be re-measured in
    # metres before the two can be compared - the same thing `compare` does.
    bfs_metres = algorithms.all_paths_cost(g, bfs.path)
    assert dij.cost < bfs_metres, "Dijkstra must walk less than BFS here"
    assert (round(bfs_metres), round(dij.cost)) == (300, 110), (
        f"README quotes 300 m vs 110 m; the graph now gives "
        f"{bfs_metres:.0f} m vs {dij.cost:.0f} m"
    )
