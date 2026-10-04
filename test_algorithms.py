"""
Test suite. Run with:  python -m pytest tests/ -v

The interesting tests are the cross-checks:
  * Dijkstra's answer is re-costed independently by walking the path.
  * Every Dijkstra result is compared against an exhaustive check of all
    simple paths, so "shortest" means shortest, not "looks short".
  * BFS is checked to be hop-optimal (which is NOT the same as distance
    optimal, and the suite proves the difference on a real pair).
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from campus_nav import algorithms, data  # noqa: E402
from campus_nav.algorithms import (  # noqa: E402
    NoPathError, a_star, bfs_shortest_path, dijkstra,
)
from campus_nav.graph import (  # noqa: E402
    CampusGraph, InvalidGraphError, UnknownLocationError, iter_pairs,
)

PAIRS = list(iter_pairs(data.LOCATIONS))


@pytest.fixture(scope="module")
def g() -> CampusGraph:
    return CampusGraph.default()


def recost(graph: CampusGraph, path: list[str]) -> float:
    """Independent re-costing: sum the weights along the returned path."""
    return sum(graph.weight(a, b) for a, b in zip(path, path[1:]))


def brute_force_shortest(graph: CampusGraph, start: str, goal: str) -> float:
    """
    Exhaustive reference: enumerate every simple path (DFS, no repeats) and
    take the minimum cost. Exponential in general, but this campus has 14
    nodes and 26 edges, so it is instant - and it is a genuinely
    independent answer for Dijkstra to be checked against.
    """
    best = float("inf")

    def walk(node: str, cost: float, seen: set[str]) -> None:
        nonlocal best
        if cost >= best:
            return                                   # prune
        if node == goal:
            best = cost
            return
        for nxt, w in graph.neighbours(node):
            if nxt not in seen:
                walk(nxt, cost + w, seen | {nxt})

    walk(start, 0.0, {start})
    return best


# --------------------------------------------------------------------------
# graph construction
# --------------------------------------------------------------------------
def test_graph_shape(g: CampusGraph) -> None:
    assert g.num_nodes == 14
    assert g.num_edges == 26
    assert len(g.nodes) == len(set(g.nodes)), "duplicate location ids"
    assert g.is_connected(), "campus graph must be fully connected"


def test_adjacency_is_symmetric(g: CampusGraph) -> None:
    """Every pathway must appear in both directions with the same weight."""
    for a in g:
        for b, w in g.neighbours(a):
            assert (a, w) in g.neighbours(b), f"{a}-{b} is one-way"


def test_weights_are_positive(g: CampusGraph) -> None:
    assert all(e.weight > 0 for e in g.edges)


def test_overrides_are_not_shorter_than_the_straight_line(g: CampusGraph) -> None:
    """
    The A* heuristic uses straight-line distance. That is only admissible if
    no edge is shorter than the straight line between its endpoints.
    """
    from campus_nav.graph import haversine_free_euclidean

    for e in g.edges:
        straight = haversine_free_euclidean(g, e.a, e.b)
        assert e.weight >= straight * 0.9, (
            f"edge {e.a}-{e.b} is {e.weight} m but the map says the two "
            f"points are {straight:.0f} m apart - the heuristic would be "
            f"inadmissible"
        )


def test_unknown_location_raises_with_a_hint(g: CampusGraph) -> None:
    with pytest.raises(UnknownLocationError) as exc:
        g.neighbours("libary")            # typo on purpose
    assert "did you mean" in str(exc.value).lower()


def test_bad_graph_construction_is_rejected() -> None:
    g = CampusGraph()
    g.add_node("a")
    g.add_node("b")
    g.add_edge("a", "b", 10)

    with pytest.raises(InvalidGraphError):
        g.add_edge("a", "b", 10)          # duplicate pathway
    with pytest.raises(InvalidGraphError):
        g.add_edge("a", "a", 10)          # self-loop
    with pytest.raises(InvalidGraphError):
        g.add_edge("a", "b", 0)           # non-positive weight
    with pytest.raises(UnknownLocationError):
        g.add_edge("a", "nowhere", 10)    # dangling reference


# --------------------------------------------------------------------------
# BFS
# --------------------------------------------------------------------------
def test_bfs_is_hop_optimal(g: CampusGraph) -> None:
    for a, b in PAIRS:
        r = bfs_shortest_path(g, a, b)
        assert r.path[0] == a and r.path[-1] == b
        assert r.cost == r.hops == len(r.path) - 1
        # every consecutive pair must be a real pathway
        for u, v in zip(r.path, r.path[1:]):
            g.weight(u, v)  # raises if not adjacent


def test_bfs_beats_dijkstra_on_hops_somewhere(g: CampusGraph) -> None:
    """BFS's whole reason to exist: on sports->library it walks ONE pathway."""
    bfs = bfs_shortest_path(g, "sports", "library")
    dij = dijkstra(g, "sports", "library")
    assert bfs.hops < dij.hops
    assert bfs.cost < dij.cost, "here BFS's hop count is also fewer metres"


# --------------------------------------------------------------------------
# Dijkstra
# --------------------------------------------------------------------------
def test_dijkstra_matches_brute_force_on_every_pair(g: CampusGraph) -> None:
    for a, b in PAIRS:
        if a == b:
            continue
        got = dijkstra(g, a, b)
        want = brute_force_shortest(g, a, b)
        assert got.cost == want, (
            f"{a}->{b}: Dijkstra said {got.cost}, brute force said {want}"
        )


def test_dijkstra_cost_matches_the_path_it_returned(g: CampusGraph) -> None:
    for a, b in PAIRS:
        if a == b:
            continue
        r = dijkstra(g, a, b)
        assert recost(g, r.path) == r.cost


def test_dijkstra_is_symmetric(g: CampusGraph) -> None:
    """An undirected graph must give the same distance in both directions."""
    for a, b in PAIRS:
        if a == b:
            continue
        assert dijkstra(g, a, b).cost == dijkstra(g, b, a).cost


def test_dijkstra_avoids_the_long_service_road(g: CampusGraph) -> None:
    """
    sports->library is 420 m along the perimeter road (1 hop) but 270 m
    through Block A / USAR. Dijkstra must pick the 270 m route.
    """
    r = dijkstra(g, "sports", "library")
    assert r.cost == 270
    assert r.hops == 3


# --------------------------------------------------------------------------
# A*
# --------------------------------------------------------------------------
def test_astar_returns_the_same_cost_as_dijkstra(g: CampusGraph) -> None:
    for a, b in PAIRS:
        if a == b:
            continue
        assert a_star(g, a, b).cost == dijkstra(g, a, b).cost, (
            f"A* disagrees with Dijkstra on {a}->{b} - the heuristic is "
            f"probably inadmissible"
        )


def test_astar_expands_no_more_than_dijkstra_on_average(g: CampusGraph) -> None:
    pairs = [(a, b) for a, b in PAIRS if a != b]
    ast = sum(a_star(g, a, b).expanded for a, b in pairs)
    dij = sum(dijkstra(g, a, b).expanded for a, b in pairs)
    assert ast <= dij, f"A* expanded {ast} nodes, Dijkstra {dij}"


def test_astar_beats_dijkstra_on_at_least_one_pair(g: CampusGraph) -> None:
    pairs = [(a, b) for a, b in PAIRS if a != b]
    better = [p for p in pairs if a_star(g, *p).expanded < dijkstra(g, *p).expanded]
    assert better, "the heuristic never helped - it is not doing any work"


# --------------------------------------------------------------------------
# error handling
# --------------------------------------------------------------------------
def test_same_start_and_goal(g: CampusGraph) -> None:
    r = dijkstra(g, "library", "library")
    assert r.path == ["library"] and r.cost == 0


def test_disconnected_start_reports_no_path() -> None:
    g = CampusGraph()
    g.add_node("a")
    g.add_node("b")
    g.add_node("island")
    g.add_edge("a", "b", 5)
    with pytest.raises(NoPathError):
        dijkstra(g, "a", "island")
    with pytest.raises(NoPathError):
        bfs_shortest_path(g, "a", "island")
    with pytest.raises(NoPathError):
        a_star(g, "a", "island")


def test_bad_algorithm_name_is_rejected(g: CampusGraph) -> None:
    with pytest.raises(ValueError) as exc:
        algorithms.solve(g, "science", "library", "floyd-warshall")
    assert "unknown algorithm" in str(exc.value)


def test_solve_dispatches_by_name(g: CampusGraph) -> None:
    assert algorithms.solve(g, "science", "library", "BFS").algorithm == "BFS"
    assert algorithms.solve(g, "science", "library", "dijkstra").algorithm == "Dijkstra"
    assert algorithms.solve(g, "science", "library", "a*").algorithm == "A*"
