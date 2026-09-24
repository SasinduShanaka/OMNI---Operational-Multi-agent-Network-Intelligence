"""
build_index.py
Build or rebuild the OMNI knowledge indexes.

    python knowledge/build_index.py              # build every corpus
    python knowledge/build_index.py market_context   # build one

The vector store itself is not committed (see .gitignore), so run this
once after cloning and again whenever a document changes.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from knowledge.retriever import CORPORA, build_corpus, index_status


def main():

    requested = sys.argv[1:] or list(CORPORA)

    unknown = [name for name in requested if name not in CORPORA]

    if unknown:
        print(f"Unknown corpus: {', '.join(unknown)}")
        print(f"Available: {', '.join(CORPORA)}")
        return 1

    for corpus in requested:
        print(f"\nBuilding '{corpus}' — {CORPORA[corpus]['description']}")
        build_corpus(corpus)

    print("\nIndex status:")
    for corpus, state in index_status().items():
        mark = "ok  " if state["indexed"] else "MISSING"
        print(f"  {mark} {corpus}: {state['chunks']} chunks")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
