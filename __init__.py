"""
Campus Navigation System
=========================

Shortest routes between locations on a small campus graph.

    from campus_nav.graph import CampusGraph
    from campus_nav import algorithms

    g = CampusGraph.default()
    r = algorithms.dijkstra(g, "main_gate", "library")
    print(r.path, r.cost)

Modules
-------
data         the campus itself: locations, pathways, coordinates
graph        adjacency-list representation + validation
algorithms   BFS, Dijkstra, A*
visualize    static SVG map + interactive HTML demo
cli          the command-line interface
"""

__version__ = "1.0.0"

from .graph import CampusGraph, Edge, UnknownLocationError  # noqa: F401
from .algorithms import Route, bfs_shortest_path, dijkstra, a_star, solve  # noqa: F401

__all__ = [
    "CampusGraph",
    "Edge",
    "UnknownLocationError",
    "Route",
    "bfs_shortest_path",
    "dijkstra",
    "a_star",
    "solve",
    "__version__",
]
