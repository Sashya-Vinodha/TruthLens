#!/usr/bin/env python3
"""Compatibility wrapper so ``python scripts/build_index.py`` keeps working.

It simply forwards to ``backend.app.indexer`` which contains the real
index-building logic (BM25 + FAISS + docs dump).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import indexer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build FAISS/BM25 indexes")
    parser.add_argument(
        "--docs",
        default="data/docs.json",
        help="Path to the JSON file containing input documents",
    )
    parser.add_argument(
        "--out-dir",
        default="backend/data",
        help="Directory where index artifacts (faiss, bm25, docs.pkl) are saved",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # ``indexer.main`` expects CLI args via sys.argv, so temporarily override.
    original_argv = sys.argv[:]
    sys.argv = [original_argv[0], "--docs", args.docs, "--out-dir", args.out_dir]
    try:
        indexer.main()
    finally:
        sys.argv = original_argv


if __name__ == "__main__":
    main()
