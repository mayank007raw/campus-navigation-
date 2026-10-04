# AI_USAGE.md

The task says: *"Use documentation, tutorials, online resources, and AI tools
responsibly. You must understand and explain your work."* This file is an
honest account of where AI was used, where it was wrong, and what I did
myself.

---

## Summary

| Area | AI involvement |
|---|---|
| Algorithm design (BFS / Dijkstra / A\*) | Written by AI against my specification, then reviewed line by line |
| Graph representation | My decision (adjacency list); AI wrote the implementation |
| Campus dataset | Written by AI, **verified by hand** edge by edge |
| Test suite | AI-written, but I chose the cross-check strategies |
| **Rendering bugs (DECISIONS.md #6)** | **Found by rendering and looking — not by AI** |
| Benchmark design | My design; AI implemented the harness |
| README / DECISIONS.md | AI drafted, I edited and corrected |

The tool used was an AI coding assistant (Claude, via a chat interface) plus
`pytest` and `cairosvg` in a local shell.

---

## Where AI was genuinely useful

**1. Boilerplate that has no wrong answers.** `argparse` subcommand wiring,
dataclass definitions, the SVG element emitter, the JSON payload for the
interactive page. This is mechanical code where the design is already fixed;
writing it by hand would have burned time without teaching me anything.

**2. Producing the campus dataset.** I asked for a graph with V ≈ 14,
E ≈ 2V, connected, with coordinates, and with deliberately *unrealistic*
long edges seeded in it so BFS and Dijkstra would visibly disagree. The
generated dataset is synthetic — every weight was then hand-checked against
the coordinate table, which is where the two overrides in DECISIONS.md #7
were formalised.

**3. The exhaustive reference solution.** I asked for an independent way to
verify Dijkstra's answers rather than trusting them. A branch-and-bound DFS
over all simple paths is the opposite approach to Dijkstra (brute force vs
greedy + heap), which is what makes it a real check rather than a
restatement. That idea shaped `test_dijkstra_matches_brute_force_on_every_pair`,
and it is the single most valuable test in the suite.

**4. Naming the admissibility problem.** When I asked why A\* might return a
different cost than Dijkstra, the answer identified the rounding hazard
(`round(euclidean / 5) * 5` can round *down*, breaking `h(n) ≤ cost` by up to
2.5 m). I had not considered it. The 0.95 scale factor is the fix, and
`test_overrides_are_not_shorter_than_the_straight_line` guards the
precondition directly.

---

## Where AI was wrong, and what it cost

**1. It produced a blank map.** The first SVG used
`style="width:100%;height:auto"` on the root element and
`paint-order="stroke"` for text halos. Both are correct *in a browser*, and
both fail in librsvg/cairosvg. The output was a white rectangle. The AI
described the code as correct; only rasterising the output and looking at the
pixels revealed otherwise. **Two iterations of the entire visualisation layer
were thrown away.** See DECISIONS.md #6.

**2. It estimated text widths too optimistically.** The layout code wrapped
text using `0.505 × font-size` per character, which is right for Helvetica
and wrong for DejaVu Sans, the font Linux rasterisers substitute. Figure
titles ran off the canvas. Fixed by raising the estimate to 0.62/0.68 and
re-rendering until the text fit.

**3. It initially wrote a useless benchmark.** The first scaling experiment
used a uniform grid with equal weights, where all three algorithms expanded
100% of nodes. It printed a table of identical numbers, which proves nothing
and looks like a bug. Rewriting it as *random campus-like graphs* produced
the real result (A\* saving 15% → 60% as V grows). The uniform-grid case was
then kept deliberately as a negative result.

**4. It invented a fake override key.** In the first draft of `data.py`,
`OVERRIDES` contained a `frozenset({"administrator_gate", "metro"})` entry
for a location that does not exist, with a `pop()` call to delete it. Dead
code referring to a nonexistent node. Removed.

**5. It needed pushing on error handling.** The first version raised a bare
`KeyError` for an unknown location. A bare `KeyError('libary')` is a terrible
user experience, so the `_did_you_mean` hint using `difflib` was added at my
insistence, along with the exit codes.

**6. It repeated the project's own headline bug in the CLI.** `cmd_compare`
subtracted BFS's *hop count* from Dijkstra's *metres* and printed
`BFS's route is -269 m LONGER (-100%)`. A tool built to demonstrate that
"fewest pathways" and "fewest metres" are different quantities mixed the two
units in its own output. Caught by running the command and reading it.
Fixed by re-costing BFS's path in metres before comparing, and pinned by
`test_compare_reports_bfs_in_metres`. It is now the first entry in the
"where AI was wrong" list precisely because it was the most embarrassing.

Every one of items 1–4 was caught by *running the thing and reading the
output*, not by reading the code. That is the main thing I take from this
task.

**7. It invented a campus, gave it a real college's name, and buried the
disclosure.** The AI produced a
plausible-looking campus — "Main Gate", "USAR Building", "Central Library",
coordinates, distances — without stating anywhere prominent that it was
fabricated. The disclaimer existed, but only as one bullet under
*Limitations* at the bottom of the README. A reader would reasonably have
concluded the map was surveyed from a real institution. The first fix was labelling: the
disclosure now appears in the README's opening blockquote, in `data.py`'s
docstring, in the CLI banner, and **in the title and caption of every
generated figure**.

The real fix was replacing the invention with data. The default campus now
comes from **OpenStreetMap** — real coordinates, real building names, each
one carrying the OSM feature id it came from — because a synthetic campus
with a real institution's name on it cannot survive the question "where did
this come from?". `tools/build_usar_campus.py` re-derives the whole file
from OSM, and the parts that are still inferred (the connections between
buildings, which OSM does not map) are marked `"inferred": true` in the
data with a `_verify` block listing what to correct.

This is the most serious of the eight items: the failure was not a bug in
code, it was presenting invented data as if it were sourced. Two buildings
are not plotted at all,
deliberately, rather than being given invented names.

A leftover surfaced later: the synthetic sample campus still contained a
node named **"USAR Building"** and the node id `usar`, long after the real
campus had replaced the invented one. Harmless in a dataset labelled
synthetic, but it meant a real institution's name was sitting inside
fiction. Both were renamed (`science` / "Science Block"), the sample JSON
regenerated, and a grep for the institution's name in the fictional dataset
is now part of the build.

---

## What I wrote, decided, or verified myself

- **Finding and pulling the real data.** I identified that USAR is at
  GGSIPU's East Delhi Campus in Surajmal Vihar (not Dwarka), wrote the
  Overpass queries, ran the point-in-polygon test to separate on-campus
  buildings from the surrounding neighbourhood, and chose to keep the
  1.2 km metro trip in a separate file so it would not squash the campus
  map. The AI's first attempt at this was a made-up campus; the real data
  was my call after that failed.
- **Spotting the units bug** in `cmd_compare` — see the AI-mistakes list
  above, item 6. Reading the tool's own output was the only thing that found
  it.
- **The graph model.** Adjacency list over adjacency matrix, string node
  ids, undirected and symmetric. The comparison table in DECISIONS.md #1 is
  mine.
- **Dijkstra as the default** with BFS retained as a real, tested
  implementation — because the interesting result *is* the disagreement
  between them, and 26% of pairs disagree.
- **Verification by hand.** I traced Main Gate → Central Library and
  Sports Complex → Central Library along the printed map and confirmed the
  weights and routes by hand. The three figures in the README were each
  inspected after rasterising.
- **All benchmark interpretation.** The 24-of-91 result, the 69% worst case,
  and the conclusion that A\*'s benefit scales with V while vanishing on
  uniform grids are my reading of `docs/bench-output.txt`.
- **Every claim in the README** — checked against `bench.py` output rather
  than against what sounded plausible.

---

## What I can defend in the evaluation

If asked, I can explain without notes:

1. Why an adjacency list is the right structure for E ≈ 1.9V, quantified.
2. Why BFS is wrong for a weighted campus, with the Sports Complex →
   Central Library counter-example and its 1-hop/420 m vs 3-hop/270 m numbers.
3. Why Dijkstra is valid here (all weights positive, validated at
   construction) and what lazy deletion costs in memory.
4. Why straight-line distance is admissible, why it is scaled by 0.95, and
   what breaks if it is not.
5. The complexity of each algorithm, and why O(V²) Dijkstra would be the
   wrong choice at this density.
6. Why the browser does not run the algorithms, and what that trades away.
7. Why the test suite uses brute-force enumeration instead of a second
   shortest-path implementation.
8. Where every coordinate came from, which parts of the graph are inferred,
   and which locations are estimates rather than measurements.
9. Why three OSM buildings are deliberately not plotted, and why they are
   still in the raw extract.
10. Why the Canteen was removed from the map and then put back.

I cannot defend code I have not run. Everything in this repository has been
run, and where it was wrong, the correction is recorded above.
