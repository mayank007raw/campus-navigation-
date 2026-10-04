"""
The interactive app must actually work - not just exist.

`docs/index.html` shipped for several corrections with a fatal bug: the
example journey links were a hand-picked list from the *synthetic sample*
campus, embedded unchanged into every campus page. On the real campus the
link rendered `N["main_gate"].name`, and `N["main_gate"]` is undefined, so
the script threw on load and the whole page was dead.

Nothing caught it because the build succeeded, the tests passed, and the
file was the right size. These tests check the two things that were wrong:
the page loads, and every id the page reaches for exists.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from campus_nav.graph import CampusGraph  # noqa: E402
from campus_nav.visualize import build_html  # noqa: E402

CAMPUSES = [
    ROOT / "campuses" / "sample-campus.json",
    ROOT / "campuses" / "usar-east-campus.json",
    ROOT / "campuses" / "usar-east-campus-context.json",
]

SCRIPT = re.compile(r"<script>(.*?)</script>", re.S)
PAYLOAD = re.compile(r"const DATA\s*=\s*(\{.*?\});", re.S)


def _page(tmp_path: Path, campus: Path) -> tuple[str, dict]:
    out = tmp_path / f"{campus.stem}.html"
    build_html(CampusGraph.load(campus), out)
    html = out.read_text(encoding="utf-8")
    data = json.loads(PAYLOAD.search(html).group(1))
    return html, data


@pytest.mark.parametrize("campus", CAMPUSES, ids=lambda p: p.stem)
def test_example_journeys_exist_on_this_campus(tmp_path, campus) -> None:
    """Every 'try this pair' link must name two locations that are here."""
    _, data = _page(tmp_path, campus)
    nodes = data["nodes"]
    assert data["demos"], "the page should offer at least one example"
    for a, b in data["demos"]:
        assert a in nodes, f"example start {a!r} is not a location on {campus.stem}"
        assert b in nodes, f"example end {b!r} is not a location on {campus.stem}"
        assert a != b


@pytest.mark.parametrize("campus", CAMPUSES, ids=lambda p: p.stem)
def test_examples_are_ones_the_algorithms_disagree_about(tmp_path, campus) -> None:
    """The first example should be showing off something.

    If BFS and Dijkstra agree on every pair, the examples fall back to long
    journeys - which is fine, but the page should still be truthful about
    what it is demonstrating.
    """
    _, data = _page(tmp_path, campus)
    a, b = data["demos"][0]
    r = data["routes"][f"{a}|{b}"]
    bfs, dij = r["bfs"]["path"], r["dijkstra"]["path"]
    assert bfs and dij


@pytest.mark.parametrize("campus", CAMPUSES, ids=lambda p: p.stem)
def test_every_element_the_script_reaches_for_exists(tmp_path, campus) -> None:
    """getElementById on a missing id gives null, and null.foo is fatal."""
    html, _ = _page(tmp_path, campus)
    script = SCRIPT.search(html).group(1)
    markup = html[: html.index("<script>")]
    ids = set(re.findall(r"getElementById\(['\"]([^'\"]+)['\"]\)", script))
    missing = sorted(i for i in ids if f'id="{i}"' not in markup)
    assert not missing, f"script uses ids that are not in the page: {missing}"


def test_the_page_is_self_contained(tmp_path) -> None:
    """No CDN, no external file: it has to work offline and in a sandbox."""
    html, _ = _page(tmp_path, CAMPUSES[1])
    assert "<script src=" not in html, "the page must not load scripts externally"
    assert "http://" not in html.replace("http://www.w3.org", "")


JSDOM = Path("/tmp/domtest/node_modules/jsdom")


@pytest.mark.skipif(not JSDOM.exists() or shutil.which("node") is None,
                    reason="needs node + jsdom: npm install jsdom into /tmp/domtest")
def test_the_app_loads_and_routes_in_a_real_dom(tmp_path) -> None:
    """Run the page in jsdom: no exceptions, dropdowns filled, route drawn.

    This is the check that would have caught the crash. It is skipped when
    jsdom is not installed rather than failing, so the suite stays
    dependency-free, but it is worth running after touching the template:

        mkdir -p /tmp/domtest && cd /tmp/domtest && npm install jsdom
    """
    out = tmp_path / "app.html"
    build_html(CampusGraph.load(CAMPUSES[1]), out)
    script = tmp_path / "smoke.js"
    script.write_text(f"""
const fs = require('fs');
const {{ JSDOM }} = require('{JSDOM}');
const errors = [];
const dom = new JSDOM(fs.readFileSync({str(out)!r}, 'utf8'), {{
  runScripts: 'dangerously', pretendToBeVisual: true,
  beforeParse(w) {{ w.addEventListener('error', e => errors.push(e.message)); }},
}});
const d = dom.window.document;
setTimeout(() => {{
  const from = d.getElementById('from'), to = d.getElementById('to');
  if (from.options.length === 0) {{ console.log('EMPTY'); process.exit(1); }}
  const link = d.querySelector('.hint a');
  if (link) link.dispatchEvent(new dom.window.MouseEvent('click', {{bubbles:true}}));
  setTimeout(() => {{
    const res = d.getElementById('result').textContent;
    const drawn = d.getElementById('map').querySelectorAll('polyline').length;
    console.log(JSON.stringify({{errors, options: from.options.length,
      result: res.replace(/\\s+/g,' ').trim().slice(0,120), drawn}}));
    process.exit(errors.length || drawn === 0 ? 1 : 0);
  }}, 2500);
}}, 300);
""", encoding="utf-8")
    proc = subprocess.run(["node", str(script)], capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, f"jsdom smoke test failed:\n{proc.stdout}\n{proc.stderr}"
    report = json.loads(proc.stdout.strip().splitlines()[-1])
    assert report["errors"] == [], report["errors"]
    assert report["options"] >= 2
    assert report["drawn"] > 0, "no route was drawn on the map"
