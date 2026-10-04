#!/usr/bin/env python3
"""
Campus Navigation System - entry point.

Examples
--------
    python main.py list
    python main.py route --from usar --to hostel_w --algo dijkstra
    python main.py compare --from sports --to library
    python main.py map --from sports --to library --out docs/route.svg
    python main.py demo
"""

import sys

from campus_nav.cli import main

if __name__ == "__main__":
    sys.exit(main())
