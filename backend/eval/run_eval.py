"""Evaluate the live search system on a graded qrels file.

Reports Recall@K, Precision@R, MRR and nDCG@K, averaged over all queries.
Runs the full system (Azure embedding + Qdrant hybrid dense/BM25 + Cohere
rerank). Per-query results are printed so weak queries are easy to spot.

Usage:
    python -m eval.run_eval --qrels ../eval/qrels.jsonl --k 10
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from eval.metrics import (ndcg_at_k, precision_at_r, recall_at_k,
                          reciprocal_rank)
from index.qdrant_store import QdrantStore
from search.engine import SearchEngine


def load_qrels(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate search quality")
    parser.add_argument("--qrels", type=str, default="../eval/qrels.jsonl")
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--out", type=str, default=None,
                        help="Write a Markdown report to this path")
    args = parser.parse_args()

    qrels_path = (Path(__file__).resolve().parent.parent / args.qrels).resolve()
    qrels = load_qrels(qrels_path)
    if not qrels:
        raise SystemExit(f"No qrels found in {qrels_path}")

    engine = SearchEngine(QdrantStore())
    k = args.k

    rows = []  # (category, query, n_relevant, recall, pr, mrr, ndcg)
    sums = {"recall": 0.0, "pr": 0.0, "mrr": 0.0, "ndcg": 0.0}
    for row in qrels:
        relevant = set(row["relevant"])
        grades = {kk: float(vv) for kk, vv in row.get("grades", {}).items()}
        if not grades:
            grades = {doc_id: 1.0 for doc_id in relevant}

        resp = engine.search(row["query"], top_k=k)
        ranked = [h.email.id for h in resp.hits]

        rec = recall_at_k(ranked, relevant, k)
        pr = precision_at_r(ranked, relevant)
        mrr = reciprocal_rank(ranked, relevant)
        ndcg = ndcg_at_k(ranked, grades, k)
        sums["recall"] += rec
        sums["pr"] += pr
        sums["mrr"] += mrr
        sums["ndcg"] += ndcg
        rows.append((row.get("category", "Other"), row["query"],
                     len(relevant), rec, pr, mrr, ndcg))

    n = len(qrels)
    avg = {key: total / n for key, total in sums.items()}

    # Console summary (ASCII-safe so it never trips Windows code pages).
    print(f"{n} queries  |  metrics @ k={k}")
    print(f"Recall@{k}={avg['recall']:.3f}  Precision@R={avg['pr']:.3f}  "
          f"MRR={avg['mrr']:.3f}  nDCG@{k}={avg['ndcg']:.3f}")

    if args.out:
        out_path = (Path(__file__).resolve().parent.parent / args.out).resolve()
        _write_markdown(out_path, rows, avg, k, n)
        print(f"Wrote report -> {out_path}")


def _write_markdown(path, rows, avg, k: int, n: int) -> None:
    lines = [
        "# Search Quality Evaluation",
        "",
        f"System: Azure `text-embedding-3-large` + Qdrant hybrid "
        f"(dense + BM25, RRF) + Cohere rerank.  ",
        f"Dataset: {n} hand-labeled queries over real emails "
        f"(graded relevance 0/1/2).",
        "",
        "## Summary",
        "",
        "| Metric | Score |",
        "| --- | --- |",
        f"| Recall@{k} | {avg['recall']:.3f} |",
        f"| Precision@R | {avg['pr']:.3f} |",
        f"| MRR | {avg['mrr']:.3f} |",
        f"| nDCG@{k} | {avg['ndcg']:.3f} |",
        "",
        "## Per-query results",
    ]

    # Group rows by category, preserving first-seen order.
    categories: list[str] = []
    grouped: dict[str, list] = {}
    for r in rows:
        cat = r[0]
        if cat not in grouped:
            grouped[cat] = []
            categories.append(cat)
        grouped[cat].append(r)

    for cat in categories:
        members = grouped[cat]
        c_avg = {
            "recall": sum(r[3] for r in members) / len(members),
            "pr": sum(r[4] for r in members) / len(members),
            "mrr": sum(r[5] for r in members) / len(members),
            "ndcg": sum(r[6] for r in members) / len(members),
        }
        lines += [
            "",
            f"### {cat}",
            "",
            f"| Query | #rel | Recall@{k} | P@R | MRR | nDCG@{k} |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
        for _cat, q, nrel, rec, pr, mrr, ndcg in members:
            lines.append(
                f"| {q} | {nrel} | {rec:.3f} | {pr:.3f} | {mrr:.3f} | {ndcg:.3f} |")
        lines.append(
            f"| **Subtotal** | | **{c_avg['recall']:.3f}** | "
            f"**{c_avg['pr']:.3f}** | **{c_avg['mrr']:.3f}** | "
            f"**{c_avg['ndcg']:.3f}** |")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
