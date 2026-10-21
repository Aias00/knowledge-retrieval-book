import math
import os
from pathlib import Path
import tempfile
import unittest

from lab.fixtures import populate
from lab.index import Context, Index


@unittest.skipUnless(os.environ.get("BGE_MODEL_DIR"), "optional pinned model not configured")
class RealLocalEmbeddingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from lab.embedding import BGEEncoder
        cls.encoder = BGEEncoder(os.environ["BGE_MODEL_DIR"])

    def test_actual_onnx_vectors_have_expected_dimension_and_l2_norm(self):
        vectors = self.encoder.encode(["旅馆住宿发票", "员工在家办公"])
        self.assertEqual(len(vectors), 2)
        for vector in vectors:
            self.assertEqual(len(vector), 512)
            self.assertTrue(all(math.isfinite(v) for v in vector))
            self.assertAlmostEqual(sum(v*v for v in vector), 1, places=5)

    def test_real_embedding_search_still_obeys_acl_and_tenant_filter(self):
        with tempfile.TemporaryDirectory() as directory:
            index = Index(Path(directory)/"bge.sqlite",encoder=self.encoder,chunk_size=80,overlap=16)
            try:
                populate(index)
                hits=index.search("旅馆住一夜能花多少钱",Context("acme","alice"),mode="vector")
                self.assertEqual(hits[0]["doc_id"],"travel")
                private=index.search("并购董事会秘密预算",Context("acme","alice"),mode="vector",limit=100)
                self.assertTrue(all(h["tenant"]=="acme" and h["doc_id"] not in {"board","health"} for h in private))
            finally:index.close()


if __name__=="__main__":unittest.main()
