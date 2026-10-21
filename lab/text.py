"""Explicit text projection, source coordinates and lexical representations."""
from collections import Counter
import hashlib
import json
import math
import re
import unicodedata


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize(text):
    if not isinstance(text, str):
        raise ValueError("text_required")
    return unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))


def parse_source(format, source):
    if format == "markdown":
        body = normalize(source)
        match = re.search(r"^#\s+(.+)$", body, re.M)
        return (match[1].strip() if match else "Untitled"), body
    if format == "json":
        value = json.loads(source)
        if not isinstance(value, dict) or set(value) != {"title", "sections"}:
            raise ValueError("unsupported_json_shape")
        if not isinstance(value["title"], str) or not isinstance(value["sections"], list):
            raise ValueError("unsupported_json_shape")
        parts = ["# " + value["title"]]
        for section in value["sections"]:
            if not isinstance(section, dict) or set(section) != {"heading", "text"}:
                raise ValueError("unsupported_json_section")
            if not all(isinstance(section[k], str) for k in ["heading", "text"]):
                raise ValueError("unsupported_json_section")
            parts.append("## " + section["heading"] + "\n" + section["text"])
        return value["title"], normalize("\n\n".join(parts))
    raise ValueError("unsupported_format")


def chunks(body, size=220, overlap=40):
    if not 1 <= size <= 4096 or not 0 <= overlap < size:
        raise ValueError("invalid_chunk_window")
    headings = [(m.start(), m[2].strip()) for m in re.finditer(r"^(#{1,6})\s+(.+)$", body, re.M)]
    start, index = 0, 0
    while start < len(body):
        end = min(start + size, len(body))
        if end < len(body):
            boundary = body.rfind("\n\n", start + size // 2, end)
            if boundary > start:
                end = boundary + 2
        quote = body[start:end]
        heading = next((title for pos, title in reversed(headings) if pos <= start), "")
        yield {"index": index, "start": start, "end": end, "text": quote,
               "heading": heading, "sha256": digest(quote)}
        if end == len(body):
            break
        start = max(start + 1, end - overlap)
        index += 1


def terms(text):
    result = []
    for span in re.findall(r"[A-Za-z0-9_]+|[\u3400-\u9fff]+", normalize(text).lower()):
        if re.fullmatch(r"[\u3400-\u9fff]+", span):
            result.extend(span[i:i+2] for i in range(len(span)-1))
            if len(span) == 1:
                result.append(span)
        else:
            result.append(span)
    return result


class TermEncoder:
    identifier = "chinese-bigrams-ascii-terms-v1"
    minimum_score = 0.05

    def encode(self, texts, query=False):
        return [dict(Counter(terms(text))) for text in texts]


def cosine(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        numerator = sum(value * b.get(key, 0) for key, value in a.items())
        denominator = math.sqrt(sum(v*v for v in a.values()) * sum(v*v for v in b.values()))
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        numerator = sum(x*y for x, y in zip(a, b))
        denominator = math.sqrt(sum(v*v for v in a) * sum(v*v for v in b))
    else:
        raise ValueError("incompatible_vector_contract")
    return numerator / denominator if denominator else 0.0
