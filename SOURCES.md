# Where every fact on this map comes from

If an examiner asks "how do you know this is your campus?", this is the file
to open. Nothing in `campuses/usar-east-campus.json` is invented, and every
location records its own source in the JSON itself.

There are **five** sources. They are not equal: two of them can place a
building on a map, and three of them can only tell you what a building *is*.

---

## 1. The student's Google Maps screenshot — *geometry*

`uploads/Screenshot_2026-10-02-12-30-38-82_3d9111e2d3171bf4882369f490c087b4.jpg`

The authority on **where things are**. Every position on the map is either
traced from this image (recorded with the pixel it was read from,
`measured_at_px`) or derived from something placed on it.

**Scale:** two anchors — Google's own pin and the OpenStreetMap gate node —
are 213 px apart in the image and 328 m apart on the ground, so **1 px =
1.54 m**. The transform is `x = −23.4 + (px − 345) × 1.54`, and it is
reversible, which is how a position described in metres gets back onto the
image.

## 2. OpenStreetMap — *four buildings, surveyed* (© OSM contributors, ODbL)

| Location | OSM object |
|---|---|
| Block A (USAR) | `way/1186488777` |
| Auditorium | `way/1186488780` |
| Gate 1 | `node barrier=gate` |
| Sports Hall | `leisure=sports_centre` |

These coordinates are **not** estimated: they were surveyed by OSM
contributors, so they override the screenshot where the two disagree. The
untouched extraction is kept in `campuses/usar-osm-raw.json`.

## 3. A student's campus tour — *what the blocks are called*

**"USAR Campus Tour — University School of Automation and Robotics, GGSIPU
East Campus"**, Aryan Mahendru, 29 June 2023, 13:07 —
<https://www.youtube.com/watch?v=oyGoBPmT7c0>

This is the source for the **A/B/C/D block letters**, and it is quoted, not
paraphrased, in the JSON under `_tour_evidence`:

> "in this whole building of ours, there are a total of four blocks. The
> first block is our **USAR, which we call A-Block**. **B-Block is for
> USDI**, which is the design block. The third block is our **C-Block, which
> is the library**, and **D-Block is our canteen**."

It also says the canteen is *"downstairs"* and is *"the only canteen in the
entire college"*, that the library is open 9:30–17:00 Mon–Fri, and that the
sports hall has a badminton court and table tennis.

**What it cannot do: place anything.** A transcript names buildings and the
order you walk past them; it does not give coordinates. The screenshot is
still the only source of geometry.

**Its one useful geometric check** — the tour's order matches this map:

> "there is our sports hall over there … behind us, this is the entire main
> building. If we go further, we will see the auditorium there. Behind this
> is our ground, hostel."

Sports hall → main building → auditorium → ground and hostel. That is the
same ordering this map arrived at through corrections 9 and 10, from the
student describing it independently. Two independent descriptions agreeing
is the closest thing to verification this map has.

## 4. India Today, 3 November 2022 — *what is inside the buildings*

<https://www.indiatoday.in/education-today/news/story/east-delhi-to-get-new-ip-university-campus-to-offer-these-courses-2292674-2022-11-03>

Reported while the campus was being finished:

- **18.75 acres**, about **2,400 students**
- sections: **Administrative, Auditorium, Teaching, Sports** — plus a
  **separate library block**
- the academic block is **two 9-storey buildings and one 7-storey building**
- **4 lecture halls** (120 each), **24 classrooms** (100 each)
- **sports hall**, capacity 300; **5-storey auditorium block**, capacity 650
- hostels for about **500 students**, plus **48 staff quarters**
- **2 tennis courts and a football field** alongside the sports hall
- solar panels on every roof (India's first net-zero energy campus)

These are facts about the *insides* of buildings, so most of them cannot be
nodes on a 2-D graph. They are recorded where they belong — as `_tour_evidence`
on the building they describe — rather than dropped.

## 5. The student — *how the paths actually connect*

`CORRECTIONS.md`, thirteen corrections, each one dated by who said it and
what changed. This is the source that found the errors **no other source
could**: a gate on the wrong side of the campus is not a rounding error, and
only someone who walks through it every day would notice. OpenStreetMap
independently locates 4 of the 12 locations, and names none of them the way
the student does.

---

## Where the sources disagree, and who wins

| Disagreement | Resolution |
|---|---|
| OSM calls the main building by a generic name | **the student** — "the main building is Block A" |
| The screenshot puts the gate south; OSM has gate nodes on the west | **the student + OSM** — the gate moved twice |
| The student said the canteen is *inside Block B*; the tour says it is its **own** block, D | **the tour** — the canteen is drawn as Block D. Flagged in `CORRECTIONS.md` as the one place a source overruled the student |
| Correction 7 put the gate in the auditorium's lane; correction 10 put it between the blocks | **the later, more specific instruction** — and the conflict is written down, not hidden |

**The rule:** a source that can *place* a building beats a source that can
only *name* it. A human who has stood there beats both on names — but when a
human contradicts a filmed walkthrough, that goes in `CORRECTIONS.md` with
both claims, not quietly into the data.

## What no source can tell us

The map is 12 locations against the ~30 the news coverage implies
(administrative block, lecture theatres, labs, faculty residences, 48 staff
quarters, and the USDI building as more than a block letter). That gap is
not a failure of research — it is the honest limit of what can be verified
from a screenshot, a transcript and a news report. Inventing the rest is
exactly the mistake this project started with.
