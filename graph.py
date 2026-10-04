"""
Graph representation for the campus.

Data structure choice (see DECISIONS.md #1): an ADJACENCY LIST built on a
dict of lists, not an adjacency matrix.

    adjacency : dict[str, list[tuple[str, int]]]

Why: the campus graph is sparse. With V = 14 locations and E = 26 pathways
a matrix would store 14*14 = 196 cells of which only 2*26 = 52 are used
(~73% wasted), and every "who are my neighbours?" query would cost O(V).
The adjacency list stores exactly 2E = 52 directed entries, iterates
neighbours in O(deg(v)), and total memory is O(V + E).

Nodes are strings (building ids) rather than integer indices. That costs a
few bytes and a dict lookup, but it removes an entire class of bugs: the
mapping from a human-readable place to an index is never written by hand.
"""

from __future__ import annotations

import difflib
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator

from . import data


class UnknownLocationError(KeyError):
    """Raised when a location id is not part of the campus."""


class InvalidGraphError(ValueError):
    """Raised when the graph itself is malformed."""


@dataclass(frozen=True)
class Edge:
    """One undirected pathway between two locations."""

    a: str
    b: str
    weight: int          # metres
    kind: str = "walkway"

    @property
    def endpoints(self) -> frozenset[str]:
        return frozenset({self.a, self.b})


@dataclass
class CampusGraph:
    """An undirected, non-negatively weighted graph of campus locations."""

    adjacency: dict[str, list[tuple[str, int]]] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    #: Where this campus came from. Every figure prints it, so a synthetic
    #: example can never be mistaken for a surveyed one.
    label: str = "Campus"
    note: str = ""
    #: pathway -> free-text reason for a hand-set weight
    annotations: dict[frozenset[str], str] = field(default_factory=dict)
    _coords: dict[str, tuple[float, float]] = field(default_factory=dict)
    _names: dict[str, str] = field(default_factory=dict)
    _categories: dict[str, str] = field(default_factory=dict)

    # ---------------------------------------------------------------- build
    @classmethod
    def default(cls) -> "CampusGraph":
        """
        The built-in dataset - a SYNTHETIC sample campus, not a real one.

        It is a demonstration graph: its only job is to be small enough to
        verify by hand and connected enough to show BFS and Dijkstra
        disagreeing. For a real campus, load a file:

            CampusGraph.load("campuses/usar-campus.json")
        """
        g = cls(label=data.CAMPUS_LABEL, note=data.CAMPUS_NOTE)
        for node, (name, cat, x, y) in data.LOCATIONS.items():
            g.add_node(node, name=name, category=cat, x=x, y=y)
        for a, b, w, kind in data.edges():
            g.add_edge(a, b, w, kind)
        for edge, why in data.WEIGHT_NOTES.items():
            g.annotations[edge] = why
        g.validate()
        return g

    @classmethod
    def load(cls, path: str | Path) -> "CampusGraph":
        """Load a campus from a JSON file. See campus_nav/loader.py."""
        from .loader import load_campus          # local import: no cycle
        return load_campus(path)

    def add_node(
        self,
        node: str,
        *,
        name: str | None = None,
        category: str = "academic",
        x: float = 0.0,
        y: float = 0.0,
    ) -> None:
        if node in self.adjacency:
            raise InvalidGraphError(f"duplicate location {node!r}")
        self.adjacency[node] = []
        self._coords[node] = (float(x), float(y))
        self._names[node] = name or node.replace("_", " ").title()
        self._categories[node] = category

    def add_edge(self, a: str, b: str, weight: int, kind: str = "walkway") -> None:
        for endpoint in (a, b):
            if endpoint not in self.adjacency:
                raise UnknownLocationError(
                    f"pathway references unknown location {endpoint!r}"
                )
        if a == b:
            raise InvalidGraphError(f"self-loop at {a!r} is not a pathway")
        if weight <= 0:
            # Negative weights would break Dijkstra, so they are rejected at
            # the boundary instead of silently producing wrong routes.
            raise InvalidGraphError(f"non-positive weight {weight} on {a}-{b}")
        if any(nxt == b for nxt, _ in self.adjacency[a]):
            raise InvalidGraphError(f"duplicate pathway {a}-{b}")
        self.adjacency[a].append((b, weight))
        self.adjacency[b].append((a, weight))
        self.edges.append(Edge(a, b, weight, kind))

    # --------------------------------------------------------------- access
    @property
    def nodes(self) -> list[str]:
        return list(self.adjacency)

    @property
    def num_nodes(self) -> int:
        return len(self.adjacency)

    @property
    def num_edges(self) -> int:
        return len(self.edges)

    def neighbours(self, node: str) -> list[tuple[str, int]]:
        """(neighbour, weight) pairs. O(1) lookup, O(deg v) iteration."""
        try:
            return self.adjacency[node]
        except KeyError:
            raise UnknownLocationError(self._did_you_mean(node)) from None

    def degree(self, node: str) -> int:
        return len(self.neighbours(node))

    def weight(self, a: str, b: str) -> int:
        for nxt, w in self.neighbours(a):
            if nxt == b:
                return w
        raise UnknownLocationError(f"{a!r} and {b!r} are not directly connected")

    def name(self, node: str) -> str:
        return self._names.get(node, node)

    def kind(self, node: str) -> str:
        return self._categories.get(node, "academic")

    def coords(self, node: str) -> tuple[float, float]:
        return self._coords.get(node, (0.0, 0.0))

    # ------------------------------------------------------------ utilities
    def _did_you_mean(self, node: str) -> str:
        close = difflib.get_close_matches(node, self.adjacency, n=3, cutoff=0.4)
        hint = f" Did you mean: {', '.join(close)}?" if close else ""
        return f"unknown location {node!r}.{hint}"

    def is_connected(self) -> bool:
        """True if every location is reachable from every other one (BFS)."""
        if not self.adjacency:
            return True
        seen = {next(iter(self.adjacency))}
        queue = list(seen)
        while queue:
            node = queue.pop()
            for nxt, _ in self.neighbours(node):
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        return len(seen) == self.num_nodes

    def validate(self) -> None:
        """Cheap structural checks, run once at build time."""
        for a, b, w, _kind in (
            (e.a, e.b, e.weight, e.kind) for e in self.edges
        ):
            assert a in self.adjacency and b in self.adjacency
        if not self.is_connected():
            # Not a hard error - a real campus can have an isolated corner -
            # but the CLI reports it, and Dijkstra will report "unreachable".
            pass

    def __iter__(self) -> Iterator[str]:
        return iter(self.adjacency)

    def __len__(self) -> int:
        return self.num_nodes

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (f"CampusGraph({self.label!r}, V={self.num_nodes}, "
                f"E={self.num_edges})")


def haversine_free_euclidean(
    graph: CampusGraph, a: str, b: str
) -> float:
    """Straight-line distance in metres between two locations on the map."""
    ax, ay = graph.coords(a)
    bx, by = graph.coords(b)
    return math.hypot(ax - bx, ay - by)


def iter_pairs(nodes: Iterable[str]) -> Iterator[tuple[str, str]]:
    """Every unordered pair of distinct nodes - used by the benchmarks."""
    items = list(nodes)
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            yield a, b
