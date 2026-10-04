"""
Three shortest-path algorithms over the campus graph.

All three return the same `Route` object, so they are interchangeable and can
be compared directly. Every algorithm also reports how many nodes it
*expanded*, which is the honest way to compare search effort: it is what the
benchmarks in `bench.py` measure.

BFS       - fewest pathways (hops). Correct only when every edge costs the
            same, which on this campus it does not.
Dijkstra  - minimum total walking distance. Handles the weighted graph.
A*        - Dijkstra guided by straight-line distance to the goal. Same
            answer as Dijkstra, usually fewer expansions.
"""

from __future__ import annotations

import heapq
from collections import deque
from dataclasses import dataclass
from typing import Callable, Iterator

from .graph import CampusGraph, UnknownLocationError

INF = float("inf")


class NoPathError(RuntimeError):
    """Raised when the destination cannot be reached from the start."""


@dataclass(frozen=True)
class Route:
    """The result of a shortest-path search."""

    path: list[str]          # [start, ..., goal]
    cost: float              # total weight: metres for Dijkstra/A*, hops for BFS
    algorithm: str
    expanded: int            # nodes popped off the frontier
    visited: list[str]       # everything the search touched, in visit order

    @property
    def hops(self) -> int:
        """Number of pathways walked (edges), i.e. len(path) - 1."""
        return max(0, len(self.path) - 1)

    def describe(self, graph: CampusGraph) -> str:
        if self.path:
            seen = "  ->  ".join(graph.name(n) for n in self.path)
        else:
            seen = "(no route)"
        unit = "pathways" if self.algorithm == "BFS" else "m"
        return f"{seen}\n  {self.hops} hops, {self.cost:g} {unit}"


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _check_endpoints(graph: CampusGraph, start: str, goal: str) -> None:
    for node in (start, goal):
        if node not in graph.adjacency:
            raise UnknownLocationError(graph._did_you_mean(node))


def _empty_route(
    graph: CampusGraph,
    start: str,
    goal: str,
    algorithm: str,
    visited: list[str],
    expanded: int,
) -> Route:
    raise NoPathError(
        f"no route from {graph.name(start)!r} to {graph.name(goal)!r} "
        f"({algorithm} expanded {expanded} nodes)"
    )


def _rebuild(parent: dict[str, str | None], start: str, goal: str) -> list[str]:
    """Walk the parent chain backwards and reverse it. O(len(path))."""
    path = [goal]
    while path[-1] != start:
        prev = parent[path[-1]]
        if prev is None:  # pragma: no cover - guarded by callers
            raise NoPathError("parent chain is broken")
        path.append(prev)
    path.reverse()
    return path


def _path_cost(graph: CampusGraph, path: list[str]) -> float:
    """Independent re-costing of a path, used by the tests as a cross-check."""
    return sum(graph.weight(a, b) for a, b in zip(path, path[1:]))


# --------------------------------------------------------------------------
# BFS - unweighted (fewest hops)
# --------------------------------------------------------------------------
def bfs_shortest_path(graph: CampusGraph, start: str, goal: str) -> Route:
    """
    Breadth-first search. Treats every pathway as cost 1, so it minimises the
    NUMBER OF PATHWAYS, not the metres walked.

    Complexity: time O(V + E), space O(V) for the queue and visited set.
    """
    _check_endpoints(graph, start, goal)

    frontier: deque[str] = deque([start])
    parent: dict[str, str | None] = {start: None}
    distance = {start: 0}          # in hops
    visited: list[str] = []
    expanded = 0

    while frontier:
        node = frontier.popleft()
        expanded += 1
        visited.append(node)

        if node == goal:
            path = _rebuild(parent, start, goal)
            return Route(path, float(distance[goal]), "BFS", expanded, visited)

        # A node is marked visited on ENQUEUE (not on dequeue). With an
        # unweighted graph the first time we reach a node is already the
        # shortest, so we never need to revisit it.
        for nxt, _w in graph.neighbours(node):
            if nxt not in parent:
                parent[nxt] = node
                distance[nxt] = distance[node] + 1
                frontier.append(nxt)

    return _empty_route(graph, start, goal, "BFS", visited, expanded)


# --------------------------------------------------------------------------
# Dijkstra - weighted, non-negative
# --------------------------------------------------------------------------
def dijkstra(graph: CampusGraph, start: str, goal: str) -> Route:
    """
    Dijkstra with a binary heap. Minimises total walked distance.

    Complexity: time O((V + E) log V), space O(V).
    A dense O(V^2) variant is deliberately NOT used - see DECISIONS.md #3.
    """
    _check_endpoints(graph, start, goal)

    best = {start: 0.0}
    parent: dict[str, str | None] = {start: None}
    settled: set[str] = set()
    heap: list[tuple[float, str]] = [(0.0, start)]
    visited: list[str] = []
    expanded = 0

    while heap:
        dist_u, u = heapq.heappop(heap)

        if u in settled:
            # Lazy deletion: we push an improved entry instead of doing a
            # decrease-key, so stale entries are skipped here.
            continue
        settled.add(u)
        expanded += 1
        visited.append(u)

        if u == goal:
            return Route(_rebuild(parent, start, goal), dist_u, "Dijkstra", expanded, visited)

        for v, w in graph.neighbours(u):
            if v in settled:
                continue
            candidate = dist_u + w
            if candidate < best.get(v, INF):
                best[v] = candidate
                parent[v] = u
                heapq.heappush(heap, (candidate, v))

    return _empty_route(graph, start, goal, "Dijkstra", visited, expanded)


# --------------------------------------------------------------------------
# A* - Dijkstra + heuristic
# --------------------------------------------------------------------------
# Straight-line distance is a lower bound on walking distance, so it is an
# admissible heuristic. It is scaled slightly (see DECISIONS.md #4) because
# pathway lengths are rounded to the nearest 5 m.
HEURISTIC_SCALE = 0.95


def straight_line(graph: CampusGraph, goal: str) -> Callable[[str], float]:
    """Return h(n) = scaled euclidean distance from n to `goal`."""
    gx, gy = graph.coords(goal)

    def h(node: str) -> float:
        nx, ny = graph.coords(node)
        return HEURISTIC_SCALE * ((nx - gx) ** 2 + (ny - gy) ** 2) ** 0.5

    return h


def a_star(graph: CampusGraph, start: str, goal: str) -> Route:
    """
    A* with the straight-line heuristic. Returns the same optimal route as
    Dijkstra but typically expands fewer nodes.

    Complexity: O((V + E) log V) worst case; in practice far fewer
    expansions because the heuristic prunes nodes heading away from the goal.
    """
    _check_endpoints(graph, start, goal)

    h = straight_line(graph, goal)
    best = {start: 0.0}
    parent: dict[str, str | None] = {start: None}
    settled: set[str] = set()
    heap: list[tuple[float, float, str]] = [(h(start), 0.0, start)]
    visited: list[str] = []
    expanded = 0

    while heap:
        _f, dist_u, u = heapq.heappop(heap)

        if u in settled:
            continue
        settled.add(u)
        expanded += 1
        visited.append(u)

        if u == goal:
            return Route(_rebuild(parent, start, goal), dist_u, "A*", expanded, visited)

        for v, w in graph.neighbours(u):
            if v in settled:
                continue
            candidate = dist_u + w
            if candidate < best.get(v, INF):
                best[v] = candidate
                parent[v] = u
                # Tie-break on the node id so results are deterministic.
                heapq.heappush(heap, (candidate + h(v), candidate, v))

    return _empty_route(graph, start, goal, "A*", visited, expanded)


ALGORITHMS: dict[str, Callable[[CampusGraph, str, str], Route]] = {
    "bfs": bfs_shortest_path,
    "dijkstra": dijkstra,
    "astar": a_star,
    "a*": a_star,
}


def solve(graph: CampusGraph, start: str, goal: str, algorithm: str = "dijkstra") -> Route:
    """Dispatch by name. Raises ValueError for an unknown algorithm."""
    try:
        fn = ALGORITHMS[algorithm.strip().lower()]
    except KeyError:
        valid = ", ".join(sorted({"bfs", "dijkstra", "astar"}))
        raise ValueError(f"unknown algorithm {algorithm!r}. Choose from: {valid}") from None
    return fn(graph, start, goal)


def all_paths_cost(graph: CampusGraph, path: list[str]) -> float:  # pragma: no cover
    return _path_cost(graph, path)
