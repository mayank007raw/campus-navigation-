# DECISIONS.md

Every decision below is dated, states the alternative that was rejected, and
gives the evidence. The task asks for "one design change or edge case" — this
file documents all of them, because the reasoning is the point.

---

## 1. Adjacency list, not adjacency matrix

**Decision.** Represent the campus as `dict[str, list[tuple[str, int]]]` —
an adjacency list keyed by location id, where each entry is
`(neighbour, weight_in_metres)`.

**Rejected: adjacency matrix.** V = 14, E = 26. A matrix would allocate
14 × 14 = 196 cells and fill only 2 × 26 = 52 of them — **73% waste** — and
every "who are my neighbours?" query, which is the only query Dijkstra and
BFS ever make, would cost O(V) instead of O(deg v).

| Operation | Adjacency list | Matrix |
|---|---|---|
| Memory | O(V + E) → 52 directed entries | O(V²) → 196 cells |
| Neighbours of v | O(deg v) | O(V) |
| Edge (u, v)? | O(deg u) | **O(1)** |
| Iterate all edges | O(V + E) | O(V²) |

The campus is sparse: E/V ≈ 1.9. The one operation the matrix wins — a
direct edge lookup — is never on the hot path. `graph.weight(u, v)` does use
a linear scan, but it is called only for display and for the test suite's
re-costing, never inside a search loop.

**Node identity.** Nodes are strings (`usar`, `hostel_w`), not integer
indices. A string costs a dict lookup and a few bytes more, and buys the
disappearance of an entire bug class: there is no hand-written id ↔ index
table anywhere in the project that can drift out of sync.

---

## 2. Dijkstra as the default; BFS kept and tested

**Decision.** `--algo dijkstra` is the default. BFS remains a first-class
implementation with its own tests.

**Why not BFS-only.** BFS minimises *pathways*, and on a weighted campus
that is not the same as minimising *metres*. Measured on all 91 pairs:

- **24 pairs (26%)** have a fewest-hop route that walks further than the
  shortest route.
- Worst case: Sports Complex → Girls' Hostel — the fewest-hop route is
  **515 m, the shortest route is 305 m, a 210 m difference (69%)**.
- The case the README leads with: Sports Complex → Central Library is
  **1 pathway / 420 m** under BFS vs **3 pathways / 270 m** under Dijkstra.
  The direct service road behind the sports field is a trap for a
  hop-minimising algorithm.

**Why not Dijkstra-only.** Two reasons. First, the task explicitly asks for
BFS (or Dijkstra) plus an explanation of why the chosen algorithm fits — and
the only way to *show* that Dijkstra fits is to run BFS against it. Second,
BFS is still the correct algorithm for an unweighted graph, and this design
makes that boundary explicit rather than pretending it does not exist.

**Consequence.** The CLI prints the disagreement, not just the answer:
"BFS's route is 150 m LONGER (36%) than Dijkstra's, because BFS counts
pathways while Dijkstra counts metres."

---

## 3. Binary-heap Dijkstra, and why 0-1 BFS was not used

**Decision.** Dijkstra with a `heapq` binary heap and **lazy deletion**
(push a better entry instead of doing a decrease-key), giving
O((V + E) log V).

**Rejected: dense O(V²) Dijkstra.** It is faster only when E ≈ V², i.e.
when the adjacency matrix is nearly full. Here E = 26 ≪ V² = 196, so the
heap version is both faster and simpler — no matrix memory, no
"find the unvisited minimum by scanning all V nodes" loop.

**Rejected (for now): 0-1 BFS.** For a graph whose weights are only 0 or 1,
a deque gives Dijkstra's answer in O(V + E). It does not apply here: real
pathway lengths span 65 m to 420 m. The nearest true analogue would be
bucketing the weights, which is a real optimisation for a much larger graph
and is noted in "what I would do next" — but at V=14 it would add machinery
and remove no measurable work.

**Lazy deletion detail.** Stale heap entries are skipped with
`if u in settled: continue` rather than mutated in place. The heap can grow
to O(E) entries, which is a deliberate memory-for-simplicity trade: the
alternative needs an index map and a decrease-key routine, both of which are
prime bug territory, to save nothing at this scale.

---

## 4. A\* heuristic scaled by 0.95 (an admissibility fix)

**Decision.** `h(n) = 0.95 × straight_line_distance(n, goal)`.

**Why a heuristic is legitimate here.** The locations have real coordinates,
and straight-line distance can never exceed the walking distance, so it is
an admissible lower bound — A\* returns exactly Dijkstra's optimal cost.

**Why the scale factor.** Admissibility also requires `h(n) ≤ true cost` for
*every* edge. Two pathway weights are hand-set overrides (perimeter road
420 m, sports-field detour 260 m) and the rest are rounded to the nearest
5 m by `round(euclidean / 5) * 5`. Rounding **down** by up to 2.5 m can make
the map distance slightly shorter than the stored weight, which would break
the bound by a hair. Scaling by 0.95 (≈ 5% headroom, far more than the
rounding error) restores it with a negligible loss of pruning.

**Evidence it is still correct and still useful.**

- `test_astar_returns_the_same_cost_as_dijkstra` asserts A\* = Dijkstra on
  all 91 pairs.
- `test_overrides_are_not_shorter_than_the_straight_line` guards the
  admissibility precondition directly, so a future edit to `data.py` that
  adds an unrealistically short edge fails the build rather than silently
  producing wrong routes.
- A\* expanded **3.80** nodes on average vs Dijkstra's **7.91** — **52%
  less search** for identical answers.

---

## 5. The browser does not re-implement the algorithms

**Decision.** `docs/index.html` is a single self-contained file with the
Python-computed answers for all 91 pairs × 3 algorithms embedded as JSON
(~59 KB).

**Rejected: port Dijkstra to JavaScript.** It duplicates the algorithm,
which means two implementations to keep in sync, two places for a bug to
hide, and a test suite that covers only one of them. Writing a second
implementation purely to draw a map is the worst of both worlds.

**Rejected: a Flask/FastAPI server.** The task recommends 4–6 hours and a
small complete solution. A server adds a dependency, a port, a CORS story
and a deployment step, and breaks GitHub Pages hosting.

**Consequence.** The page is one static file that works offline, from a
`file://` URL, or on GitHub Pages, and the algorithms have exactly one
implementation — the one `pytest` covers. The trade-off is that the page is
fixed to the 14-location graph: edit `data.py`, and `python gen_docs.py`
regenerates it.

---

## 6. Two SVG rendering bugs that changed how the figures are drawn

Both were found by rasterising the output with `cairosvg` and *looking at
the pixels*, not by reading the SVG source. Neither would have shown up in
the browser.

### 6a. `paint-order="stroke"` does not exist outside the browser

Node labels were drawn with `stroke="#fff" stroke-width="3.5"
paint-order="stroke"` — the standard trick for a white halo behind text.
**librsvg and cairosvg ignore `paint-order`** and paint the stroke *over*
the fill, turning every white-filled glyph into a white blob. The map
rendered as an empty field of circles.

*Fix:* every label is now emitted **twice by hand** — an outline pass with
`fill="none"`, then the fill pass on top. This works in every renderer,
including GitHub's README renderer, which is where these figures are read.

### 6b. `style="width:100%;height:auto"` produces a zero-size canvas

The root `<svg>` carried `width="100%"` plus `height:auto` for responsive
layout. librsvg resolves that to a zero-height canvas and rasterises to a
blank image, so the SVGs rendered fine in a browser and were **invisible
everywhere else** — including GitHub.

*Fix:* the SVG declares only `width`/`height` attributes. Responsiveness is
the embedding page's job: `docs/index.html` sets `svg{width:100%;height:auto}`
in CSS, where neither the browser nor a rasteriser has to guess.

**Lesson recorded.** "It looks right in the browser" is not a test.
`python gen_docs.py` output is now verified by rasterising it, which is how
both bugs surfaced. A third, smaller fix came from the same loop: footer
text overflowed the canvas because the width estimate assumed Helvetica,
and word wrapping in the figures was tuned for DejaVu Sans, the font most
Linux renderers substitute.

---

## 7. Weights derived from coordinates, with two documented overrides

**Decision.** Pathway weights are computed as
`round(euclidean(a, b) / 5) * 5` metres from the map coordinates.
Two exceptions carry explicit overrides:

| Pathway | Straight line | Stored weight | Why |
|---|---|---|---|
| Sports Complex – Central Library | 245 m | **420 m** | the only real route is the perimeter service road around the sports field |
| Boys' Hostel – Block C | 135 m | **260 m** | the sports field is in the way |

**Reasoning.** Deriving weights means the drawn map and the graph can never
disagree — a mismatch between the picture and the numbers is the single most
common way a navigation demo looks wrong during evaluation. The two
overrides then become the *most interesting* edges in the graph: the 420 m
edge is what makes BFS take a route that is 150 m longer, which is the
headline result of the whole project.

**Guarded by tests.** Every stored weight must be at least 90% of its
straight-line distance (`test_overrides_are_not_shorter_than_the_straight_line`),
which is exactly the precondition A\*'s heuristic needs. An override that
made an edge *shorter* than the straight line would silently break A\*
optimality; now it fails the build instead.

---

## 8. The campus is a labelled synthetic sample, and swappable

**Decision.** The built-in campus stays synthetic, but it now says so
everywhere — in `data.py`'s module docstring, in the README's opening
blockquote, in the CLI banner, and **in the caption of every generated
figure**. A real campus is supplied as a JSON file, not by editing code.

**The provenance problem.** The GDG-USAR brief names a provided dataset for
almost every task; for DSA it does not:

| Task | Data source |
|---|---|
| AI/ML 1–4 | *"dataset provided by GDG-USAR"* / *"one document provided by GDG-USAR"* / *"guided list provided by GDG-USAR"* |
| Web/App 1, Cyber 1–2 | *"a provided or publicly available 3D model"*, *"the authorised application or security lab provided for the task"* |
| DSA 2 — Smart Search Engine | *"a fixed collection of text documents provided by GDG-USAR"* / *"Use the provided document collection"* |
| **DSA 1 — Campus Navigation System** | **"Represent locations and connections as a graph."** |

DSA 1 is the only task with no provided artefact, because the graph *is* the
work. So inventing a campus is within the brief — but a reviewer is entitled
to know which parts are invented, and the first version of this repo made
that easy to miss: the synthetic disclaimer sat in a *Limitations* bullet at
the end of the README, while the figures showed a place that looked
surveyed. That is a documentation failure regardless of the task rules.

**What changed.**

1. `data.py` opens with `*** THIS IS A MADE-UP CAMPUS. IT IS NOT A REAL
   PLACE. ***` and states outright that nothing was surveyed.
2. The label `Sample Campus (synthetic)` is the graph's own `label` field, so
   it is the *title* of every figure and the first line of every CLI run.
   It travels with the data; it is not a caption someone has to remember
   to add.
3. The footer of every figure repeats that the distances are invented.
4. `campuses/MY-CAMPUS.template.json` makes replacing the campus a
   five-minute job with no code changes.

**Why a JSON loader rather than "just edit `data.py`".** Editing the Python
literal works, but it couples the graph to the source file: you cannot keep
two campuses side by side, you cannot diff a campus change in review, and
nothing validates the result. The loader adds real checks — every endpoint
must exist, no self-loops, no duplicates, positive weights, and **no pathway
weight shorter than the straight line between its endpoints**, which is
exactly the precondition A\*'s heuristic depends on (see #4). A campus file
that would silently break optimality is rejected at load time with the
offending path named.

**Consequence.** `python gen_docs.py -c campuses/usar-campus.json` rebuilds
every figure, the interactive page and the README images for a different
campus, with the algorithms, tests and visualisation code untouched.

**Kept as evidence.** The rejected map is archived at
`docs/archive/campus-map-v1-invented.svg` with a banner explaining what it
is, and `tools/make_comparison.py` renders
`docs/compare-original-vs-real.html` — both maps side by side with a table
of what changed. Deleting the mistake would have been tidier; keeping it
makes the reasoning auditable, and it is the clearest illustration of why
provenance matters more than plausibility.

---

## 9. Real OSM data instead of an invented campus

**Decision.** The default campus is built from **OpenStreetMap** data by
`tools/build_usar_campus.py`, and every location carries the OSM feature id
it came from.

**What went wrong first.** An earlier revision shipped a campus I made up —
generic buildings, invented coordinates, invented distances — while putting a
real institution's name on it. It looked authoritative and was unverifiable.
In a viva, "where did this map come from?" has no good answer, and on a
campus the interviewer knows, the fiction is obvious within seconds.

**Why OSM specifically.** It has real coverage of the USAR East Delhi
Campus, including a `GGSIPU East Delhi Campus` landuse polygon
(`way/1186490427`), named buildings (`Academic Block` as
`building=university`, `Auditorium`, `Boys Hostel`, `Teachers' Hostel`),
`Maharaja Surajmal Park`, an `Indoor Sports complex`, and the nearest metro
station. ODbL licensing permits reuse with attribution, which the repo gives
in the README, in every figure caption and in the JSON itself.

**What is sourced vs inferred, and why that distinction is in the data.**
Coordinates, names, the campus boundary and the point-in-polygon test are
sourced. The *connections between buildings* are not: OSM maps only four
footpaths on this campus, far too few to route on. So edges are inferred
from proximity and campus structure, and **each one is marked
`"inferred": true` in the JSON** with a `_verify` block telling the reader
what to correct. Three OSM buildings that the student said are not part of
the campus map are left out of the shipped file and exported as
`Unnamed Block 1/2` with a TODO rather than being given invented names —
the failure mode this whole decision exists to prevent.

**The honest cost, and what actually fixed it.** Thin path coverage means
inferred edges are close to straight lines, and when the real campus was
first built from OSM alone, BFS and Dijkstra disagreed on only **1 of 45
pairs** — the graph was too flat to distinguish them. That number is now
**17 of 66**, and *not one of those extra disagreements came from more
data*. They came from the student correcting the map: a gate in the right
place, a library between two blocks, a canteen on the way to the sports
hall. Real structure creates real weight differences. The synthetic sample
is kept as a second dataset with a documented detour, and both benches are
checked in.

**Reproducibility.** The Overpass query is reprinted in the script's
docstring. Anyone can re-run it and diff the output, or paste a single
feature id into openstreetmap.org and see the building.

---

## 10. Provenance is a field, not a comment

**The decision.** Every location in `campuses/usar-east-campus.json` carries a
`source`, and the value names the method, not the confidence:

| `source` | Meaning | Trust |
|---|---|---|
| `osm:way/1186488777` | surveyed by OpenStreetMap | exact |
| `screenshot` + `measured_at_px` | I read it off an image; the pixel is recorded so the arithmetic is checkable | ±10 m |
| `described` | a person said where it is, in words | position is an estimate; **only the connection is sourced** |

**Why this rather than a comment in a README.** The first version of this
project shipped an entirely invented campus while the README explained, in
prose, that it was invented. That failed at the only moment that mattered:
someone looked at the map and could not tell which parts were real. A
disclaimer in a document is not read at the point of use. A field on every
row is.

The distinction the third row draws is the one that matters most. "A student
told me the canteen is at the end of Block B" is **evidence about
connectivity and weak evidence about position** — so the file records both
things separately, instead of averaging them into one number that claims
more than the source does.

**Cost.** More JSON, and a reader has to hold three trust levels in their
head. **Benefit.** An evaluator can ask "is this real?" about any single row
and get an answer without asking me, and `SOURCES.md` can list where the
sources disagree and which one wins instead of glossing it.

---

## 11. The documentation is checked by tests, because prose rots silently

**The decision.** `tests/test_docs.py` asserts that:

- the counts in the README equal the real location and pathway counts
- the README's provenance counts equal the `source` values actually in the JSON
- `CORRECTIONS.md` contains a written-up section for every correction the
  README claims, with no gaps in the numbering
- the headline journey quoted in the README still matches what the code
  returns on the current graph

**Why this is a design decision and not a chore.** Three separate times in
this project the *code* was right and the *documentation was wrong*:

1. The README quoted a headline benchmark — "Block A → Sports Hall, 575 m vs
   390 m" — after corrections 8–10 had moved or deleted every building
   involved. It was a true statement about a map that no longer existed.
2. `CORRECTIONS.md` fell three corrections behind the builder, so the
   project's central artefact — the record of what the student said — was
   incomplete at the point it was most needed.
3. The `_verify` block inside the shipped JSON, the first thing a reader
   sees, spent six corrections asking whether Block B was a complex and
   quoting a gate id that had been renamed.

Each time, my own edits had used `str.replace` with an anchor that was not
in the file. **A `str.replace` that matches nothing is a no-op, not an
error** — so the edit reported success, the tests stayed green, and the file
was quietly wrong.

**The generalisable lesson.** Documentation that is not executable is
documentation that will eventually lie, and it will lie most confidently at
the moment it is most wrong. The four assertions above are cheap; the failure
they prevent cost three corrections' worth of credibility.

**Cost.** Tests now fail when prose is stale, which means a real change
requires updating prose in the same commit. That is the point.

---

## Edge cases handled

| Case | Decision |
|---|---|
| Start = destination | returns a single-node route, cost 0, no special-casing in the search |
| Unreachable destination | `NoPathError` with the number of nodes expanded; CLI exits 3. Tested with a disconnected 3-node graph. |
| Typos (`libary`) | `difflib.get_close_matches` suggests the nearest ids rather than dumping the whole location list |
| Self-loop or duplicate pathway | refused at graph construction — a self-loop is never a valid walking route |
| Non-positive weight | refused at construction, because a negative weight silently breaks Dijkstra's correctness guarantee rather than failing loudly |
| Parallel paths between the same pair | not allowed; the second is rejected as a duplicate, so "the weight of edge (u,v)" is always well defined |
| Ties in cost | A\* breaks ties on node id, so repeated runs and the test suite are deterministic |

---

## Complexity summary

| Operation | Time | Space |
|---|---|---|
| Build graph from `data.py` | O(V + E) | O(V + E) |
| BFS (fewest pathways) | O(V + E) | O(V) |
| Dijkstra (binary heap) | O((V + E) log V) | O(V) |
| A\* | O((V + E) log V) worst case, fewer expansions in practice | O(V) |
| Connectivity check | O(V + E) | O(V) |
| Re-cost a returned path | O(hops) | O(1) |
| All-pairs, all algorithms (used by the HTML generator) | O(V² · E log V) → 273 searches, 2.7 ms measured | O(V²) |

At V=14, E=26 every operation here is microseconds. The complexity analysis
matters because it is what decides *which* structure is correct, not because
this campus is slow.
