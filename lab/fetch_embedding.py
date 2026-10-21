"""Explicit optional model download, pinned commit and expected file SHA-256."""
import argparse
import hashlib
from pathlib import Path
import subprocess

REVISION = "75c43b069aac4d136ba6bc1122f995fedcfd2781"
FILES = {
    "model_quantized.onnx": ("onnx/model_quantized.onnx", "15b717c382bcb518ba457b93ea6850ede7f4f1cd8937454aa06972366cd19bcc"),
    "tokenizer.json": ("tokenizer.json", "48cea5d44424912a6fd1ea647bf4fe50b55ab8b1e5879c3275f80e339e8fae26"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path(".tools/models/bge-small-zh-v1.5"))
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    for name, (remote, expected) in FILES.items():
        destination = args.directory / name
        if not destination.is_file() or hashlib.sha256(destination.read_bytes()).hexdigest() != expected:
            temporary = destination.with_suffix(destination.suffix + ".part")
            url = f"https://huggingface.co/Xenova/bge-small-zh-v1.5/resolve/{REVISION}/{remote}"
            subprocess.run(["curl", "--fail", "--location", "--silent", "--show-error", "--max-time", "180",
                            "--max-filesize", "200000000", url, "--output", str(temporary)], check=True)
            if hashlib.sha256(temporary.read_bytes()).hexdigest() != expected:
                raise ValueError("model_download_hash_mismatch:" + name)
            temporary.replace(destination)
        print(name, destination.stat().st_size, expected)


if __name__ == "__main__":
    main()
