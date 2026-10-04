# Campus Navigation System

Shortest-path navigation on a small campus graph, built for the
**GDG-USAR Tech Team 2026** selection task — **DSA / Task 1**.

Pick a start and a destination; the tool returns the route, the total walking
cost, and an explanation of why that route is right. Three algorithms
(BFS, Dijkstra, A\*) run over the same graph so the difference between them
can be *shown* rather than claimed.

The default campus is **USAR's East Delhi Campus at GGSIPU, Surajmal
Vihar**, laid out from a satellite screenshot and OpenStreetMap building
coordinates — so every point on the map can be traced to its source.

![Campus map](docs/campus-map.svg)

---

> **New to the code?** Read **[`HOW-IT-WORKS.md`](HOW-IT-WORKS.md)** first — the
> whole project in plain English, no programming background assumed, including
> what to say if you are asked to explain it.
>
> Then **[`CODE-GUIDE.md`](CODE-GUIDE.md)** — what every file does, Dijkstra
> line by line, and the code questions you are likely to be asked.

## Where the map came from

Read this before anything else, because the first version of this project got
it wrong.

**All coordinates and building names come from OpenStreetMap**, and every
location in `campuses/usar-east-campus.json` carries the OSM feature id it
came from:

| Location | Source | Notes |
|---|---|---|
| Block A (USAR) | OSM `way/1186488777` | `building=university`; named "Block A" by the student |
| Auditorium | OSM `way/1186488780` | |
| Boys Hostel | OSM `way/1186488779` | |
| Sports Hall | OSM `leisure=sports_centre` | "Indoor Sports complex" in OSM |
| Gate 1 | OSM `barrier=gate` node | unnamed in OSM; named by the student |
| Gate 2 | screenshot trace | measured at px (252, 680) |
| Library (C-Block), Block B (USDI), Canteen (D-Block), Parking, Outdoor Ground, Girls' Hostel | described by the student | position estimated; only the connections are sourced |

Three OSM buildings — Teachers' Hostel and two unnamed blocks — are
deliberately **not plotted**: the student said they are not on the campus
map. They remain in `campuses/usar-osm-raw.json`, which is the untouched
extract. Not plotting a real feature and pretending OSM never had it are
different things.

Traced coordinates are marked `"source": "screenshot"` and carry the pixel
they were read from, so the arithmetic is checkable. The scale comes from two
anchors: Google's USAR pin (which is the OSM Academic Block) and the OSM gate
node on the south road — **213 px apart in the image, 328 m apart on the
ground, so 1 px = 1.54 m**. One scale serves both axes because a north-up
web map is square.

Paste any of those ids into [openstreetmap.org](https://www.openstreetmap.org)
and the feature appears. `tools/build_usar_campus.py` re-derives the whole
file from OSM, so the coordinate→metres conversion is reproducible rather
than something you have to trust.

**What is genuinely sourced:** building names where OSM has them, coordinates
to about a metre, and which buildings fall inside the
`GGSIPU East Delhi Campus` landuse polygon (checked with a
point-in-polygon test, not by eye).

**What is inferred, and labelled as such:** which locations connect to which.
OSM maps only four footpaths on this campus — far too thin to route on — so
`campus_nav/data`-style edges are inferred from proximity and campus
structure. Every one is marked `"inferred": true` in the JSON, and each file
has a `_verify` block listing exactly what a student should correct:

1. Check the inferred paths against routes actually walked.
2. OpenStreetMap maps only 6 buildings inside the campus boundary, and the
   news coverage describes about 30 facilities — add the rest.
3. Six locations are placed from a verbal description, good to ±10 m. Any
   measured coordinate improves them.

> **Why this matters.** An earlier version of this project shipped a campus
> that was entirely invented: generic buildings ("Main Gate", "Canteen",
> "Block A"), made-up coordinates, made-up distances — while carrying a real
> college's name. That is indefensible in a viva, because nobody can check
> it and someone who knows the campus will spot it immediately. Real data
> with clearly-marked gaps is worth more than convincing-looking fiction.

---

## The question this project answers

"Campus Navigation" is an easy task to do wrongly. It is tempting to read
"shortest route" as "fewest turns", reach for BFS, and stop. On a campus,
each path has a different length, so **fewest pathways is not the same as
fewest metres** — and the two answers can be compared directly.

### The sources, and which one wins

Five sources feed this map, and they are not equal. **[`SOURCES.md`](SOURCES.md)
lists every one of them** with the actual quotation behind each fact:

| Source | What it can establish |
|---|---|
| The student's Google Maps screenshot | **where** things are — the only source of geometry |
| **OpenStreetMap** (© contributors, ODbL) | surveyed coordinates for 4 buildings |
| **A student's campus tour video** | **what** the blocks are called: A=USAR, B=USDI, C=library, D=canteen |
| **India Today, Nov 2022** | storeys, capacities, the separate library block |
| **The student, 13 corrections** | how the paths actually connect |

The rule when they disagree: *a source that can place a building beats one
that can only name it — and a human who has stood there beats both on names.*
When a human contradicted the video, that went into `CORRECTIONS.md` with
both claims rather than quietly into the data.

### On the real campus

After twelve corrections from the student — the gates named and moved, the
park and two buildings removed, Block A identified as the main building,
Block B pinned down as a single building with the Library on the way to it,
Parking placed on the Gate 1 path, and the hostels chained in behind the
Sports Hall — the two algorithms split on **11 of 55 pairs**:

| Journey | BFS (fewest pathways) | Dijkstra (fewest metres) |
|---|---|---|
| **Block A → Block B** | 2 hops, **300 m** | 2 hops, **110 m** |
| Gate 1 → Block B | 4 hops, 630 m | 4 hops, 440 m |
| Auditorium → Block B | 3 hops, 545 m | 3 hops, 355 m |

**Block A → Block B is the one to quote.** BFS walks out to the gate and back
in: Block A (USAR) → **Gate 2** → Block B (USDI), 300 m. Dijkstra goes the way
a student actually walks, past the Library: Block A → **Library (C-Block)** →
Block B, **110 m**.
Identical hop count — 2 pathways either way — but **190 m less walking, 63%
shorter**. Neither algorithm is wrong; they are answering different questions,
and only one of them is the question the user asked.

That route is the best argument for this whole project. It is not a
coincidence that Dijkstra's answer is the path the student described: the
Library really does sit between Block A and Block B, and the map only knew
that because a human who walks it said so.

This is what correct data does to a benchmark. The invented campus "disagreed
on 24 of 91", but it was fiction. Twelve corrections from the student took
the real map from 1 disagreement to 11 — and every one of them came from a
person, not from OpenStreetMap, which independently locates only four of the
eleven locations. The map was wrong in ways no amount of data-gathering would
have caught: a gate on the wrong side of the campus is not a rounding error,
and only someone who walks through it every day would notice.

The task's actual question — "why this algorithm?" — still has a definite
answer, and to show it you need a graph that exercises it. So the repo ships
a **second, synthetic dataset** built with one deliberate detour, and there
the algorithms split sharply:

![BFS versus Dijkstra](docs/sample-campus/bfs-vs-dijkstra.svg)

**Sports Complex → Central Library** (sample campus)

| | Route | Pathways | Metres |
|---|---|---|---|
| **BFS** | Sports Complex → Central Library | **1** | 420 m |
| **Dijkstra** | Sports Complex → Block A → USAR → Central Library | 3 | **270 m** |

BFS takes a single service road behind the sports field; Dijkstra takes three
shorter pathways and saves **150 m — 36%**. Across the sample campus the two
disagree on **24 of 91 pairs**, worst case 69%.

Both benches are checked in: `docs/bench-usar.txt` and `docs/bench-output.txt`.
**Being able to say which of your datasets produces which behaviour, and why,
is worth more than a demo that only shows the convenient case.**

---

## Quick start

No dependencies. Python 3.10+, standard library only.

```bash
git clone <your-repo-url>
cd campus-navigation

# the real campus
python main.py list    -c campuses/usar-east-campus.json
python main.py route   -c campuses/usar-east-campus.json --from main_gate --to boys_hostel
python main.py compare -c campuses/usar-east-campus.json --from auditorium --to main_gate

# the synthetic sample, which has more disagreeing pairs
python main.py compare --from sports --to library

./run_checks.sh        # tests + regenerate docs + benchmarks + smoke test
```

```console
$ python main.py compare -c campuses/usar-east-campus.json --from auditorium --to main_gate

  campus: USAR East Campus, GGSIPU (from OpenStreetMap)
  Locations and coordinates from OpenStreetMap (© OpenStreetMap
  contributors, ODbL). Distances are straight-line estimates...

  Auditorium -> Main Gate
  --------------------------------------------------------------
  algorithm      cost   hops  expanded   route
  --------------------------------------------------------------
  BFS           585m      2         9   Auditorium -> Academic Block -> Main Gate
  Dijkstra      485m      2         9   Auditorium -> Maharaja Surajmal Park -> Main Gate
  A*            485m      2         3   Auditorium -> Maharaja Surajmal Park -> Main Gate
```

### Interactive map

`docs/index.html` is a single self-contained file — no CDN, no build step, no
server. Open it, pick a start and destination, switch algorithms, and watch
the yellow search frontier expand before the route is drawn in blue. A
second copy for the sample campus lives at `docs/sample-campus/index.html`.

```
python3 main.py demo -c campuses/usar-east-campus.json   # same thing in a terminal
```

**It shipped broken for several revisions, and that is worth knowing about.**
The "try this pair" example links were a hand-picked list from the synthetic
sample campus, embedded unchanged into *every* campus page. On the real
campus a link rendered `N["main_gate"].name`, `N["main_gate"]` was undefined,
and the script threw on load — the page was dead, not merely wrong. The build
succeeded, the tests passed, and the file was the right size, so nothing
noticed until the page was actually opened in a DOM.

Examples are now derived from whatever graph is being drawn, and
`tests/test_app.py` checks the things that were false: every example pair
exists on that campus, every id the script reaches for is in the page, and —
when jsdom is installed — the page loads with no exceptions, fills its
dropdowns, and really draws a route.

### Regenerating everything

```bash
python tools/build_usar_campus.py                  # OSM data -> campus JSON
python tools/build_usar_from_screenshot.py         # + traced layout -> shipped campus
python gen_docs.py -c campuses/usar-east-campus.json    # campus JSON -> figures
python gen_docs.py --docs-dir docs/sample-campus        # the synthetic sample
```

No file in `docs/` is hand-edited, and the README's figures are those same
generated files, so they cannot drift from the code.

---

## Project layout

```
campus-navigation/
├── main.py                      CLI entry point
├── bench.py                     the three experiments behind DECISIONS.md
├── gen_docs.py                  regenerates every figure from a campus file
├── tools/
│   ├── build_usar_campus.py          USAR campus from OpenStreetMap only
│   └── build_usar_from_screenshot.py the shipped layout, traced from the
│                                     user's screenshot + OSM coordinates
├── campuses/
│   ├── usar-east-campus.json          the real campus
│   ├── usar-east-campus-context.json  + landmarks up to ~1 km out
│   ├── usar-osm-raw.json              OSM-only extraction, kept as a check
│   ├── sample-campus.json             synthetic; exercises BFS vs Dijkstra
│   └── MY-CAMPUS.template.json        fill this in with your own campus
├── campus_nav/
│   ├── data.py          the SYNTHETIC sample (labelled as invented)
│   ├── loader.py        load and validate a campus JSON file
│   ├── geo.py           shared distance / weight-derivation formula
│   ├── graph.py         adjacency-list graph + validation
│   ├── algorithms.py    BFS, Dijkstra, A*
│   ├── visualize.py     SVG map + interactive HTML generator
│   └── cli.py           list / route / compare / map / demo / validate
├── tests/               47 tests, including exhaustive cross-checks
├── docs/                generated figures, interactive pages, bench logs
├── run_checks.sh        tests → regenerate docs → benchmarks → smoke test
├── README.md · DECISIONS.md · AI_USAGE.md
```

---

## Graph representation

An **adjacency list**: `dict[str, list[tuple[str, int]]]`.

| | Adjacency list (used) | Adjacency matrix (rejected) |
|---|---|---|
| Memory | O(V + E) → 24 directed entries | O(V²) → 100 cells, 76% wasted |
| Iterate neighbours | O(deg v) | O(V) |
| Look up one edge | O(deg v) | O(1) |

The campus is sparse (E ≈ 1.2 × V on the real graph). The one operation a
matrix wins — a direct edge lookup — is never inside a search loop. Nodes are
string ids (`main_gate`, `boys_hostel`) rather than integer indices, which
removes a whole class of off-by-one bugs. Full reasoning: DECISIONS.md #1.

Pathway weights are **derived from the coordinates** as
`round(euclidean / 5) × 5` metres, so the picture and the algorithm cannot
disagree. An explicit weight is only stored where the real walk is longer
than the straight line, and each such edge must carry a `"why"` explaining
it. The loader **rejects any pathway shorter than the straight line between
its endpoints**, because that would make A\*'s heuristic inadmissible.

---

## Algorithms

| Algorithm | Optimises | Complexity | Used when |
|---|---|---|---|
| **BFS** | fewest pathways | O(V + E) time, O(V) space | every pathway costs the same |
| **Dijkstra** | fewest metres | O((V + E) log V) time, O(V) space | **the default** |
| **A\*** | fewest metres, faster | O((V + E) log V) worst case | coordinates are known |

**Why Dijkstra is the default.** Pathway lengths differ substantially (20 m
to 340 m on the real campus), so fewest-pathways is not fewest-metres.
Dijkstra is optimal for non-negative weights, and every weight is validated
positive at load time.

**Why BFS is still there.** It is the honest answer for an *unweighted*
campus, it is what exposes the disagreement above, and it powers
`is_connected()`.

**Why A\* is worth having.** Straight-line distance is a lower bound on
walking distance, so it is admissible — A\* returns Dijkstra's route, never a
worse one. It is scaled by 0.95 so rounding pathway lengths to 5 m cannot
make the heuristic overestimate (DECISIONS.md #4).

### Measured results

Real campus, all 45 pairs (`python bench.py -c campuses/usar-east-campus.json`):

| Algorithm | avg nodes expanded | max | avg time |
|---|---|---|---|
| BFS | 6.53 | 10 | 0.010 ms |
| Dijkstra | 6.33 | 10 | 0.012 ms |
| **A\*** | **3.98** | 7 | 0.016 ms |

A\* expands **37% fewer nodes** than Dijkstra for identical answers.

Synthetic sample, all 91 pairs: BFS 8.49, Dijkstra 7.91, **A\* 3.80** — 52%
fewer expansions.

Scaling on synthetic campus-like graphs (`bench.py`, Experiment 2a):

| V | E | BFS expanded | Dijkstra expanded | A\* expanded | A\* saving |
|---|---|---|---|---|---|
| 40 | 57 | 26 (65%) | 26 (65%) | 22 (55%) | 15% |
| 80 | 113 | 27 (34%) | 73 (91%) | 48 (60%) | 34% |
| 160 | 229 | 47 (29%) | 91 (57%) | 41 (26%) | 55% |
| 320 | 457 | 143 (45%) | 281 (88%) | 164 (51%) | 42% |
| 640 | 932 | 218 (34%) | 526 (82%) | 220 (34%) | 58% |

Dijkstra's search radius grows with the graph; A\* stays pointed at the goal.

**An honest negative result.** On a *uniform grid* with equal weights, A\*
saves nothing — all three expand 100% of nodes. Euclidean distance is a weak
heuristic on a 4-connected grid (Manhattan would be exact), and on an
unweighted graph BFS is already optimal. A\* is not free speed. That
experiment is kept in `bench.py` precisely because it argues against the
convenient conclusion.

---

## Reference solution used by the tests

Dijkstra's output is not taken on trust. For every pair, on both campuses,
the suite re-derives the answer two independent ways:

1. **Re-costing** — walk the returned path and sum its edge weights, which
   catches a path/cost mismatch.
2. **Exhaustive search** — every simple path enumerated by DFS with
   branch-and-bound. Exponential in general, instant at this size, and
   completely independent of the code under test.

```bash
python -m pytest tests/ -v      # 47 passed
```

---

## Bring your own campus

The campus is **data, not code**. `campuses/MY-CAMPUS.template.json` is a
fill-in template.

```bash
cp campuses/MY-CAMPUS.template.json campuses/my-campus.json
# fill it in, then:
python main.py validate -c campuses/my-campus.json
python main.py list     -c campuses/my-campus.json
python gen_docs.py      -c campuses/my-campus.json
```

You do not need to measure anything precisely — only the weights drive
routing, so relative order is what matters. Omit `weight` and it is derived
from `x`/`y`. **Malformed files fail loudly with the offending entry named:**

```console
$ python main.py validate -c bad.json
error: path #12: unknown location 'liberry'. Declared locations: block1,
       canteen, gate, hostel, library, metro, sports, workshop

$ python main.py validate -c bad2.json
error: path #12: gate-sports is 20 m but the map puts those two points
       267 m apart. A pathway shorter than the straight line breaks the
       A* heuristic. Either raise the weight or fix the coordinates.
```

If you would rather build the campus from OpenStreetMap the way this repo
does, `tools/build_usar_campus.py` is a worked example to copy: query
Overpass, point-in-polygon test against the campus boundary, project to a
local metre grid with an equirectangular approximation, and emit the JSON.

---

## Bonus work

The task's bonus is *"create a simple visual map **or** compare two
shortest-path approaches"*. Both are implemented: generated SVG maps and an
interactive page, plus BFS vs Dijkstra run head to head on any pair.

---

## Corrections

Thirteen rounds of "that's wrong, fix it" from the student who walks the
campus. Every one is written up in [`CORRECTIONS.md`](CORRECTIONS.md) with
what was said and what changed.

**Every correction is also re-checked automatically.** `tools/audit_map.py`
walks the shipped graph and tests each correction as a geometric claim - is
Block A still left of you entering Gate 2, is the Library still between the
two blocks, are the hostels still behind the sports pair - then prints a
pass/fail line for each. One verdict, no prose:

```
python3 tools/audit_map.py        # -> docs/audit-report.txt
```

And [`docs/map-walkthrough.html`](docs/map-walkthrough.html) puts the map,
every location's source, and the routes on one page.


`CORRECTIONS.md` tracks fixes made against the real campus, point by point —
what was wrong, where the fix came from, and how to verify it. The first two
entries are the second gate (the one beside the auditorium) and the naming of
the main building as Block A; the open questions below them are waiting on
answers from someone who has actually walked the site. That file is the honest record of how this map got from "an AI
invented a campus" to "a student corrected it".

Current state of the campus data:

| | Count |
|---|---|
| Locations | 12 |
| Pathways | 18 |
| Coordinates from OpenStreetMap | 4 |
| Traced from the screenshot | 1 |
| Described by the student (position estimated) | 7 |
| Corrected by the student, point by point | 12 |
| Revisions written up in total (12 from the student + 1 from research) | 13 |
| BFS/Dijkstra disagreements on the real campus | 11 of 55 |
| Still needing an answer | 5 open questions |

## Limitations

- **The campus map is not a copy of OpenStreetMap.** Three buildings OSM
  does map (Teachers' Hostel and two unnamed blocks) are deliberately left
  out of the shipped campus at the student's request, as is USAR Ground. They remain in
  `campuses/usar-osm-raw.json`, the untouched extraction, so the omission is
  visible rather than silent.
- **OSM coverage of USAR's campus is partial.** Only 6 buildings fall inside
  the mapped campus polygon, two are unnamed, and only four footpaths are
  mapped. The graph is honest about this rather than filling the gaps with
  invented buildings — see the `_verify` block in each campus file.
- **The grounds and roads are traced from a screenshot, not surveyed.** Those
  four locations are accurate to roughly ±10 m and are marked as such in the
  data. OSM and the screenshot also disagree about where Surajmal Park is;
  the screenshot was followed, and the disagreement is recorded rather than
  quietly resolved.
- **On the real campus the algorithms agree on every pair.** See above — the
  synthetic sample exists to exercise the case where they do not.
- **Distances are straight-line estimates**, not surveyed walking routes, and
  they do not account for which entrances are actually open or where you can
  legally cross a road.
- **Edges are inferred.** OSM does not map a footpath for most of them.
- Walking cost is distance only. Real navigation cares about time of day,
  stairs, accessibility, lighting and weather.
- One algorithm per query. Repeated queries would benefit from a precomputed
  all-pairs table (Floyd–Warshall, O(V³)) — trivial at this size.
- The map is a schematic projection onto a local metre grid, not a surveyed
  campus plan. North is up.

## What I would do next

1. Walk the campus with a phone and replace the inferred edges with real
   paths and real distances.
2. Fill in the buildings OSM is missing — the administrative block, the
   lecture theatres, the labs, the staff quarters, and the tennis courts and
   football field beside the sports hall, all named in the 2022 coverage.
3. All-pairs precomputation so repeat queries are O(1).
4. Accessibility mode: mark pathways step-free and search a filtered
   subgraph — trivial with an adjacency list, awkward with a matrix.

## Submission checklist

The task sheet asks for specific things. This is where each one lives.

| Required | Where | |
|---|---|---|
| Locations and connections as a graph | `campus_nav/graph.py`, `campuses/*.json` | adjacency list, V=12, E=18 |
| User chooses start and destination | `main.py route`, `main.py demo`, `docs/index.html` | CLI, menu, and browser |
| Shortest path with route and total cost | `campus_nav/algorithms.py` | `Route.path`, `Route.cost`, distance in metres |
| Dijkstra for a weighted graph | `main.py route` (default) | O((V+E) log V) with a binary heap |
| BFS for unweighted | `main.py route --algorithm bfs` | O(V+E) |
| **Justify the algorithm choice** | `DECISIONS.md` §2, §3 · README "The question this project answers" | Block A → Block B: 2 hops either way, 300 m vs 110 m |
| **Complexity analysis** | `DECISIONS.md` "Complexity summary" | time and space per operation |
| **A design change / edge case** | `DECISIONS.md` — 11 numbered decisions, plus a table of 7 edge cases | provenance model §10, docs-as-tests §11 |
| Bonus: visual map | `docs/campus-map.svg`, `docs/index.html` | + routes drawn, search animated |
| Bonus: compare two approaches | `main.py compare`, `bench.py`, `docs/bench-usar.txt` | BFS vs Dijkstra vs A* |
| **README.md** | `README.md` | |
| **DECISIONS.md** | `DECISIONS.md` | |
| **AI_USAGE.md** | `AI_USAGE.md` | including where the AI was wrong |
| Working code, ready for GitHub | `tests/` + `.github/workflows/tests.yml` | 78 tests, CI on 4 Python versions |

**Not claimed:** this is one focused DSA task, not a general campus platform.
No database, no web framework, no authentication. The scope was chosen to
fit the 4–6 hour budget and to be defensible line by line.

---

## Data credits

Campus data: **© OpenStreetMap contributors**, [ODbL 1.0](https://opendatacommons.org/licenses/odbl/).
Boundary polygon: OSM `way/1186490427` ("GGSIPU East Delhi Campus").
`campuses/sample-campus.json` and `campus_nav/data.py` are **synthetic** and
are labelled as such everywhere they appear.
