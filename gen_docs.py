#!/usr/bin/env python3
"""
Regenerate every artefact in docs/ from the current graph.

    python gen_docs.py
    python gen_docs.py -c campuses/my-campus.json     # any campus file

Nothing in docs/ is hand-edited: the map, the route figures, the comparison
figure and the interactive page are all projections of campus_nav.data.
The README embeds the two SVG files, so it stays in sync too.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from campus_nav import algorithms, visualize
from campus_nav.graph import CampusGraph, iter_pairs
from campus_nav.loader import CampusDataError, load_campus

DOCS = Path(__file__).parent / "docs"


def pick_disagreeing_pair(graph: CampusGraph) -> tuple[str, str]:
    """
    Choose the pair that shows the biggest gap between the fewest-hop route
    and the shortest route. Hard-coding node ids would silently break on any
    campus that does not use the sample's names - which is exactly what
    happened the first time an OSM campus was loaded.
    """
    best: tuple[float, str, str] | None = None
    for a, b in iter_pairs(graph.nodes):
        bfs = algorithms.bfs_shortest_path(graph, a, b)
        dij = algorithms.dijkstra(graph, a, b)
        if bfs.path == dij.path:
            continue
        bfs_m = sum(graph.weight(u, v) for u, v in zip(bfs.path, bfs.path[1:]))
        gain = bfs_m - dij.cost
        if best is None or gain > best[0]:
            best = (gain, a, b)
    if best is None:
        # no disagreement on this campus - fall back to the most distant pair
        nodes = graph.nodes
        far = max(iter_pairs(nodes),
                  key=lambda p: graph.coords(p[0])[0] ** 2 + graph.coords(p[0])[1] ** 2
                  + graph.coords(p[1])[0] ** 2 + graph.coords(p[1])[1] ** 2
                  - 2 * (graph.coords(p[0])[0] * graph.coords(p[1])[0]
                         + graph.coords(p[0])[1] * graph.coords(p[1])[1]))
        return far
    return best[1], best[2]


def main() -> None:
    ap = argparse.ArgumentParser(description="regenerate docs/ from a campus")
    ap.add_argument("-c", "--campus", metavar="FILE", default=None,
                    help="JSON campus file (default: the built-in sample)")
    ap.add_argument("--docs-dir", metavar="DIR", default="docs",
                    help="where to write the artefacts (default: docs/)")
    args = ap.parse_args()

    if args.campus:
        g = load_campus(args.campus)
    else:
        g = CampusGraph.default()
    print(f"campus: {g.label}")
    if g.note:
        print(f"        {g.note}")
    global DOCS
    DOCS = Path(args.docs_dir)
    if not DOCS.is_absolute():
        DOCS = Path(__file__).parent / DOCS
    DOCS.mkdir(parents=True, exist_ok=True)

    visualize.write_svg(g, DOCS / "campus-map.svg")

    start, goal = pick_disagreeing_pair(g)
    r = algorithms.dijkstra(g, start, goal)
    visualize.write_svg(
        g, DOCS / "route-shortest.svg", route=r,
        title=f"{g.name(start)} to {g.name(goal)}",
        subtitle="Dijkstra - shortest walking distance",
    )

    b = algorithms.bfs_shortest_path(g, start, goal)
    visualize.write_svg(
        g, DOCS / "route-fewest-hops.svg", route=b,
        title=f"{g.name(start)} to {g.name(goal)} - BFS route",
        subtitle="BFS - fewest pathways (the long way round)",
    )

    visualize.write_comparison_svg(
        g, DOCS / "bfs-vs-dijkstra.svg", start, goal,
        title=f"{g.name(start)} to {g.name(goal)}: why Dijkstra beats BFS",
    )

    visualize.build_html(g, DOCS / "index.html")

    for f in sorted(DOCS.iterdir()):
        print(f"  docs/{f.name:<34} {f.stat().st_size / 1024:>7.1f} KB")


if __name__ == "__main__":
    main()
