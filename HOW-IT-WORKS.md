# The whole project, in plain English

Written for someone who does not code. By the end of this you should be able
to explain the project, defend it, and answer questions about it — because
the honest story of how this was built is a good one, and it is yours.

Read it once properly. Then read section 1 and section 8 again the night
before.

---

## 1. If you remember only five things

**1. What the project does.** You type in where you are on campus and where
you want to go. It tells you the shortest route and how many metres it is.

**2. The idea underneath it.** The campus is drawn as dots and lines. Each dot
is a place (Block A, the library, a hostel). Each line is a path you can walk
between two dots. Each line has a number on it — the distance in metres.

**3. Why there are two different answers.** One method tells you the route
with the **fewest turnings**. The other tells you the route with the **fewest
metres**. On a campus those are not the same thing. That is the whole point
of the project.

**4. The example to quote.** Block A to Block B. Both methods say "two
turnings". The first walks you **300 metres** out through the gate and back
in. The second walks you **110 metres** straight past the library. Same
number of turns, **63% less walking.**

**5. Why it is really your project.** The map is your college, and the
computer got it wrong **twelve times** before you corrected it. Those twelve
corrections are written down in `CORRECTIONS.md`, and they are the reason
this project is worth anything.

---

## 2. What a "graph" is — the one word to get right

A **graph** in computing has nothing to do with bar charts. A graph is just
**dots joined by lines.**

- A **node** = one dot = one place. This campus has **12** of them.
- An **edge** = one line = a path between two places. This campus has **18**.
- A **weight** = the number on the line = how many metres that path is.

So when the task sheet says *"represent locations and connections as a
graph"*, it means: **write down the places, and write down which places
connect to which, and how far apart they are.** That's it. That is the data
for this whole project.

**A graph with numbers on the lines is called "weighted".** A graph without
numbers is "unweighted" — it only knows whether two places are connected,
not how far apart they are. That difference is the entire reason for the next
section.

> **If they ask:** "A graph is the campus drawn as points and connections.
> Each point is a location, each connection is a walkway with its length in
> metres. Twelve points, eighteen connections."

**The analogy that works.** Think of a Delhi Metro map. The stations are
nodes, the lines between them are edges, and the number of minutes between
stations is the weight. Everything else in this project is just asking
questions about that map.

---

## 3. The two methods, and why both exist

You need to be able to say what each one does in one sentence, without
notes. Here they are.

### BFS — "Breadth First Search"

**What it does:** counts turnings. It spreads out from your starting point in
every direction at once, one step at a time, until it reaches your
destination. Whatever it finds first has the **fewest number of paths
walked**.

**What it ignores:** how long those paths actually are. It treats a 45-metre
path and a 330-metre path as equally good, because both are "one step".

> **Say this:** "BFS finds the route with the fewest turnings. It doesn't
> know or care how long each path is."

### Dijkstra — "Dijkstra's algorithm" (say it: *DYKE-struh*)

**What it does:** adds up metres. It always extends from the place with the
smallest total distance travelled so far, so the first time it reaches your
destination, that is the **shortest total distance**.

**What it needs:** every path to have a positive length. Zero or negative
lengths break it — this project refuses to load a campus with a negative
path, on purpose, rather than quietly returning wrong answers.

> **Say this:** "Dijkstra adds up the actual metres and gives the shortest
> walking route. BFS counts steps. On a campus with different-length paths,
> those are two different answers."

### A\* — "A star" (named after the letter)

**What it does:** the same as Dijkstra, but with a hint. Before deciding
where to look next, it asks *"which of these places is roughly pointing
towards my destination?"* and looks there first.

**Is it a shortcut that might be wrong?** No — provided the hint never
overestimates the real distance. The hint here is the straight-line distance
("as the crow flies"), and you can never walk a shorter distance than the
straight line. So it stays correct — and this project proves it: **A\* returns
the exact same distance as Dijkstra on every single pair of locations**, and
there is a test that checks that.

> **Say this:** "A\* is Dijkstra plus an estimate of how far is left to go.
> The estimate is the straight-line distance, which can never be longer than
> the real walk, so it never gives a wrong answer — it just looks in fewer
> places."

### Why the project kept all three

The task only asked for two (BFS and Dijkstra). Keeping A\* as well made it
possible to **measure** the difference instead of guessing — and one of the
findings was a surprise: on a plain grid where every path is the same length,
A\* saves **nothing at all**. That honest negative result is in the report.
Finding something that didn't work and writing it down is worth more than
pretending everything improved.

---

## 4. How the project was actually built — the honest timeline

This is the story to tell. It is true, and it is more interesting than "I
wrote a shortest path program".

### Step 1 — Picking the task

The task sheet offered a few options. Two of them needed datasets you don't
have. Task 1 — Campus Navigation — was the one where **you get to define the
data yourself**, which is what made it possible.

### Step 2 — The first version was a lie, and it looked fine

The first map had 14 buildings and 26 paths. It drew beautifully. There was
just one problem: **none of it was real.** It was invented to look like a
college campus.

This matters enormously, so understand why. If your interviewer opens the
project and asks *"where's the library on this map?"*, you cannot answer,
because the library on that map is a made-up dot. The map said "USAR" — your
actual college — but nothing on it was your college.

> **If they ask about this, do not hide it. Say it:** "The first version was
> an invented campus. I threw it out, because if you ask me a question about
> my own college I have to be able to answer it."

The old version is actually still in the project, side by side with the real
one, at `docs/compare-original-vs-real.html`. Keeping the failure visible is
deliberate — it shows what changed and why.

### Step 3 — You supplied the real campus

You sent a Google Maps screenshot of the campus and said *"this is the layout
of usar college."* That one screenshot is the foundation of everything after
it.

### Step 4 — Turning a picture into measurements

A picture doesn't have distances in it. So we found **two points that were
known on both sides**:

- Google's own pin on the map, and
- a gate that OpenStreetMap has a recorded position for.

In the picture those two points are **213 pixels** apart. In reality they are
**328 metres** apart. So:

**1 pixel = 1.54 metres.**

That single number converts the whole picture into real distances. You can
measure anything in the image and say how far it is on the ground. This is
the cleverest technical bit of the project and it is worth remembering.

> **Say this:** "I had a satellite screenshot but no distances. I found two
> points I knew the real distance between, measured them in the image, and
> worked out that one pixel equals 1.54 metres. Then I could measure
> everything else."

### Step 5 — Adding buildings that are already surveyed

**OpenStreetMap** is a free, open map of the world that anyone can improve,
like Wikipedia for maps. It already had proper surveyed positions for four
buildings on the campus — Block A, the auditorium, a sports centre and a
gate. Those are more accurate than anything measured off a photo, so they
were used as-is.

### Step 6 — The corrections. This is the important part.

You said: **"you generate the map, I will tell you what changes if error
occurs."**

That became the method for the rest of the project. You would look at the
map, find something wrong, and say it. **Twelve times.**

Each time:

1. Your exact sentence was written down in `CORRECTIONS.md`
2. The map was rebuilt
3. All the tests were run again, to make sure the fix didn't break anything
   else

What you corrected, and this is the evidence that you know your campus:

| You said | What was wrong |
|---|---|
| "there are two gates, one by the auditorium" | The map had gates in the wrong places |
| "the main building is Block A" | The map had it under a generic name |
| "the park is not in my campus" | A park next door had been included |
| "block b is one building, close to block a, library in between" | The map had Block B as a whole cluster, far away — and this took **three attempts** to get right, because "close" isn't a distance |
| "remove the teacher hostel and 2 unknown ones" | Three buildings came off the map |
| "gate 2 in between a block and b block, sport hall and outdoor ground side to side" | Rearranged the whole middle of the campus |
| "in path from gate 1 to block a, parking comes in between" | A whole building was missing |

**Why this is the strongest thing in the project:** no amount of research
would have found those. A gate on the wrong side of a campus is not a small
error, and **only somebody who walks through it every day would notice.**

> **Say this:** "I built the first version, it was wrong, and I corrected it
> twelve times. Every correction is written down with what I said and what
> changed. The map is accurate because I checked it, not because the computer
> got it right."

### Step 7 — The research pass

You asked for research and video sources. We found a **campus tour filmed by
a student** whose web page publishes a full transcript, and it settles
something no map could: **what the blocks are called.**

> "there are a total of four blocks. The first block is our USAR, which we
> call A-Block. B-Block is for USDI, which is the design block. The third
> block is our C-Block, which is the library, and D-Block is our canteen."

So the map's block names are not guesswork — each one carries that quote in
the data file next to it.

And here's the best bit: the video describes walking past things in the
order *sports hall → main building → auditorium → ground and hostel*. That is
**the same order your corrections had already produced**, before anyone had
seen the video. Two people who have walked the campus describing it the same
way is the closest thing to proof this project has.

### Step 8 — Proving it still works

At the end, instead of just trusting the map, we wrote a program that
**re-checks every single one of your twelve corrections** against the final
data and prints PASS or FAIL for each one. It's called the audit, and it
currently passes everything.

---

## 5. What you did versus what the computer did

Be completely straight about this. It is the rule the task sheet gives —
*"AI responsibly used and explainable"* — and honesty here is a strength, not
a confession.

**You did:**

- Picked the project and the language, and said "build the whole thing"
- Rejected the first map as wrong **without being told it was wrong**
- Supplied the screenshot that everything was built from
- Gave **twelve corrections**, in your own words, about your own campus
- Answered the questions the computer couldn't work out on its own
- Asked for the research pass that found the block names

**The computer did:**

- Wrote the code
- And, importantly, **got things wrong a lot** — an invented campus, a gate on
  the wrong side of the college, a note about a library filed under a gate,
  a web page that didn't load at all, and a benchmark whose numbers changed
  every time it ran

All of those are written down in `AI_USAGE.md`. That file is not an
apology — it is the evidence that the mistakes were found and fixed rather
than hidden.

> **The line for this:** "I used AI to write the code, and I directed it. It
> got the campus wrong repeatedly and I corrected it twelve times. The
> mistakes and the fixes are all documented in `AI_USAGE.md`."

**Do not** claim you wrote the code by hand. It's checkable, and the true
story is better anyway: *you* are the one who knows the campus, and that's
what made the project good. The computer can write code. It cannot know that
the gate is in the wrong place.

---

## 6. The five hard words, translated

If they use these words, here is what they mean:

| Word | What it actually means |
|---|---|
| **Graph** | Dots and lines. Places and the paths between them. |
| **Node / vertex** | One dot. One location. |
| **Edge** | One line. One walkable path between two places. |
| **Weight** | The number on the line — here, metres. |
| **Adjacency list** | A contact list. For each place, the list of places you can walk to directly from it. |
| **Complexity (O(...))** | How the work grows as the campus gets bigger. "O(V+E)" means the work grows in proportion to the number of places plus the number of paths — doubling the campus roughly doubles the work, it doesn't explode. |
| **Heuristic** | A smart guess that speeds something up. A\*'s guess is the straight-line distance to the destination. |
| **Connected** | You can get from any place to any other place. This map is connected, and there's a test that checks it — if a correction ever isolated a building, the build would fail instead of shipping a map with an unreachable building. That actually happened once, with the canteen. |

---

## 7. The three questions you will almost certainly be asked

### "Why did you use Dijkstra and not BFS?"

> "BFS counts turnings, Dijkstra counts metres. On a campus the paths are
> different lengths — mine run from 45 metres to 330 metres — so counting
> turnings isn't the same as finding the shortest walk. Block A to Block B is
> the proof: both algorithms say two turnings, but BFS sends you 300 metres
> out through the gate and back, and Dijkstra sends you 110 metres past the
> library. Same turns, 63% less walking."

*(If you only memorise one answer from this document, memorise that one.)*

### "Where did your map data come from?"

> "Three places. The positions are traced from a satellite screenshot of my
> campus, scaled using two known points so that one pixel equals 1.54 metres.
> Four buildings come from OpenStreetMap, which has proper surveyed
> coordinates. And six places are there because I told it where they are —
> the data file marks every location with which of the three it is."

Then mention `SOURCES.md`, which lists all of it with the links.

### "Did you use AI?"

> "Yes, to write the code. I chose the project, gave it my campus, and
> corrected it twelve times against the real layout. The mistakes it made and
> how they were fixed are documented in `AI_USAGE.md`."

---

## 8. If you get stuck — the escape hatches

You will not know everything. **Nobody expects you to.** What matters is how
you handle it.

**If they ask something you don't know:** don't invent an answer.

> "I'm not sure about that one. I know it's documented — can I show you where
> I'd find it?"

Then open `EVALUATION.md` or `DECISIONS.md`. Looking something up in your own
documentation is a *good* answer. It shows you organised the work.

**If they ask you to change something live**, the three commands:

```bash
python3 main.py route   -c campuses/usar-east-campus.json --from block_a --to sports
python3 main.py compare -c campuses/usar-east-campus.json --from block_a --to block_b
bash run_checks.sh
```

The first shows a route. The second shows the BFS-versus-Dijkstra comparison —
**this is the one to run**, it demonstrates the whole point of the project in
one screen. The third re-runs everything and ends with `ALL CHECKS PASSED`.

**If the tests fail after you change something**, that's not a disaster —
that's the tests doing their job. Read the *name* of the failing test. They're
written as sentences, like
`test_entering_gate_2_block_a_is_left_and_block_b_is_right`. The name tells
you which promise you broke.

---

## 9. Numbers worth remembering

Six. Not twenty.

| | |
|---|---|
| **12 locations, 18 pathways** | the size of the map |
| **1 pixel = 1.54 metres** | how the screenshot became measurable |
| **Block A → Block B: 300 m vs 110 m** | the headline result, same 2 turns, 63% less walking |
| **12 corrections** | how many times you fixed the map |
| **80 tests** | how many automatic checks the project passes |
| **O(V + E) and O((V+E) log V)** | BFS's cost, and Dijkstra's |

Everything else is in the documents.

---

## 10. What is honestly not perfect

Say these **before** you're asked. It builds more trust than any answer you
could give afterwards.

- **Two of your corrections contradict each other.** One puts Gate 2 near the
  auditorium, the other puts it between the blocks — 160 metres apart. The
  later, more specific one was followed, and the disagreement is written
  down rather than hidden. *If you don't want that gap in the project, this is
  the one thing left to fix: tell me which is right.*
- **Six locations are estimates** placed from your descriptions, good to about
  10 metres. The file says which ones.
- **Every pathway is guessed** from how you described walking. OpenStreetMap
  only maps four footpaths on the whole campus, far too few to route on.
- **The map has 12 locations, but the news coverage describes about 30** —
  lecture theatres, labs, the administrative block, staff quarters, a football
  field. They are real and they are missing.

Saying "the map is honest about what it doesn't know" is a strong finish.

---

## 11. The one sentence that sums up the whole project

If you take nothing else from this document:

> **"I made a shortest-path finder for my own college. The interesting part
> isn't the algorithm — it's that the map was wrong twelve times, and I'm the
> one who caught it every time, because I'm the only person on this project
> who actually walks that campus."**

That is true, and it is a better answer than any amount of code.
