#!/usr/bin/env bash
# One command that runs everything a reviewer would run.
set -euo pipefail
cd "$(dirname "$0")"

echo "== tests =="
python -m pytest tests/ -q

echo
echo "== regenerating docs/ from the graph =="
python tools/build_usar_campus.py | head -2
python tools/build_usar_from_screenshot.py | tail -2
python gen_docs.py -c campuses/usar-east-campus.json
python gen_docs.py --docs-dir docs/sample-campus

echo
echo "== benchmarks (both campuses) =="
python bench.py > docs/bench-output.txt
echo "wrote docs/bench-output.txt (synthetic sample)"
python bench.py -c campuses/usar-east-campus.json > docs/bench-usar.txt
echo "wrote docs/bench-usar.txt (real campus)"

echo
echo "== before/after comparison page =="
python tools/make_comparison.py

echo
echo "== map audit: does every correction still hold? =="
python tools/audit_map.py > docs/audit-report.txt
tail -1 docs/audit-report.txt
echo
echo "echo "== walkthrough page =="
python tools/make_walkthrough.py
echo
echo "== smoke test 1: routing on the real campus ==""
python main.py route -c campuses/usar-east-campus.json --from gate_1 --to block_b
echo
echo "== smoke test 2: where BFS and Dijkstra disagree (sample campus) =="
python main.py compare --from sports --to library
echo
echo "ALL CHECKS PASSED"
