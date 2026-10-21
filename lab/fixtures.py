"""Versioned author-created documents and labels, not a business benchmark."""
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).parent / "data"
def read(name):
    manifest = json.loads((ROOT / "manifest.json").read_text())
    data = (ROOT / name).read_bytes()
    if hashlib.sha256(data).hexdigest() != manifest["sha256"][name]:
        raise ValueError("fixture_hash_mismatch:" + name)
    return json.loads(data)
def corpus():
    return read("corpus.json")
def queries():
    return read("queries.json")
def populate(index):
    return [index.upsert(**document) for document in corpus()]
