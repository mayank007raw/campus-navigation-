"""
Command-line interface.

    python main.py list
    python main.py route --from usar --to hostel_w --algo dijkstra
    python main.py compare --from sports --to library
    python main.py map --from sports --to library --out docs/route.svg
    python main.py demo            # interactive, menu driven
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace

from . import algorithms, data, visualize
from .graph import CampusGraph, UnknownLocationError
from .loader import CampusDataError

BAR = "-" * 62


def _fmt_mins(metres: float) -> str:
    """Walking time at a lazy 1.25 m/s, rounded up to whole minutes."""
    minutes = max(1, round(metres / 1.25 / 60))
    return f"~{minutes} min walk"


def _load_graph(args: argparse.Namespace) -> CampusGraph:
    """
    Built-in sample unless the command names a campus file.

    `validate` takes its file positionally (`validate FILE`), every other
    command takes `-c/--campus FILE`. Missing the second case here made
    `validate` report "valid" for any filename at all, including files that
    did not exist - it was quietly re-checking the built-in sample.
    """
    path = getattr(args, "campus", None) or getattr(args, "file", None)
    if path:
        return CampusGraph.load(path)
    return CampusGraph.default()


def _campus_banner(graph: CampusGraph) -> None:
    print(f"  campus: {graph.label}")
    if graph.note:
        print(f"  {graph.note}")


def cmd_list(graph: CampusGraph, args: argparse.Namespace) -> int:
    _campus_banner(graph)
    print(f"  {graph.num_nodes} locations, {graph.num_edges} pathways")
    print(BAR)
    for node in sorted(graph, key=lambda n: graph.name(n)):
        x, y = graph.coords(node)
        print(f"  {node:<11} {graph.name(node):<22} "
              f"deg={graph.degree(node):<3} ({x:.0f}, {y:.0f})")
    print(BAR)
    print("connected:", "yes" if graph.is_connected() else "NO - some places are isolated")
    print("\nAlgorithms:", ", ".join(sorted({"bfs", "dijkstra", "astar"})))
    return 0


def cmd_route(graph: CampusGraph, args: argparse.Namespace) -> int:
    try:
        route = algorithms.solve(graph, args.from_, args.to, args.algorithm)
    except UnknownLocationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except algorithms.NoPathError as exc:
        print(f"no route: {exc}", file=sys.stderr)
        return 3

    unit = "pathways" if route.algorithm == "BFS" else "m"
    print()
    _campus_banner(graph)
    print(f"\n  {route.algorithm}  |  {graph.name(args.from_)} -> {graph.name(args.to)}\n")
    print("  " + BAR)
    for i, node in enumerate(route.path):
        step = "" if i == 0 else f"+{graph.weight(route.path[i - 1], node)} m  "
        marker = "  START" if i == 0 else ("  END" if i == len(route.path) - 1 else "")
        print(f"  {i}.  {step:<9} {graph.name(node)}{marker}")
    print("  " + BAR)
    print(f"  hops (pathways):  {route.hops}")
    print(f"  total cost:       {route.cost:g} {unit}")
    if route.algorithm != "BFS":
        print(f"  estimated time:   {_fmt_mins(route.cost)}")
    print(f"  nodes expanded:   {route.expanded}")
    return 0


def cmd_compare(graph: CampusGraph, args: argparse.Namespace) -> int:
    """Run all three algorithms on the same pair and show how they differ."""
    print()
    _campus_banner(graph)
    print(f"\n  {graph.name(args.from_)} -> {graph.name(args.to)}")
    print("  " + BAR)
    print(f"  {'algorithm':<10} {'cost':>8} {'hops':>6} {'expanded':>9}   route")
    print("  " + BAR)
    results = {}
    for name in ("bfs", "dijkstra", "astar"):
        r = algorithms.solve(graph, args.from_, args.to, name)
        # Re-cost BFS's route in metres. Comparing BFS's hop COUNT against
        # Dijkstra's METRES is meaningless - it is the same trap the whole
        # project is about, and it produced "-269 m longer" before this fix.
        walk = sum(graph.weight(u, v) for u, v in zip(r.path, r.path[1:]))
        r = replace(r, cost=float(walk)) if name == "bfs" else r
        results[name] = r
        names = " -> ".join(graph.name(n) for n in r.path)
        print(f"  {r.algorithm:<10} {r.cost:>6g}m {r.hops:>6} "
              f"{r.expanded:>9}   {names}")

    bfs, dij = results["bfs"], results["dijkstra"]
    print("  " + BAR)
    print(f"  (BFS's cost above is its route re-measured in metres, so the "
          f"column is comparable.)")
    if bfs.cost != dij.cost:
        extra = bfs.cost - dij.cost
        # Percentage is taken against BFS's walk, because BFS is the naive
        # baseline: "Dijkstra walks X% less than the direct-looking route".
        pct = 100 * extra / bfs.cost if bfs.cost else 0
        print(f"  Dijkstra's route is {extra:g} m shorter than BFS's "
              f"({pct:.0f}% less walking).")
        print(f"  BFS is not wrong - it is answering a different question:")
        print(f"  fewest pathways, not fewest metres.")
        if bfs.hops < dij.hops:
            print(f"  BFS used {dij.hops - bfs.hops} fewer pathways "
                  f"({bfs.hops} vs {dij.hops}) but chose a longer one.")
        elif bfs.hops == dij.hops:
            print(f"  Both routes use {bfs.hops} pathways; BFS simply picked "
                  f"longer ones.")
    else:
        print("  Both algorithms agree on this pair - the fewest-hop route is")
        print("  also the shortest route.")
    ast = results["astar"]
    print(f"  A* matched Dijkstra's cost ({ast.cost:g} m) using "
          f"{dij.expanded - ast.expanded} fewer expansions.")
    return 0


def cmd_map(graph: CampusGraph, args: argparse.Namespace) -> int:
    route = None
    title = graph.label
    subtitle = "Pathways labelled in metres"
    if args.from_ and args.to:
        route = algorithms.solve(graph, args.from_, args.to, args.algorithm)
        title = f"{graph.name(args.from_)} to {graph.name(args.to)}"
    out = visualize.write_svg(graph, args.out, route=route, title=title,
                              subtitle=subtitle)
    print(f"wrote {out}")
    if route:
        print(f"  {route.algorithm}: {route.hops} hops, {route.cost:g} m")
    return 0


def cmd_demo(graph: CampusGraph, _args: argparse.Namespace) -> int:
    """Small interactive loop - the 'choose a start and destination' flow."""
    print("\n  CAMPUS NAVIGATION SYSTEM")
    _campus_banner(graph)
    print("  " + BAR)
    for node in sorted(graph, key=lambda n: graph.name(n)):
        print(f"   {node:<11} {graph.name(node)}")
    print("  " + BAR)
    print("  Leave the destination blank to quit.\n")

    while True:
        try:
            start = input("  start       > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not start:
            return 0
        try:
            goal = input("  destination > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not goal:
            return 0
        algo = input("  algorithm [bfs/dijkstra/astar] (dijkstra) > ").strip() or "dijkstra"

        try:
            route = algorithms.solve(graph, start, goal, algo)
        except (UnknownLocationError, ValueError, algorithms.NoPathError) as exc:
            print(f"  ! {exc}\n")
            continue

        print()
        for i, node in enumerate(route.path):
            arrow = "   " if i == 0 else "-> "
            print(f"   {arrow}{graph.name(node)}")
        unit = "pathways" if route.algorithm == "BFS" else "m"
        print(f"\n   {route.hops} hops, {route.cost:g} {unit}, "
              f"{route.expanded} nodes expanded\n")


def _add_campus_flag(sub: argparse.ArgumentParser) -> None:
    sub.add_argument(
        "-c", "--campus", metavar="FILE", default=None,
        help="load the campus from a JSON file instead of the built-in "
             "synthetic sample (see campuses/MY-CAMPUS.template.json)",
    )


def cmd_validate(graph: CampusGraph, args: argparse.Namespace) -> int:
    """Loaded without raising, so report what was actually built."""
    print(f"  {args.file} is a valid campus file.")
    print(BAR)
    print(f"  label:      {graph.label}")
    if graph.note:
        print(f"  note:       {graph.note}")
    print(f"  locations:  {graph.num_nodes}")
    print(f"  pathways:   {graph.num_edges}")
    print(f"  connected:  {'yes' if graph.is_connected() else 'NO - some locations are unreachable'}")
    print("  category counts:")
    counts: dict[str, int] = {}
    for node in graph:
        counts[graph.kind(node)] = counts.get(graph.kind(node), 0) + 1
    for cat, n in sorted(counts.items()):
        print(f"      {cat:<10} {n}")
    if graph.annotations:
        print("  hand-set pathway weights:")
        for edge, why in graph.annotations.items():
            a, b = sorted(edge)
            print(f"      {graph.name(a)} - {graph.name(b)}: {why}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="campus-nav",
        description="Shortest routes between locations on a small campus graph.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="algorithms: bfs (fewest pathways), dijkstra (shortest "
               "distance), astar (dijkstra + heuristic)",
    )
    sub = p.add_subparsers(dest="command")

    l = sub.add_parser("list", help="show the locations and their degrees")
    _add_campus_flag(l)
    d = sub.add_parser("demo", help="interactive start/destination prompt")
    _add_campus_flag(d)

    r = sub.add_parser("route", help="shortest route between two locations")
    r.add_argument("--from", dest="from_", required=True, metavar="PLACE")
    r.add_argument("--to", dest="to", required=True, metavar="PLACE")
    r.add_argument("--algo", dest="algorithm", default="dijkstra")
    _add_campus_flag(r)

    c = sub.add_parser("compare", help="compare all three algorithms on one pair")
    c.add_argument("--from", dest="from_", required=True, metavar="PLACE")
    c.add_argument("--to", dest="to", required=True, metavar="PLACE")
    _add_campus_flag(c)

    m = sub.add_parser("map", help="write an SVG map (optionally with a route)")
    m.add_argument("--from", dest="from_", metavar="PLACE")
    m.add_argument("--to", dest="to", metavar="PLACE")
    m.add_argument("--algo", dest="algorithm", default="dijkstra")
    m.add_argument("--out", default="docs/campus-map.svg")
    _add_campus_flag(m)

    v = sub.add_parser("validate",
                       help="check a campus JSON file without drawing it")
    v.add_argument("file", metavar="FILE")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command is None:
        args.command = "demo"
        args.campus = None

    try:
        graph = _load_graph(args)
    except CampusDataError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    handlers = {
        "list": cmd_list,
        "route": cmd_route,
        "compare": cmd_compare,
        "map": cmd_map,
        "demo": cmd_demo,
        "validate": cmd_validate,
    }
    return handlers[args.command](graph, args)
