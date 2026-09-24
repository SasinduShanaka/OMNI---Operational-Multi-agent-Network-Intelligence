"""
eval_rag.py
Retrieval evaluation for the OMNI knowledge corpora.

Measures hit-rate@k: for a question with a known answer, does the
right document come back in the top k? Retrieval quality is measured
separately from answer quality on purpose — if the wrong passage is
retrieved, no amount of prompting fixes the answer.

    python knowledge/eval_rag.py
    python knowledge/eval_rag.py --k 1
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from knowledge.retriever import search


# Each case: question, corpus, the doc_id that should answer it.
# Questions are deliberately phrased the way a planner would ask,
# not in the wording used by the document.

CASES = [
    # --- production SOPs -------------------------------------------------
    ("How many pieces do we inspect for a 4,000 unit order?",              "production_sops", "SOP-QA-01"),
    ("Can we start final inspection when half the lot is packed?",         "production_sops", "SOP-QA-01"),
    ("How much time do we lose switching Line 3 from shirts to t-shirts?", "production_sops", "SOP-PR-02"),
    ("Who approves a long changeover?",                                    "production_sops", "SOP-PR-02"),
    ("How long does denim need to rest before we cut it?",                 "production_sops", "SOP-PR-03"),
    ("What shrinkage allowance applies to fleece?",                        "production_sops", "SOP-PR-03"),
    ("Why can't we push a line past 85 percent?",                          "production_sops", "SOP-PR-04"),
    ("How many units a day can 30 operators make of a hoodie?",            "production_sops", "SOP-PR-04"),
    ("How much overtime are we allowed to plan?",                          "production_sops", "SOP-PR-04"),
    ("Is a loose thread a major or minor defect?",                         "production_sops", "SOP-QA-05"),
    ("What happens when a broken needle is detected?",                     "production_sops", "SOP-QA-05"),
    ("How many garments per carton for knits?",                            "production_sops", "SOP-QA-06"),
    ("Can finishing keep up with a t-shirt line?",                         "production_sops", "SOP-QA-06"),

    # --- market context --------------------------------------------------
    ("Why does polo demand spike in June?",                                "market_context",  "MKT-BUY-01"),
    ("When does Northwind confirm quantities?",                            "market_context",  "MKT-BUY-01"),
    ("Is the drop in formal shirt demand in May a real decline?",          "market_context",  "MKT-BUY-02"),
    ("Is the denim programme going to keep growing?",                      "market_context",  "MKT-BUY-02"),
    ("Why is the sportswear account growing so fast?",                     "market_context",  "MKT-BUY-03"),
    ("What is the risk with the Meridian account?",                        "market_context",  "MKT-BUY-03"),
    ("Will cotton get cheaper this year?",                                 "market_context",  "MKT-RAW-01"),
    ("Why are buyers ordering more often in smaller quantities?",          "market_context",  "MKT-RAW-01"),
    ("Which months are quietest for export shipping?",                     "market_context",  "MKT-SEA-01"),
    ("Does the April holiday affect our capacity?",                        "market_context",  "MKT-SEA-01"),
]


def evaluate(k: int = 3, verbose: bool = True) -> dict:

    by_corpus = {}
    misses = []

    for question, corpus, expected in CASES:

        hits = search(question, corpus, k=k)
        retrieved = [hit.get("doc_id") for hit in hits]
        hit = expected in retrieved

        stats = by_corpus.setdefault(corpus, {"total": 0, "hits": 0})
        stats["total"] += 1
        stats["hits"] += 1 if hit else 0

        if not hit:
            misses.append((question, expected, retrieved))

        if verbose:
            mark = "PASS" if hit else "MISS"
            print(f"  [{mark}] {question}")
            if not hit:
                print(f"         expected {expected}, got {retrieved or 'nothing above the distance cut-off'}")

    total = sum(stats["total"] for stats in by_corpus.values())
    hits_total = sum(stats["hits"] for stats in by_corpus.values())

    return {
        "k": k,
        "total": total,
        "hits": hits_total,
        "hit_rate": round(hits_total / total, 3) if total else 0,
        "by_corpus": by_corpus,
        "misses": misses,
    }


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=3, help="how many passages count as a hit")
    args = parser.parse_args()

    print(f"Retrieval evaluation — hit-rate@{args.k}\n")

    report = evaluate(k=args.k)

    print("\nResults")
    for corpus, stats in report["by_corpus"].items():
        rate = stats["hits"] / stats["total"]
        print(f"  {corpus:18} {stats['hits']}/{stats['total']}  ({rate:.0%})")

    print(f"\n  overall hit-rate@{args.k}: {report['hit_rate']:.0%} "
          f"({report['hits']}/{report['total']})")

    return 0 if report["hit_rate"] == 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
