"""SQLite FTS5, local vectors, ACL prefilter and citation revalidation."""
from contextlib import contextmanager
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sqlite3
import threading

from .text import TermEncoder, chunks, cosine, digest, parse_source, terms


@dataclass(frozen=True)
class Context:
    tenant: str
    principal: str


class Index:
    def __init__(self, path, encoder=None, chunk_size=220, overlap=40):
        list(chunks("", chunk_size, overlap))
        self.encoder = encoder or TermEncoder()
        self.chunk_size, self.overlap = chunk_size, overlap
        self.lock = threading.RLock()
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS docs(
          pk INTEGER PRIMARY KEY,tenant TEXT NOT NULL,doc_id TEXT NOT NULL,
          revision INTEGER NOT NULL,acl_revision INTEGER NOT NULL,
          title TEXT NOT NULL,body TEXT NOT NULL,sha256 TEXT NOT NULL,
          deleted INTEGER NOT NULL DEFAULT 0,UNIQUE(tenant,doc_id));
        CREATE TABLE IF NOT EXISTS acl(doc_pk INTEGER REFERENCES docs(pk),principal TEXT,
          PRIMARY KEY(doc_pk,principal));
        CREATE TABLE IF NOT EXISTS chunks(
          pk INTEGER PRIMARY KEY,doc_pk INTEGER REFERENCES docs(pk),number INTEGER,
          start INTEGER,end INTEGER,text TEXT,heading TEXT,sha256 TEXT,vector TEXT,
          UNIQUE(doc_pk,number));
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(terms);
        """)
        existing = self.db.execute("SELECT value FROM meta WHERE key='encoder'").fetchone()
        contract = json.dumps({"encoder": self.encoder.identifier, "chunk_size": chunk_size,
                               "overlap": overlap}, sort_keys=True)
        if existing and existing[0] != contract:
            self.db.close()
            raise ValueError("index_projection_contract_changed_rebuild_required")
        self.db.execute("INSERT OR IGNORE INTO meta VALUES('encoder',?)", (contract,))
        self.db.commit()

    @contextmanager
    def transaction(self, write=False):
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            try:
                yield
                self.db.commit()
            except BaseException:
                self.db.rollback()
                raise

    @staticmethod
    def _identity(value):
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", value):
            raise ValueError("invalid_identity")

    @staticmethod
    def _principals(values):
        if not isinstance(values, list) or any(not isinstance(v, str) or not v for v in values):
            raise ValueError("explicit_acl_list_required")
        return sorted(set(values))

    def _doc(self, tenant, doc_id):
        return self.db.execute("SELECT * FROM docs WHERE tenant=? AND doc_id=?", (tenant, doc_id)).fetchone()

    def _remove_chunks(self, doc_pk):
        ids = [r[0] for r in self.db.execute("SELECT pk FROM chunks WHERE doc_pk=?", (doc_pk,))]
        self.db.executemany("DELETE FROM chunks_fts WHERE rowid=?", [(pk,) for pk in ids])
        self.db.execute("DELETE FROM chunks WHERE doc_pk=?", (doc_pk,))

    def upsert(self, tenant, doc_id, revision, format, source, acl, restore=False):
        self._identity(tenant); self._identity(doc_id)
        principals = self._principals(acl)
        if type(restore) is not bool:
            raise ValueError("explicit_restore_boolean_required")
        if type(revision) is not int or revision < 1:
            raise ValueError("positive_revision_required")
        title, body = parse_source(format, source)
        digest_value = digest(body)
        pieces = list(chunks(body, self.chunk_size, self.overlap))
        vectors = self.encoder.encode([p["text"] for p in pieces])
        if len(vectors) != len(pieces):
            raise ValueError("encoder_result_count_mismatch")
        with self.transaction(write=True):
            old = self._doc(tenant, doc_id)
            if old:
                if revision == old["revision"] and digest_value == old["sha256"] and not old["deleted"]:
                    return {"state": "unchanged", "revision": revision}
                if revision <= old["revision"]:
                    raise ValueError("stale_or_conflicting_revision")
                if old["deleted"] and not restore:
                    raise ValueError("deleted_document_requires_explicit_restore")
                doc_pk = old["pk"]
                self._remove_chunks(doc_pk)
                self.db.execute("UPDATE docs SET revision=?,title=?,body=?,sha256=?,deleted=0 WHERE pk=?",
                                (revision, title, body, digest_value, doc_pk))
                # Content events never regrant a revoked ACL. Only explicit
                # restoration or the separate CAS policy API can change it.
                if old["deleted"]:
                    self.db.executemany("INSERT INTO acl VALUES(?,?)", [(doc_pk, p) for p in principals])
                    self.db.execute("UPDATE docs SET acl_revision=acl_revision+1 WHERE pk=?", (doc_pk,))
            else:
                cursor = self.db.execute("INSERT INTO docs(tenant,doc_id,revision,acl_revision,title,body,sha256) VALUES(?,?,?,1,?,?,?)",
                                         (tenant, doc_id, revision, title, body, digest_value))
                doc_pk = cursor.lastrowid
                self.db.executemany("INSERT INTO acl VALUES(?,?)", [(doc_pk, p) for p in principals])
            for piece, vector in zip(pieces, vectors):
                encoded = json.dumps(vector, ensure_ascii=False, allow_nan=False)
                cursor = self.db.execute("INSERT INTO chunks(doc_pk,number,start,end,text,heading,sha256,vector) VALUES(?,?,?,?,?,?,?,?)",
                    (doc_pk, piece["index"], piece["start"], piece["end"], piece["text"], piece["heading"], piece["sha256"], encoded))
                self.db.execute("INSERT INTO chunks_fts(rowid,terms) VALUES(?,?)", (cursor.lastrowid, " ".join(terms(piece["text"]))))
            return {"state": "indexed", "revision": revision, "chunks": len(pieces), "sha256": digest_value}

    def set_acl(self, tenant, doc_id, principals, expected_acl_revision):
        principals = self._principals(principals)
        if type(expected_acl_revision) is not int or expected_acl_revision < 1:
            raise ValueError("positive_acl_revision_required")
        with self.transaction(write=True):
            old = self._doc(tenant, doc_id)
            if not old or old["deleted"]:
                raise ValueError("document_not_live")
            if expected_acl_revision != old["acl_revision"]:
                raise ValueError("stale_acl_revision")
            self.db.execute("DELETE FROM acl WHERE doc_pk=?", (old["pk"],))
            self.db.executemany("INSERT INTO acl VALUES(?,?)", [(old["pk"], p) for p in principals])
            self.db.execute("UPDATE docs SET acl_revision=acl_revision+1 WHERE pk=?", (old["pk"],))
            return old["acl_revision"] + 1

    def delete(self, tenant, doc_id, revision):
        with self.transaction(write=True):
            old = self._doc(tenant, doc_id)
            if not old or type(revision) is not int or revision <= old["revision"]:
                raise ValueError("delete_requires_new_revision")
            self._remove_chunks(old["pk"])
            self.db.execute("DELETE FROM acl WHERE doc_pk=?", (old["pk"],))
            self.db.execute("UPDATE docs SET revision=?,acl_revision=acl_revision+1,body='',deleted=1 WHERE pk=?", (revision, old["pk"]))

    @staticmethod
    def _context(context):
        if not isinstance(context, Context):
            raise PermissionError("trusted_context_required")
        Index._identity(context.tenant); Index._identity(context.principal)

    def search(self, query, context, limit=5, mode="hybrid", rerank=True):
        self._context(context)
        if not isinstance(query, str) or not 0 < len(query) <= 1024:
            raise ValueError("bounded_query_required")
        if mode not in {"lexical", "vector", "hybrid"} or not 1 <= limit <= 100:
            raise ValueError("invalid_search_options")
        qterms = list(dict.fromkeys(terms(query)))[:64]
        if not qterms:
            return []
        qvector = self.encoder.encode([query], query=True)[0] if mode != "lexical" else None
        with self.transaction():
            allowed_sql = """FROM chunks c JOIN docs d ON c.doc_pk=d.pk
            WHERE d.tenant=? AND d.deleted=0 AND EXISTS(
              SELECT 1 FROM acl a WHERE a.doc_pk=d.pk AND a.principal IN(?,'*'))"""
            params = (context.tenant, context.principal)
            columns = "c.*,d.tenant,d.doc_id,d.revision,d.acl_revision,d.title,d.sha256 AS doc_sha256"
            allowed = {r["pk"]: dict(r) for r in self.db.execute("SELECT " + columns + " " + allowed_sql, params)}
            lexical, vector = [], []
            if mode != "vector":
                match = " OR ".join('"' + term.replace('"', '""') + '"' for term in qterms)
                lexical_sql = """SELECT c.pk,bm25(chunks_fts) AS rank FROM chunks_fts
                JOIN chunks c ON c.pk=chunks_fts.rowid JOIN docs d ON c.doc_pk=d.pk
                WHERE chunks_fts MATCH ? AND d.tenant=? AND d.deleted=0
                AND EXISTS(SELECT 1 FROM acl a WHERE a.doc_pk=d.pk AND a.principal IN(?,'*'))
                ORDER BY rank,c.pk LIMIT 100"""
                lexical = [(r["pk"], r["rank"]) for r in self.db.execute(lexical_sql, (match, *params))]
            if mode != "lexical":
                for pk, row in allowed.items():
                    similarity = cosine(qvector, json.loads(row["vector"]))
                    if similarity >= self.encoder.minimum_score:
                        vector.append((pk, similarity))
                vector.sort(key=lambda x: (-x[1], x[0]))
                vector = vector[:100]
            fused = {}
            for channel, ranked in [("lexical", lexical), ("vector", vector)]:
                for rank, (pk, raw_score) in enumerate(ranked, 1):
                    value = fused.setdefault(pk, {"rrf": 0.0, "channels": {}})
                    value["rrf"] += 1 / (60 + rank)
                    value["channels"][channel] = {"rank": rank, "score": raw_score}
            hits = []
            for pk, extra in fused.items():
                row = allowed[pk]
                title_overlap = len(set(qterms) & set(terms(row["title"]))) / len(qterms)
                hits.append({"chunk_pk": pk, "tenant": row["tenant"], "doc_id": row["doc_id"],
                    "revision": row["revision"], "acl_revision": row["acl_revision"],
                    "doc_sha256": row["doc_sha256"], "start": row["start"], "end": row["end"],
                    "text": row["text"], "sha256": row["sha256"], "heading": row["heading"],
                    "title": row["title"], "rrf": extra["rrf"], "channels": extra["channels"],
                    "title_overlap": title_overlap, "principal": context.principal})
            hits.sort(key=lambda h: (-(h["title_overlap"] if rerank else 0), -h["rrf"], h["chunk_pk"]))
            return hits[:limit]

    def answer(self, hits, context, limit=2):
        self._context(context)
        if type(limit) is not int or not 1 <= limit <= 10:
            raise ValueError("invalid_answer_limit")
        evidence = []
        with self.transaction():
            for hit in hits:
                if hit["tenant"] != context.tenant or hit["principal"] != context.principal:
                    continue
                doc = self._doc(context.tenant, hit["doc_id"])
                permitted = doc and self.db.execute("SELECT 1 FROM acl WHERE doc_pk=? AND principal IN(?,'*')", (doc["pk"], context.principal)).fetchone()
                if (not permitted or doc["deleted"] or doc["revision"] != hit["revision"] or
                    doc["acl_revision"] != hit["acl_revision"] or doc["sha256"] != hit["doc_sha256"]):
                    continue
                piece = self.db.execute("SELECT * FROM chunks WHERE pk=? AND doc_pk=?", (hit["chunk_pk"], doc["pk"])).fetchone()
                if not piece or piece["sha256"] != hit["sha256"] or piece["text"] != doc["body"][piece["start"]:piece["end"]]:
                    continue
                if any(e["doc_id"] == doc["doc_id"] and e["revision"] == doc["revision"] and
                       max(e["start"], piece["start"]) < min(e["end"], piece["end"]) for e in evidence):
                    continue
                evidence.append({"doc_id": doc["doc_id"], "revision": doc["revision"],
                    "start": piece["start"], "end": piece["end"], "sha256": piece["sha256"],
                    "quote": piece["text"]})
                if len(evidence) >= limit:
                    break
        return {"state": "extractive" if evidence else "abstain", "non_llm": True,
                "answer": "\n\n".join(e["quote"] for e in evidence) if evidence else "没有当前权限下可核查的证据。",
                "evidence": evidence}

    def status(self, tenant, doc_id):
        with self.lock:
            row = self._doc(tenant, doc_id)
            return dict(row) if row else None

    def close(self):
        self.db.close()
