"""Per-query evaluation of a small authored fixture, not a model leaderboard."""
import argparse
import json
from pathlib import Path
import platform
import sqlite3
import tempfile
import time

from .fixtures import corpus, populate, queries
from .index import Context, Index


def evaluate(index, mode, rerank=True):
    rows, recall, reciprocal, negatives, negative_abstain = [], [], [], 0, 0
    for case in queries():
        start = time.monotonic()
        hits = index.search(case["query"], Context("acme", "alice"), limit=10, mode=mode, rerank=rerank)
        doc_ids = list(dict.fromkeys(h["doc_id"] for h in hits))[:3]
        rank = next((i for i, value in enumerate(doc_ids, 1) if value in case["relevant"]), None)
        if case["relevant"]:
            recall.append(len(set(doc_ids) & set(case["relevant"])) / len(case["relevant"]))
            reciprocal.append(1 / rank if rank else 0)
        else:
            negatives += 1
            negative_abstain += not hits
        assert all(h["tenant"] == "acme" and h["doc_id"] not in {"board", "health"} for h in hits)
        rows.append({**case, "top3_documents": doc_ids, "first_relevant_rank": rank,
                     "returned_chunks": len(hits), "wall_ms": round((time.monotonic()-start)*1000, 3)})
    return {"mode": mode, "rerank": rerank, "queries": len(rows),
            "positive_queries": len(recall), "recall_at_3": sum(recall)/len(recall),
            "mrr_at_3": sum(reciprocal)/len(reciprocal), "negative_queries": negatives,
            "negative_abstentions": negative_abstain, "access_violations": 0, "rows": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--onnx-model", type=Path)
    parser.add_argument("--output", type=Path, default=Path("lab/evidence/evaluation.json"))
    args = parser.parse_args()
    encoder, metadata = None, {"encoder": "character/ASCII term counts, not semantic embedding"}
    if args.onnx_model:
        from .embedding import BGEEncoder
        encoder = BGEEncoder(args.onnx_model)
        metadata = encoder.metadata
    with tempfile.TemporaryDirectory(prefix="knowledge-eval-") as directory:
        index = Index(Path(directory) / "index.sqlite", encoder=encoder, chunk_size=80, overlap=16)
        populate(index)
        reports = [evaluate(index, mode) for mode in ["lexical", "vector", "hybrid"]]
        index.close()
    result = {"kind": "small_authored_retrieval_fixture_not_a_business_or_model_benchmark",
              "python": platform.python_version(), "sqlite": sqlite3.sqlite_version,
              "documents": len(corpus()), "metadata": metadata, "reports": reports,
              "limitations": ["single authored corpus; no independent heldout population",
                "ONNX export is community quantization, not original full-precision weights",
                "embedding similarity is not a calibrated relevance probability",
                "CPU timings are local execution observations, not throughput benchmarks",
                "ACL result filtering is tested; timing/statistical side channels are not audited"]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps({"metadata": metadata, "results": [{k:v for k,v in r.items() if k != "rows"} for r in reports],
                      "output": str(args.output)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
