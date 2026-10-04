# Evaluation prep

The task sheet says evaluators may question the code and the design. This is
the short version of everything I would need to answer those questions, in
the order they are likely to come up.

**Read this file, `CORRECTIONS.md`, and `SOURCES.md` and you can defend the
whole project.** Everything here is verifiable by running something.

---

## 1. The 30-second version

A weighted graph of 12 campus locations and 18 pathways, built from my own
college. The user picks a start and a destination; the program returns the
route and the total distance. Dijkstra is the default because the graph is
weighted; BFS is kept and benchmarked against it to show *why*.

The interesting part is not the algorithm — it is where the data came from,
and the fact that the map was wrong nine times and someone who walks the
campus fixed it.

---

## 2. The questions that will actually be asked

### "Where did this map come from?"

The answer, in one breath:

> "The layout is traced from a Google Maps satellite screenshot of my campus.
> Building coordinates are OpenStreetMap. Every location in the JSON says
> which it is — `osm:way/1186488777`, or `screenshot` with the pixel I read
> it from, or `described` where a student told me how it connects. The scale
> comes from two anchors: Google's pin and an OSM gate node, 213 px apart in
> the image and 328 m on the ground, so 1 px = 1.54 m."

Then open `SOURCES.md`. **Never say "the AI made it."**

### "Did you just get an AI to generate this?"

Open `AI_USAGE.md`. The honest answer:

- The AI wrote most of the code, and the file lists what it got wrong:
  an invented campus, a gate in the wrong place, notes filed against the
  wrong building, a documentation file three corrections out of date, an
  interactive page that did not load, and an audit script whose own check
  was broken.
- **I decided** the graph structure, that provenance had to be per-location,
  that Dijkstra is the default, and that the map must match the campus I
  actually walk.
- **I corrected it nine times** with things no source on the internet has.
- Every correction is in `CORRECTIONS.md` with what I said and what changed.

The strongest sentence available: *"The map was wrong in ways no amount of
data gathering would have caught. A gate on the wrong side of the campus is
not a rounding error, and only someone who walks through it every day would
notice."*

### "Why Dijkstra and not BFS?"

> "BFS minimises the number of edges. Walking time depends on distance, and
> the edges here run from 45 m to 330 m. So BFS and Dijkstra are answering
> different questions, and only one of them is the question that was asked."

**The example to give:** Block A (USAR) → Block B (USDI). BFS goes out of the
gate and back in for the same 2 hops but **300 m**. Dijkstra goes past the
Library in 2 hops and **110 m**. Same number of turnings, **63 % less
walking**. And Dijkstra's answer is the route the student described by hand
before any of it was computed.

### "Why not just use A\*?"

It is implemented, and it returns the same cost as Dijkstra on every pair
(`tests/` assert this). It is not the default because the benefit is
proportional to graph size:

| V | A\* expansion saving |
|---|---|
| 40 | 15 % |
| 160 | ~40 % |
| 640 | 58 % |

At V = 12 the heuristic buys almost nothing, and it costs an extra scale
factor to reason about — the heuristic is multiplied by 0.95 to keep it
admissible, which `DECISIONS.md` §4 explains. On a 40×40 uniform grid the
saving is **0 %**, and that negative result is in the benchmark rather than
quietly dropped.

### "What is the complexity?"

| | Time | Space |
|---|---|---|
| BFS | O(V + E) | O(V) |
| Dijkstra (binary heap) | O((V + E) log V) | O(V) |
| A\* | O((V + E) log V) worst case | O(V) |

At V = 12, E = 18 this is microseconds. The complexity argument matters
because it decides which structure is correct: an adjacency list at
E ≈ 1.5 V, not a matrix, because a matrix would waste O(V²) space on a graph
that is 12 % dense.

### "How do you know the shortest paths are actually shortest?"

`tests/test_algorithms.py` enumerates **every simple path** between every
pair by brute force and asserts the algorithm's cost is the minimum. Not a
second implementation of Dijkstra compared against the first — exhaustive
enumeration, so a shared misunderstanding cannot pass.

### "What happens if the destination is unreachable?"

`NoPathError`, naming the nodes expanded, CLI exit code 3. Tested with a
disconnected 3-node graph. Also handled: start = destination (cost 0),
typos (`libary` → did-you-mean via `difflib`), self-loops and negative
weights refused at construction.

### "What is the hardest thing you had to change your mind about?"

Gate 2 moved **four times**. It started on the south road (wrong), moved to
the auditorium's lane, then into the gap between Block A and Block B, then
further out. Two of my own corrections contradict each other — the auditorium
lane is 160 m from the gap — and rather than silently picking one, the
conflict is written into `CORRECTIONS.md` as open question 11b and into the
test file as a comment. **The later, more specific instruction was followed,
and the disagreement is on the record.**

### "What would you do differently?"

Kept in the README, honestly: walk the campus with a phone and replace the
inferred edges with measured ones; get the buildings OSM is missing. The map
has 12 locations against the ~30 the news coverage describes. That gap is
the honest limit of a screenshot, a transcript and a news report — inventing
the rest is exactly the mistake this project started with.

---

## 3. If they ask you to change something live

**Where the data lives:** `tools/build_usar_from_screenshot.py` — one list
of locations, one list of edges. Edit, then:

```bash
python3 tools/build_usar_from_screenshot.py   # rebuild the campus JSON
python3 tools/audit_map.py                    # does every correction still hold?
python3 -m pytest tests/ -q                   # 77 tests
bash run_checks.sh                            # everything, ends in ALL CHECKS PASSED
```

**The three commands worth having in your fingers:**

```bash
python3 main.py list    -c campuses/usar-east-campus.json
python3 main.py route   -c campuses/usar-east-campus.json --from block_a --to sports
python3 main.py compare -c campuses/usar-east-campus.json --from block_a --to block_b
```

**If a test fails after your edit**, it is telling you which promise broke.
The tests are named after the sentences students said — e.g.
`test_entering_gate_2_block_a_is_left_and_block_b_is_right`. Read the test
name, not the traceback.

---

## 4. Things that are not perfect, and should be said out loud

| | |
|---|---|
| **Two corrections contradict each other** | Gate 2: auditorium lane vs between the blocks. Both are in `CORRECTIONS.md`; the newer one was followed |
| **Six locations are estimates** | `source: described` — placed from a verbal description, good to about ±10 m |
| **Every pathway is inferred** | OSM maps only four footpaths here; the edges come from a student describing how they walk |
| **12 locations vs ~30 in the news coverage** | administrative block, lecture theatres, labs, staff quarters, the football field and tennis courts are all real and absent |
| **The canteen was removed and then restored** | the student said it was inside Block B; a campus tour video says it is its own block. The video won, and the reversal is logged |
| **`docs/` is generated** | do not hand-edit it; `run_checks.sh` regenerates it, and CI fails if it drifts from the code |

Saying these before you are asked is worth more than having an answer ready.

---

## 5. Map of the repository

| File | What it is for |
|---|---|
| `README.md` | the project, how to run it, the headline result |
| `DECISIONS.md` | **required** — design decisions and edge cases |
| `AI_USAGE.md` | **required** — how AI was used, and where it was wrong |
| `SOURCES.md` | where every fact came from, and which source wins |
| `CORRECTIONS.md` | the 13 rounds of correction, in the student's words |
| `EVALUATION.md` | this file |
| `campus_nav/` | the library: graph, algorithms, loader, visualisation, CLI |
| `campuses/` | the data: the real campus, the raw OSM extract, the sample |
| `tools/` | build scripts, the audit, the page generators |
| `tests/` | 78 tests, including the app loaded in a real DOM |
| `docs/` | generated: the map, the routes, the interactive app |
