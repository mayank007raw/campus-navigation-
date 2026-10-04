#!/usr/bin/env python3
"""
Benchmarks - the experimental evidence behind DECISIONS.md.

Three experiments:

  1. all-pairs search effort   BFS vs Dijkstra vs A* over all 91 pairs
  2. scaling                   synthetic grid campuses of growing size,
                               to check the shape of the growth curve
  3. hop-optimal vs distance-optimal
                               how often "fewest turns" is not "least metres"

Run:  python bench.py
"""

from __future__ import annotations

import argparse
import statistics
import time
from contextlib import contextmanager

from campus_nav import algorithms, data
from campus_nav.graph import CampusGraph, iter_pairs


@contextmanager
def timer():
    t0 = time.perf_counter()
    box = {"t": 0.0}
    try:
        yield box
    finally:
        box["t"] = time.perf_counter() - t0


def pair_key(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a <= b else (b, a)


def experiment_1(graph: CampusGraph) -> None:
    print("\n" + "=" * 74)
    print("EXPERIMENT 1 - search effort over all origin/destination pairs")
    print("=" * 74)
    pairs = [(a, b) for a, b in iter_pairs(graph.nodes)]
    print(f"pairs tested: {len(pairs)}   "
          f"(V={graph.num_nodes}, E={graph.num_edges}, undirected)\n")

    stats: dict[str, dict[str, float]] = {}
    for name, fn in (("BFS", algorithms.bfs_shortest_path),
                     ("Dijkstra", algorithms.dijkstra),
                     ("A*", algorithms.a_star)):
        expanded, touched, elapsed = [], [], []
        for a, b in pairs:
            with timer() as t:
                r = fn(graph, a, b)
            expanded.append(r.expanded)
            touched.append(len(r.visited))
            elapsed.append(t["t"])
        stats[name] = {
            "exp": statistics.mean(expanded),
            "max": max(expanded),
            "ms": statistics.mean(elapsed) * 1000,
            "total_ms": sum(elapsed) * 1000,
        }

    head = f"{'algorithm':<12}{'avg expanded':>14}{'max expanded':>14}{'avg ms':>11}"
    print(head + "\n" + "-" * len(head))
    for name, s in stats.items():
        print(f"{name:<12}{s['exp']:>14.2f}{s['max']:>14.0f}{s['ms']:>11.3f}")

    dij, ast = stats["Dijkstra"]["exp"], stats["A*"]["exp"]
    print(f"\nA* expanded {dij - ast:.2f} fewer nodes per query than Dijkstra "
          f"({100 * (dij - ast) / dij:.1f}% less search) for identical answers.")

    # where the algorithms disagree on route choice
    print("\npairs where BFS and Dijkstra return different routes:")
    disagreements = 0
    for a, b in pairs:
        b_r = algorithms.bfs_shortest_path(graph, a, b)
        d_r = algorithms.dijkstra(graph, a, b)
        if b_r.path != d_r.path:
            disagreements += 1
            if disagreements <= 6:
                print(f"  {graph.name(a)} -> {graph.name(b)}")
                bfs_m = sum(graph.weight(u, v)
                            for u, v in zip(b_r.path, b_r.path[1:]))
                print(f"      BFS      {b_r.hops} hops, {bfs_m:.0f} m: "
                      f"{' -> '.join(graph.name(n) for n in b_r.path)}")
                print(f"      Dijkstra {d_r.hops} hops, {d_r.cost:.0f} m: "
                      f"{' -> '.join(graph.name(n) for n in d_r.path)}")
    print(f"  ... {disagreements} of {len(pairs)} pairs "
          f"({100 * disagreements / len(pairs):.0f}%) differ")


def _grid(k: int, weight: int = 10) -> CampusGraph:
    """k x k lattice with 4-neighbour connections and real coordinates."""
    g = CampusGraph()
    for r in range(k):
        for c in range(k):
            g.add_node(f"n{r}_{c}", x=c * weight, y=r * weight)
    for r in range(k):
        for c in range(k):
            if c + 1 < k:
                g.add_edge(f"n{r}_{c}", f"n{r}_{c + 1}", weight)
            if r + 1 < k:
                g.add_edge(f"n{r}_{c}", f"n{r + 1}_{c}", weight)
    return g


def _random_campus(n: int, seed: int, box: tuple[float, float] = (300, 350)) -> CampusGraph:
    """
    Synthetic campus that mirrors the topology of the real dataset:
    scattered buildings, each linked to its 2 nearest neighbours, plus a few
    long service roads. Kept connected on purpose.
    """
    import math
    import random

    rng = random.Random(seed)
    w, h = box
    g = CampusGraph()
    pts: list[tuple[float, float]] = []
    for i in range(n):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        pts.append((x, y))
        g.add_node(f"L{i}", x=x, y=y)

    def dist(i: int, j: int) -> float:
        return math.dist(pts[i], pts[j])

    def metres(i: int, j: int) -> int:
        return max(5, int(round(dist(i, j) / 5) * 5))

    # 2 nearest neighbours each (union -> a few hundred edges, like a campus)
    for i in range(n):
        for j in sorted((j for j in range(n) if j != i), key=lambda j: dist(i, j))[:2]:
            if not any(nb == f"L{j}" for nb, _ in g.adjacency[f"L{i}"]):
                g.add_edge(f"L{i}", f"L{j}", metres(i, j))
    # a handful of long service roads
    for _ in range(max(2, n // 8)):
        i, j = rng.randrange(n), rng.randrange(n)
        if i != j and not any(nb == f"L{j}" for nb, _ in g.adjacency[f"L{i}"]):
            g.add_edge(f"L{i}", f"L{j}", int(metres(i, j) * 1.6))

    # stitch any remaining components together so Dijkstra never hits "unreachable"
    while not g.is_connected():
        seen, queue = {g.nodes[0]}, [g.nodes[0]]
        while queue:
            for nb, _ in g.neighbours(queue.pop()):
                if nb not in seen:
                    seen.add(nb)
                    queue.append(nb)
        outside = [x for x in g.nodes if x not in seen]
        # `next(iter(seen))` looked fine but was not: `seen` is a set of
        # strings, and Python randomises string hashing per process, so the
        # stitch edge joined a different node on every run. That made this
        # whole experiment - and every number the README quotes from it -
        # unreproducible. Pick deterministically instead.
        a, b = min(seen), outside[0]
        i, j = int(a[1:]), int(b[1:])
        g.add_edge(a, b, metres(i, j))
    return g


def experiment_2() -> None:
    """How BFS / Dijkstra / A* scale as the graph grows."""
    print("\n" + "=" * 74)
    print("EXPERIMENT 2 - scaling: 40-node random campus -> 900-node grid")
    print("=" * 74)

    print("\n2a. Random campus graphs (scattered buildings, 2 nearest "
          "neighbours each)")
    print("    Corner-ish pair: the two nodes furthest apart. "
          "Percentages are of V.\n")
    head = (f"{'V':>6}{'E':>7}{'BFS exp':>12}{'Dijkstra exp':>15}"
            f"{'A* exp':>12}{'A* vs Dij':>12}")
    print(head + "\n" + "-" * len(head))

    for n in (40, 80, 160, 320, 640):
        g = _random_campus(n, seed=7)
        nodes = g.nodes
        start, goal = min(nodes, key=lambda k: g.coords(k)[0] + g.coords(k)[1]), \
                      max(nodes, key=lambda k: g.coords(k)[0] + g.coords(k)[1])
        if start == goal:
            goal = nodes[-1]
        b = algorithms.bfs_shortest_path(g, start, goal)
        d = algorithms.dijkstra(g, start, goal)
        s = algorithms.a_star(g, start, goal)
        assert d.cost == s.cost, f"A* and Dijkstra disagree at n={n}"
        saved = 100 * (d.expanded - s.expanded) / d.expanded
        print(f"{g.num_nodes:>6}{g.num_edges:>7}"
              f"{b.expanded:>7} ({100 * b.expanded / g.num_nodes:>3.0f}%)"
              f"{d.expanded:>8} ({100 * d.expanded / g.num_nodes:>3.0f}%)"
              f"{s.expanded:>7} ({100 * s.expanded / g.num_nodes:>3.0f}%)"
              f"{saved:>10.0f}%")

    print("\n2b. Uniform k x k grid, corner to opposite corner")
    print("    Every edge costs the same, so this is BFS's best case. Note that")
    print("    Euclidean distance is a WEAK heuristic on a 4-connected grid")
    print("    (Manhattan distance would be exact), so A* prunes little here.\n")
    head = (f"{'V':>6}{'E':>7}{'BFS exp':>12}{'Dijkstra exp':>15}"
            f"{'A* exp':>12}{'A* vs Dij':>12}")
    print(head + "\n" + "-" * len(head))
    for k in (10, 20, 30):
        g = _grid(k)
        start, goal = "n0_0", f"n{k - 1}_{k - 1}"
        b = algorithms.bfs_shortest_path(g, start, goal)
        d = algorithms.dijkstra(g, start, goal)
        s = algorithms.a_star(g, start, goal)
        assert d.cost == s.cost
        saved = 100 * (d.expanded - s.expanded) / d.expanded
        print(f"{g.num_nodes:>6}{g.num_edges:>7}"
              f"{b.expanded:>7} ({100 * b.expanded / g.num_nodes:>3.0f}%)"
              f"{d.expanded:>8} ({100 * d.expanded / g.num_nodes:>3.0f}%)"
              f"{s.expanded:>7} ({100 * s.expanded / g.num_nodes:>3.0f}%)"
              f"{saved:>10.0f}%")


def experiment_3(graph: CampusGraph) -> None:
    """Is the fewest-hop route ever the shortest route?"""
    print("\n" + "=" * 74)
    print("EXPERIMENT 3 - hop-optimal vs distance-optimal")
    print("=" * 74)
    worst = None
    worse = same = 0
    rows = []
    for a, b in iter_pairs(graph.nodes):
        b_r = algorithms.bfs_shortest_path(graph, a, b)
        d_r = algorithms.dijkstra(graph, a, b)
        bfs_metres = sum(graph.weight(u, v) for u, v in zip(b_r.path, b_r.path[1:]))
        extra = bfs_metres - d_r.cost
        rows.append((extra, a, b, bfs_metres, d_r.cost))
        if extra > 0:
            worse += 1
            if worst is None or extra > worst[0]:
                worst = (extra, a, b, bfs_metres, d_r.cost)
        else:
            same += 1

    print(f"pairs where the fewest-hop route is also the shortest: {same}")
    print(f"pairs where the fewest-hop route walks further:          {worse}")
    if worst:
        extra, a, b, bm, dm = worst
        print(f"\nworst case: {graph.name(a)} -> {graph.name(b)}")
        print(f"  fewest hops : {bm:.0f} m")
        print(f"  shortest    : {dm:.0f} m  ({extra:.0f} m / "
              f"{100 * extra / dm:.0f}% less)")
    print("\nconclusion: on a weighted campus graph, minimising turns and")
    print("minimising metres are different objectives. Dijkstra is the")
    print("correct algorithm for walking distance; BFS is used for the")
    print("unweighted comparison the task asks for.")


def print_dataset(graph: CampusGraph) -> None:
    print("=" * 74)
    print("CAMPUS DATASET")
    print("=" * 74)
    print(f"{graph.label}")
    if graph.note:
        print(f"{graph.note}")
    print()
    print(f"{graph.num_nodes} locations, {graph.num_edges} pathways\n")
    print(f"{'edge':<26}{'weight':>8}  {'kind':<9}derived?")
    print("-" * 74)
    from campus_nav import geo
    for e in graph.edges:
        derived = geo.derive_weight(*graph.coords(e.a), *graph.coords(e.b))
        tag = "map distance" if derived == e.weight else f"override (map {derived} m)"
        why = graph.annotations.get(frozenset({e.a, e.b}))
        if why:
            tag += f" - {why}"
        print(f"{graph.name(e.a) + ' - ' + graph.name(e.b):<40}"
              f"{e.weight:>7}  {e.kind:<9}{tag}")


def main() -> None:
    ap = argparse.ArgumentParser(description="benchmarks and dataset dump")
    ap.add_argument("--only", choices=["1", "2", "3", "data"], default=None)
    ap.add_argument("-c", "--campus", metavar="FILE", default=None,
                    help="JSON campus file (default: the built-in sample)")
    args = ap.parse_args()

    graph = CampusGraph.load(args.campus) if args.campus else CampusGraph.default()
    print(f"campus: {graph.label}")
    if args.only in (None, "data"):
        print_dataset(graph)
    if args.only in (None, "1"):
        experiment_1(graph)
    if args.only in (None, "2"):
        experiment_2()
    if args.only in (None, "3"):
        experiment_3(graph)
    print()


if __name__ == "__main__":
    main()
