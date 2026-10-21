from pathlib import Path
import copy
import json
import tempfile
import unittest

from lab.fixtures import corpus, populate
from lab.index import Context, Index
from lab.text import TermEncoder, chunks, cosine, digest, normalize, parse_source, terms


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)/"index.sqlite"
        self.index = Index(self.path, chunk_size=80, overlap=16)
        self.addCleanup(self.index.close)
        populate(self.index)
        self.alice = Context("acme", "alice")
        self.bob = Context("acme", "bob")

    def hits(self, doc_id, query, context=None):
        return [h for h in self.index.search(query, context or self.alice, limit=100) if h["doc_id"] == doc_id]

    def test_actual_fts5_table_returns_ranked_rows(self):
        rows = self.index.db.execute("SELECT rowid,bm25(chunks_fts) FROM chunks_fts WHERE chunks_fts MATCH ?", ('"住宿"',)).fetchall()
        self.assertGreater(len(rows), 0)
        result = self.index.search("住宿发票", self.alice, mode="lexical")
        self.assertEqual(result[0]["doc_id"], "travel")
        self.assertIn("lexical", result[0]["channels"])

    def test_markdown_and_json_projection_and_exact_coordinates(self):
        title, body = parse_source("json", json.dumps({"title":"标题","sections":[{"heading":"小节","text":"第一行\r\n第二行"}]}))
        self.assertEqual(title, "标题")
        self.assertNotIn("\r", body)
        for piece in chunks(body, 12, 3):
            self.assertEqual(body[piece["start"]:piece["end"]], piece["text"])
            self.assertEqual(digest(piece["text"]), piece["sha256"])

    def test_chunk_overlap_is_bounded_and_covers_oversized_paragraph(self):
        body = "一二三四五六七八九十"*15
        pieces = list(chunks(body, 30, 5))
        self.assertEqual(pieces[0]["start"], 0)
        self.assertEqual(pieces[-1]["end"], len(body))
        self.assertTrue(all(len(p["text"]) <= 30 for p in pieces))
        self.assertTrue(all(a["end"] >= b["start"] for a,b in zip(pieces,pieces[1:])))

    def test_chinese_terms_are_explicit_not_semantic_embedding(self):
        self.assertIn("住宿", terms("住宿500元"))
        self.assertIn("500", terms("住宿500元"))
        a,b=TermEncoder().encode(["酒店住宿","旅馆睡觉"])
        self.assertEqual(cosine(a,b), 0)

    def test_hybrid_exposes_channels_and_rrf_arithmetic(self):
        hits=self.index.search("住宿发票",self.alice)
        top=hits[0]
        self.assertEqual(top["doc_id"],"travel")
        self.assertAlmostEqual(top["rrf"],sum(1/(60+v["rank"]) for v in top["channels"].values()))

    def test_vector_search_prefilters_private_documents(self):
        for mode in ["lexical","vector","hybrid"]:
            with self.subTest(mode=mode):
                hits=self.index.search("并购谈判猎户座健康福利",self.alice,mode=mode,limit=100)
                self.assertTrue(all(h["doc_id"] not in {"board","health"} for h in hits))
                self.assertTrue(all("SECRET" not in h["text"] for h in hits))
                self.assertGreater(len(self.hits("board","并购谈判",self.bob)),0)

    def test_same_document_id_in_other_tenant_cannot_cross_boundary(self):
        hits=self.index.search("酒店限额",self.alice,limit=100)
        self.assertTrue(all(h["tenant"]=="acme" for h in hits))
        beta=self.index.search("酒店限额",Context("beta","alice"))
        self.assertTrue(all(h["tenant"]=="beta" for h in beta))
        self.assertTrue(any("900元" in h["text"] for h in beta))

    def test_missing_context_fails_closed_and_unknown_tenant_sees_nothing(self):
        with self.assertRaises(PermissionError):self.index.search("退款",None)
        self.assertEqual(self.index.search("退款",Context("unknown","alice")),[])

    def test_match_operators_and_quotes_are_not_executable_query_syntax(self):
        self.index.search('" OR 住宿 NEAR(secret) -退款 *',self.alice)
        self.assertEqual(self.index.db.execute("SELECT count(*) FROM docs").fetchone()[0],8)

    def test_idempotent_ingestion_and_conflicting_revision(self):
        document=corpus()[0]
        count=self.index.db.execute("SELECT count(*) FROM chunks").fetchone()[0]
        self.assertEqual(self.index.upsert(**document)["state"],"unchanged")
        self.assertEqual(self.index.db.execute("SELECT count(*) FROM chunks").fetchone()[0],count)
        with self.assertRaises(ValueError):self.index.upsert(**{**document,"source":"# changed"})

    def test_incremental_update_removes_old_fact_and_invalidates_citation(self):
        old=self.hits("refund","退款政策")
        self.index.upsert("acme","refund",2,"markdown","# 退款政策\n\n购买后14天内申请退款。",["alice"])
        self.assertEqual(self.index.answer(old,self.alice)["state"],"abstain")
        self.assertEqual(self.index.search("30",self.alice),[])
        fresh=self.index.answer(self.hits("refund","退款政策"),self.alice)
        self.assertIn("14天",fresh["answer"])

    def test_policy_revocation_rechecks_cached_hits_and_keeps_other_user(self):
        old=self.hits("remote","远程办公")
        version=self.index.status("acme","remote")["acl_revision"]
        self.index.set_acl("acme","remote",["bob"],version)
        self.assertEqual(self.index.answer(old,self.alice)["state"],"abstain")
        self.assertEqual(self.hits("remote","远程办公"),[])
        self.assertGreater(len(self.hits("remote","远程办公",self.bob)),0)

    def test_new_content_event_cannot_regrant_old_acl(self):
        version=self.index.status("acme","remote")["acl_revision"]
        self.index.set_acl("acme","remote",["bob"],version)
        doc=next(d for d in corpus() if d["doc_id"]=="remote")
        self.index.upsert(**{**doc,"revision":2})
        self.assertEqual(self.hits("remote","远程办公"),[])

    def test_stale_acl_compare_and_swap_is_rejected(self):
        self.index.set_acl("acme","refund",["bob"],1)
        with self.assertRaises(ValueError):self.index.set_acl("acme","refund",["alice"],1)
        self.assertEqual(self.hits("refund","退款政策"),[])

    def test_empty_acl_denies_and_wildcard_is_tenant_scoped(self):
        self.index.upsert("acme","empty",1,"markdown","# 独占口令\nSENSITIVE-EMPTY",[])
        self.assertEqual(self.hits("empty","SENSITIVE-EMPTY"),[])
        self.assertGreater(len(self.hits("support","售后保修",Context("acme","charlie"))),0)
        self.assertEqual(self.index.search("售后保修",Context("beta","charlie")),[])

    def test_delete_clears_live_index_and_rejects_old_or_implicit_restore(self):
        old=self.hits("leave","年假申请")
        self.index.delete("acme","leave",2)
        self.assertEqual(self.index.answer(old,self.alice)["state"],"abstain")
        self.assertEqual(self.hits("leave","年假申请"),[])
        doc=next(d for d in corpus() if d["doc_id"]=="leave")
        with self.assertRaises(ValueError):self.index.upsert(**doc)
        with self.assertRaises(ValueError):self.index.upsert(**{**doc,"revision":3})
        self.assertEqual(self.index.status("acme","leave")["body"],"")
        self.index.upsert(**{**doc,"revision":3},restore=True)
        self.assertGreater(len(self.hits("leave","年假申请")),0)

    def test_citation_quote_is_read_from_current_database_not_caller_payload(self):
        hits=self.hits("refund","退款政策")
        hits[0]["text"]="FORGED ANSWER"
        result=self.index.answer(hits,self.alice)
        self.assertNotIn("FORGED",result["answer"])
        evidence=result["evidence"][0]
        self.assertEqual(digest(evidence["quote"]),evidence["sha256"])

    def test_cross_principal_hit_reuse_is_rejected(self):
        bob=self.hits("board","并购谈判",self.bob)
        self.assertEqual(self.index.answer(bob,self.alice)["state"],"abstain")

    def test_parse_failure_rolls_back_without_changing_existing_projection(self):
        old=self.index.status("acme","refund")
        with self.assertRaises((ValueError,json.JSONDecodeError)):
            self.index.upsert("acme","refund",2,"json",'{bad json}',["alice"])
        self.assertEqual(self.index.status("acme","refund"),old)

    def test_empty_or_invalid_window_is_rejected(self):
        with self.assertRaises(ValueError):list(chunks("abc",10,10))
        with self.assertRaises(ValueError):self.index.search("",self.alice)
        with self.assertRaises(ValueError):self.index.search("a"*1025,self.alice)

    def test_encoder_or_chunk_contract_change_requires_rebuild(self):
        with self.assertRaises(ValueError):Index(self.path,chunk_size=81,overlap=16)

    def test_unknown_query_abstains_and_answer_is_explicitly_non_llm(self):
        hits=self.index.search("zxqv-unrelated-token",self.alice)
        self.assertEqual(hits,[])
        self.assertEqual(self.index.answer(hits,self.alice),{"state":"abstain","non_llm":True,
            "answer":"没有当前权限下可核查的证据。","evidence":[]})


if __name__=="__main__":unittest.main()
