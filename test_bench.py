"""
The benchmark has to be reproducible, or the numbers in the README are
decorative.

`bench.py` seeds its random graph generator, which looks like it makes the
experiment deterministic. It did not: the loop that stitches disconnected
components together picked its joining node with `next(iter(seen))`, and
`seen` is a set of strings - so Python's per-process string hash
randomisation chose a different node on every run. The graph changed shape,
and so did every expansion count quoted in the README.

These tests run the generator in fresh subprocesses with different hash
seeds, which is the only way to see the bug: inside one process the hash
seed is fixed and the code looks perfectly deterministic.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PROBE = """
import json, sys
sys.path.insert(0, {root!r})
from bench import _random_campus
out = {{}}
for n in (40, 80, 160):
    g = _random_campus(n, seed=7)
    out[n] = {{'V': g.num_nodes, 'E': g.num_edges,
              'edges': sorted(tuple(sorted((e.a, e.b))) for e in g.edges)}}
print(json.dumps(out))
"""


def _probe(hash_seed: str) -> dict:
    env = dict(os.environ, PYTHONHASHSEED=hash_seed)
    proc = subprocess.run(
        [sys.executable, "-c", PROBE.format(root=str(ROOT))],
        capture_output=True, text=True, env=env, timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_the_random_campus_is_identical_under_a_different_hash_seed() -> None:
    a, b = _probe("1"), _probe("987654")
    assert a == b, (
        "the synthetic graph changed shape between processes, so the seeded "
        "benchmark is not reproducible and the README's numbers depend on "
        "which run you are reading"
    )


def test_the_stitching_step_does_not_depend_on_set_iteration_order() -> None:
    """Guard the specific cause, so a future edit cannot reintroduce it."""
    # Check executable lines only: the comment above the fix quotes the bad
    # pattern on purpose, and a naive grep fails on its own explanation.
    offenders = [
        line.strip()
        for line in (ROOT / "bench.py").read_text(encoding="utf-8").splitlines()
        if not line.strip().startswith("#") and "next(iter(" in line
    ]
    assert not offenders, (
        "bench.py picks a node from set iteration order, which Python "
        "randomises per process - use min(seen) or sorted(seen)[0]: "
        f"{offenders}"
    )
