"""
CLI-level tests.

The important one here is `test_compare_reports_bfs_in_metres`. The first
version of `cmd_compare` subtracted BFS's HOP COUNT from Dijkstra's METRES
and printed "BFS's route is -269 m longer". That is the exact mistake the
whole project exists to illustrate, so it now has a test that fails loudly
if the units ever get mixed again.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from campus_nav import algorithms  # noqa: E402
from campus_nav.cli import main  # noqa: E402
from campus_nav.graph import CampusGraph  # noqa: E402


@pytest.fixture(scope="module")
def g() -> CampusGraph:
    return CampusGraph.default()


def test_compare_reports_bfs_in_metres(g: CampusGraph, capsys) -> None:
    """BFS's printed cost must be its route re-measured in metres."""
    rc = main(["compare", "--from", "sports", "--to", "library"])
    out = capsys.readouterr().out
    assert rc == 0

    bfs = algorithms.bfs_shortest_path(g, "sports", "library")
    bfs_metres = sum(g.weight(u, v) for u, v in zip(bfs.path, bfs.path[1:]))
    assert bfs_metres == 420, "the 420 m service road should be the BFS route"

    assert "420m" in out, "BFS row must show 420m, not its 1-hop count"
    assert "270m" in out
    assert "150 m shorter" in out
    # the specific historical bug
    assert "LONGER (-" not in out.replace(" ", " ")
    assert "-269" not in out
    assert "saved -" not in out


def test_compare_on_an_agreeing_pair(g: CampusGraph, capsys) -> None:
    rc = main(["compare", "--from", "science", "--to", "block_c"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Both algorithms agree" in out


def test_route_prints_hops_and_cost(g: CampusGraph, capsys) -> None:
    rc = main(["route", "--from", "main_gate", "--to", "library",
               "--algo", "dijkstra"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Main Gate" in out and "Central Library" in out
    assert "hops (pathways):  3" in out
    assert "295 m" in out


def test_route_with_unknown_location_exits_nonzero(capsys) -> None:
    rc = main(["route", "--from", "libary", "--to", "science"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "unknown location" in err
    assert "library" in err, "should suggest the near match"


def test_route_with_unknown_algorithm(capsys) -> None:
    with pytest.raises(ValueError, match="unknown algorithm"):
        main(["route", "--from", "science", "--to", "library",
              "--algo", "bellman-ford"])


def test_list_shows_the_whole_graph(capsys) -> None:
    rc = main(["list"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "14 locations, 26 pathways" in out
    assert "connected: yes" in out


def test_map_writes_an_svg(tmp_path, capsys) -> None:
    out_file = tmp_path / "route.svg"
    rc = main(["map", "--from", "sports", "--to", "library",
               "--out", str(out_file)])
    assert rc == 0
    svg = out_file.read_text()
    assert svg.startswith("<svg")
    assert "<polyline" in svg, "the route should be drawn"
    # guards the two rendering bugs in DECISIONS.md #6
    assert "paint-order" not in svg, "librsvg ignores paint-order; use a halo pass"
    assert "width:100%" not in svg, "style width:100% makes librsvg render blank"
