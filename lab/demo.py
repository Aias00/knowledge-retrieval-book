"""Actual SQLite ingestion/search/update/revocation/deletion experiment."""
import argparse
import json
from pathlib import Path
import tempfile

from .fixtures import populate
from .index import Context, Index
from .text import digest


def run():
    with tempfile.TemporaryDirectory(prefix="knowledge-demo-") as directory:
        index = Index(Path(directory)/"index.sqlite", chunk_size=80, overlap=16)
        populate(index)
        context = Context("acme", "alice")
        hits = index.search("住宿发票报销", context)
        answer = index.answer(hits, context)
        assert answer["state"] == "extractive" and any(e["doc_id"] == "travel" for e in answer["evidence"])
        for evidence in answer["evidence"]:
            assert digest(evidence["quote"]) == evidence["sha256"]
        stale = index.search("退款政策", context)
        update = index.upsert("acme", "refund", 2, "markdown", "# 退款政策\n\n客户购买商品后14天内可申请退款，需保留订单编号和付款凭证。", ["alice", "bob"])
        assert index.answer(stale, context)["state"] == "abstain"
        assert not index.search("30", context)
        updated = index.answer(index.search("退款政策", context), context)
        assert "14天" in updated["answer"]
        before_revoke = index.search("远程办公", context)
        acl_revision = index.status("acme", "remote")["acl_revision"]
        index.set_acl("acme", "remote", ["bob"], acl_revision)
        assert index.answer(before_revoke, context)["state"] == "abstain"
        assert all(h["doc_id"] != "remote" for h in index.search("远程办公", context))
        assert any(h["doc_id"] == "remote" for h in index.search("远程办公", Context("acme", "bob")))
        before_delete = [hit for hit in index.search("年假申请", context) if hit["doc_id"] == "leave"]
        index.delete("acme", "leave", 2)
        assert index.answer(before_delete, context)["state"] == "abstain"
        assert all(h["doc_id"] != "leave" for h in index.search("年假", context))
        try:
            index.upsert("acme", "leave", 1, "markdown", "# 年假\n旧内容", ["alice"])
        except ValueError as error:
            replay = str(error)
        else:
            raise AssertionError("old event resurrected deleted document")
        denied = [index.search(q, context) for q in ["SECRET-ACME-BOB", "SECRET-BETA", "zxqv-unrelated-token"]]
        assert all(not value for value in denied)
        result = {"kind": "real_sqlite_fts5_and_term_vectors_non_llm",
                  "initial_answer": answer, "version_update": update,
                  "old_30_day_fact_retrievable": False, "new_answer": updated,
                  "stale_revision_citation_rejected": True,
                  "revoked_alice_citation_rejected": True, "bob_access_preserved": True,
                  "deleted_citation_rejected": True, "stale_replay_error": replay,
                  "cross_tenant_and_private_results": [len(v) for v in denied],
                  "limitations": ["extractive answers, no LLM", "term vectors are not semantic embeddings",
                    "deletion is a live-index visibility guarantee, not backup/physical erasure",
                    "revocation cannot recall information already delivered"]}
        index.close()
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("lab/evidence/demo.json"))
    args = parser.parse_args()
    result = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
