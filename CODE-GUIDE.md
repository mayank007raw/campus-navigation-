# The code, explained

`HOW-IT-WORKS.md` covers the *ideas*. This file covers the *code* — enough to
open any file in this project, say what it does and why, and survive being
asked about a line of it.

You are not expected to write code from scratch in the evaluation. You are
expected to **understand what your own program does.** That is a different
and much easier thing, and it is what this file gives you.

---

## 1. Eight words, and then you can read code

Code is not a secret language. Almost everything in this project is built
from eight ideas, and you already understand six of them from ordinary life.

| Word | What it means | In this project |
|---|---|---|
| **Function** | A named recipe. You give it things, it gives something back. | `dijkstra(...)` is the recipe for "find the shortest walk" |
| **Input / argument** | What you hand to the recipe. | You hand it the campus, a start and a destination |
| **Return** | What the recipe gives back. | A route: the list of places, and the total metres |
| **Variable** | A labelled box holding one thing. | `start = "block_a"` — a box called `start` holding Block A |
| **List** | An ordered row of things. | `["block_a", "library", "block_b"]` — the route, in order |
| **Dictionary** | A lookup table: give a name, get a value. | `"block_a" → the coordinates of Block A` |
| **Loop** | Do this again and again. | "for each place you can walk to from here…" |
| **If / else** | Decide something. | "if this place is the destination, stop" |

**That's genuinely it.** When you look at the project's code and see
`for v, w in graph.neighbours(u):`, read it as: *"for each place (v) and each
distance (w) that I can reach from here (u)…"*. Every line of this project
can be read like that out loud.

> **The confidence move:** if they show you a line, don't panic and don't
> bluff. Read it out slowly like a sentence. Code is written to be read.

---

## 2. The file map — what every file does

If they ask "what's in this file?", you need one sentence. Here they are,
in the order that matters.

| File | One sentence |
|---|---|
| **`main.py`** | The front door. 19 lines. It just passes whatever you typed to the command-line handler. |
| **`campus_nav/algorithms.py`** | **The heart.** BFS, Dijkstra and A\* — the three route-finding methods. |
| **`campus_nav/graph.py`** | The campus itself: the places, the connections, and the distances between them. |
| **`campus_nav/loader.py`** | Reads a campus file from disk and checks it's valid before anything uses it. |
| **`campus_nav/cli.py`** | Handles what you type — `list`, `route`, `compare`, `map`, `demo`. |
| **`campus_nav/visualize.py`** | Draws the map and the routes, and generates the interactive web page. |
| **`campus_nav/data.py`** | The invented sample campus, used for testing and comparison. |
| **`campuses/usar-east-campus.json`** | **Your actual campus.** 12 locations, 18 paths, each with its source. |
| **`tools/build_usar_from_screenshot.py`** | Builds that file from the screenshot, OSM and your corrections. |
| **`tools/audit_map.py`** | Re-checks all 12 of your corrections against the final map. |
| **`tests/`** | 80 automatic checks that the program still works. |

**The structure in one line:** *"The data is separate from the algorithms.
The campus lives in a JSON file; the code just reads it. That's why I could
correct the map twelve times without touching the algorithm code at all."*

That last point is a genuinely good answer and it's true — it's also a real
design decision, written up in `DECISIONS.md` §8.

---

## 3. "Walk me through your code" — the 60-second script

This is the single most likely request. Here's what to do, in order. Open the
files as you speak.

**① Open `main.py`** (19 lines — it will not intimidate anyone)

> "This is the entry point. It reads what you typed and passes it to the
> command handler. Everything real is in the `campus_nav` folder."

**② Open `campus_nav/graph.py`**

> "This is the campus as data. A place is called a node, a walkable path is
> an edge, and each edge has a distance in metres. It's stored as an
> **adjacency list** — for each location, the list of places you can walk to
> directly from it, and how far. I chose that over a grid-style table because
> the campus is sparse: 12 places with 18 connections. A full table would be
> 12×12 = 144 boxes, and 126 of them would be empty."

**③ Open `campus_nav/algorithms.py`, point at `bfs_shortest_path`**

> "BFS. It spreads outwards from the start one step at a time, so the first
> time it reaches the destination it has the fewest steps. It ignores the
> distances completely — a 45-metre path and a 330-metre path both count
> as one step."

**④ Point at `dijkstra`**

> "Dijkstra. This one keeps a running total of metres from the start, and
> always continues from the place with the smallest total so far. So the
> first time it reaches the destination, that's the shortest walk."

**⑤ Open `campuses/usar-east-campus.json`, show any location**

> "And this is where the data lives — each location carries where it came
> from: an OpenStreetMap id, a pixel from my screenshot, or a note that a
> person told me."

**⑥ Finish with the example**

> "The reason both exist: Block A to Block B. Both say two turnings. BFS
> walks 300 metres out the gate and back. Dijkstra walks 110 metres past the
> library. Same turns, 190 metres less walking."

**That's a complete, confident answer.** You have not written a line of code
in front of them, and you have explained the architecture, the data
structure choice, both algorithms, and the result.

---

## 4. Dijkstra's code, line by line

This is the one piece of code worth genuinely understanding, because it is
the answer to the task. Here it is — 20 lines. Read the right column.

```python
def dijkstra(graph, start, goal):
    best = {start: 0.0}                 # distance so far: we start at 0 m
    parent = {start: None}              # how we got here (for rebuilding)
    settled = set()                     # places we're finished with
    heap = [(0.0, start)]               # to-do list, nearest first

    while heap:                         # keep going while there's work
        dist_u, u = heapq.heappop(heap) # take the nearest place on the list

        if u in settled:                # a stale entry — skip it
            continue
        settled.add(u)                  # mark it done

        if u == goal:                   # arrived? then we're finished,
            return Route(...)           # and this is the shortest route

        for v, w in graph.neighbours(u):     # for each place you can walk to
            candidate = dist_u + w           # total metres via here
            if candidate < best.get(v, INF): # is that shorter than before?
                best[v] = candidate          # remember the new shorter way
                parent[v] = u
                heapq.heappush(heap, (candidate, v))  # add to the to-do list
```

**The plain-English version:**

> "It keeps a to-do list of places, always taking the nearest one first. When
> it takes a place off the list, it checks every place you could walk to from
> there, and asks: *is going this way shorter than the best I had before?* If
> yes, it updates the record and adds it to the list. When the destination
> comes off the list, that's the shortest possible route — and the program
> then walks backwards through those records to rebuild the actual path."

**Five things they might ask about it:**

**"What's the heap?"** A to-do list that always gives you the smallest item
first. Python has one built in (`heapq`). It's what makes the algorithm fast
instead of having to search the whole list every time.

**"What is `settled` for?"** To never do the same place twice. Once a place
has been taken off the list, the shortest way to it is already known.

**"What if there are two equally short routes?"** It picks one — whichever
got there first. A route is still returned, and the *distance* is the same
either way. That's the only thing that matters.

**"What is the `parent` dictionary doing?"** The algorithm finds the *cost*,
but to show you the route it needs to know how it got there. `parent` records
"to reach this place, I came from that one". At the end the program follows
those backwards and reverses it.

**"What is `continue`?"** "Skip the rest of this round and go to the next
one." It's used to ignore entries that have already been superseded — the
technical name is *lazy deletion*, and `DECISIONS.md` §3 explains why that
choice was made instead of the alternative.

---

## 5. The code questions you'll actually be asked

### "Why Python?"

> "The task allowed it, it reads almost like English, and it needs no
> installation — no libraries, no setup. It only uses what comes built in.
> The whole project runs with `python3 main.py`."

*(True, and checkable — `requirements.txt` says the runtime has no
dependencies at all.)*

### "Where is the shortest path actually computed?"

> "`campus_nav/algorithms.py`, in the `dijkstra` function. About twenty lines."

Then open it. **Being able to open the right file instantly is what
"understanding your code" means in practice.**

### "What is an adjacency list and why did you use it?"

> "For each location, a list of the places you can walk to directly. I used
> it instead of a matrix — a full table of every location against every
> other — because this campus is sparse. Twelve places, eighteen connections:
> a matrix would be a hundred and forty-four boxes, and a hundred and eight
> of them would be empty. The adjacency list only stores the connections
> that exist."

### "How do you know the code is correct?"

> "There are 80 automated tests. The important one is that for every pair of
> locations, the test **works out every possible route by brute force** and
> checks that my algorithm's answer is the shortest. It doesn't compare my
> code against another copy of my code — it checks against exhaustive
> enumeration, so it can't be wrong in the same way twice."

### "What happens if I give it a place that doesn't exist?"

> "It fails with a clear message naming the nearest matches — not a crash.
> If you type `libary` it suggests the library. And it's refused at the point
> the file is loaded, not silently ignored."

### "What if two places aren't connected?"

> "It raises a specific error and says how many places it searched. There's a
> test for it using a deliberately disconnected three-place graph. And on the
> real campus, a check refuses to even build a map with an unreachable
> building — that caught a real bug once when the canteen got isolated."

### "How do you handle a negative distance?"

> "It refuses to load the file. Negative distances silently break Dijkstra —
> they don't crash it, they make it return wrong answers, which is worse. So
> it's rejected up front."

### "Is it fast?"

> "At this size, everything is under a millisecond. But the complexity
> analysis still matters, because it decides which structure is right:
> BFS is O(V+E), Dijkstra is O((V+E) log V). The project measures this and
> scales the test up to 900 locations to show how it grows."

---

## 6. What a test is, and why there are 80

A **test** is a small program that checks one promise. It either passes or
fails, and it tells you immediately if you've broken something.

Here's a real one from this project:

```python
def test_entering_gate_2_block_a_is_left_and_block_b_is_right():
    ...
    assert cross("block_a") < 0, "Block A must be on the LEFT entering Gate 2"
    assert cross("block_b") > 0, "Block B must be on the RIGHT entering Gate 2"
```

Read that as: **"check that walking in through Gate 2, Block A is on the left
and Block B is on the right — exactly what I told the computer."**

The `assert` line means *"this must be true; if it isn't, stop and complain."*
The message in quotes is what gets printed.

**Why they matter here.** Your corrections live on as tests. If someone later
moves Block B, the test fails and says:

> `Block B must be on the RIGHT entering Gate 2`

So the map can't silently drift away from what you told it. **Your knowledge
is enforced by the code.**

**The tests are named as sentences**, on purpose. If one fails you read the
name, like `test_block_a_to_block_b_goes_past_the_library`, and you already
know what broke. Tell them that if they ask — it's a deliberate choice.

> "I've got 80 tests, and the tests are named after the sentences I said
> about my campus. So the code can't quietly drift away from the real
> layout — if it does, a test named after my own correction fails."

---

## 7. How to run it and read the output

**Three commands. Practise these in a terminal before the evaluation.**

```bash
python3 main.py list -c campuses/usar-east-campus.json
```
Prints every location. Just shows the data loaded.

```bash
python3 main.py route -c campuses/usar-east-campus.json --from block_a --to block_b
```
Prints the shortest route from Block A to Block B.

```bash
python3 main.py compare -c campuses/usar-east-campus.json --from block_a --to block_b
```
**This is the one to run.** It prints a table:

```
  algorithm      cost   hops  expanded   route
  BFS           300m      2         8   Block A (USAR) -> Gate 2 -> Block B (USDI)
  Dijkstra      110m      2         3   Block A (USAR) -> Library (C-Block) -> Block B (USDI)
```

Point at the two numbers on the left and the two route columns. **The whole
project is on that screen**: same turnings, 190 metres less walking.

**What the columns mean** — worth knowing so you can explain the output:

- **cost** — total metres walked
- **hops** — number of turnings
- **expanded** — how many places the algorithm had to look at. Lower is
  better, and it's how you compare how *efficient* two methods are, not just
  how good their answer is
- **route** — the actual way to walk

**And the all-in-one command:**

```bash
bash run_checks.sh
```
Runs the tests, rebuilds the maps, re-runs the benchmarks, and finishes with
`ALL CHECKS PASSED`.

---

## 8. The code story — real bugs, found and fixed

This is the answer to *"what went wrong while you were building it?"* and it
is much stronger than "nothing".

| The bug | What it means in plain English |
|---|---|
| **The page didn't load at all** | The example journey buttons pointed at places that only existed on the *test* campus, not the real one. Opening the page crashed the whole thing. Every test passed because nothing had ever *opened* the page. |
| **A note filed under the wrong building** | "The library is on the 5th floor" got stored against *Gate 1*. It was a bug in one line, it hid for four rounds of corrections, and it's exactly the kind of quiet wrongness an examiner would find by opening the data file. |
| **The benchmark changed every time it ran** | The test benchmark picked a connection point from a list whose order Python randomly shuffles each run. So the numbers in the report were a record of one lucky run, not a reproducible result. |
| **A checker that checked the wrong thing** | The audit's "is the park gone?" test searched for the word `park` — which matches inside **`parking`**, a real location. It reported the park as still there. |
| **Instructions describing a map that no longer existed** | The notes inside the data file still asked about buildings that had been removed six corrections earlier. |

**The line to use:**

> "Most of the bugs weren't in the algorithms — the shortest-path code was
> right early. The bugs were in everything around it: the data, the
> documentation, the page. And most of them only showed up when something
> was actually run rather than assumed."

That is a mature thing to say and it's completely true.

---

## 9. What to say and what not to say

**Do say:**

- "The algorithms are in `algorithms.py`, the data is in a separate JSON file."
- "BFS counts steps, Dijkstra counts metres."
- "The test brute-forces every route to check the answer."
- "I don't know that one — it's documented, let me find it."

**Don't say:**

- ❌ "I don't know, the AI wrote it." — You directed this project for its whole
  life. You picked the task, rejected the fake map, gave twelve corrections
  and answered every question the computer couldn't. That is authorship of
  the *content*, and the content is what makes the project good.
- ❌ "I wrote all the code myself." — The AI wrote the code and it says so in
  `AI_USAGE.md`. Claiming otherwise is checkable and unnecessary.
- ❌ Guessing at what a line does. Read it out loud instead, slowly, as a
  sentence. You will usually be right.

**If you truly don't know:** *"I'd need to check — the reasoning is written up
in `DECISIONS.md`. Would you like me to show you?"*

Opening your own documentation to find an answer scores better than a
lucky guess. It shows the project was organised, which is the thing being
assessed.

---

## 10. A note on the numbers in this file

Every figure quoted in this guide — 300 m, 110 m, 190 m saved, the 12 and 18,
the 144 boxes — was printed by running the program, not typed from memory.
If a number in this guide ever disagrees with what the program prints on the
day, **the program is right** and the guide is stale. That is the whole point
of the docs-as-tests rule in `DECISIONS.md` §11.

---

## 11. The three things to actually do before the evaluation

1. **Run the three commands above in a terminal** until you don't have to
   think about them. `compare` is the important one.
2. **Open `campus_nav/algorithms.py` and find the word `dijkstra`.** Know that
   it is about twenty lines and roughly what each part does. You do not need
   to memorise it — you need to have seen it, so it isn't a wall of
   unfamiliar symbols under pressure.
3. **Open `campuses/usar-east-campus.json` and look at one location.** See the
   `source` field and the pixel measurement. That file is the answer to
   "where did your data come from" and it is genuinely yours.

If you can do those three things, you can handle the evaluation. The project
is documented far beyond what will be asked.
