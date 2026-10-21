"""Optional real local BGE embedding using a pinned community ONNX export.

Original model: BAAI/bge-small-zh-v1.5. Quantized export: Xenova repository.
No model files are redistributed by this book. No cloud inference is called.
"""
import hashlib
import importlib.metadata
from pathlib import Path


class BGEEncoder:
    minimum_score = 0.40  # Demonstration cutoff, not a relevance probability.

    def __init__(self, directory):
        import numpy as np
        import onnxruntime as ort
        from tokenizers import Tokenizer
        root = Path(directory)
        model = root / "model_quantized.onnx"
        tokenizer = root / "tokenizer.json"
        hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [model, tokenizer]}
        self.identifier = "bge-zh-v15-onnx-quantized-cls512-instruction-v1:" + hashes[model.name] + ":" + hashes[tokenizer.name]
        self.metadata = {"original_model": "BAAI/bge-small-zh-v1.5",
            "original_revision": "7999e1d3359715c523056ef9478215996d62a620",
            "export": "Xenova/bge-small-zh-v1.5",
            "export_revision": "75c43b069aac4d136ba6bc1122f995fedcfd2781",
            "files_sha256": hashes, "pooling": "CLS", "normalization": "L2",
            "max_tokens": 512, "query_instruction": "为这个句子生成表示以用于检索相关文章：",
            "runtime": {name: importlib.metadata.version(name) for name in ["onnxruntime", "numpy", "tokenizers"]},
            "provider": "CPUExecutionProvider", "dimension": 512}
        self.np = np
        self.tokenizer = Tokenizer.from_file(str(tokenizer))
        self.tokenizer.enable_truncation(max_length=512)
        self.tokenizer.enable_padding()
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(model), sess_options=options, providers=["CPUExecutionProvider"])

    def encode(self, texts, query=False):
        if not texts:
            return []
        if query:
            texts = [self.metadata["query_instruction"] + text for text in texts]
        encoded = self.tokenizer.encode_batch(texts)
        inputs = {"input_ids": self.np.array([e.ids for e in encoded], dtype=self.np.int64),
                  "attention_mask": self.np.array([e.attention_mask for e in encoded], dtype=self.np.int64),
                  "token_type_ids": self.np.array([e.type_ids for e in encoded], dtype=self.np.int64)}
        required = {i.name for i in self.session.get_inputs()}
        output = self.session.run(None, {k: v for k, v in inputs.items() if k in required})[0]
        vectors = output[:, 0, :]
        norms = self.np.linalg.norm(vectors, axis=1, keepdims=True)
        if vectors.shape[1] != 512 or not self.np.isfinite(vectors).all() or (norms == 0).any():
            raise ValueError("invalid_embedding_output")
        return (vectors / norms).tolist()
