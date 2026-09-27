import hashlib
import json
import pathlib
import re
import subprocess
import time


ROOT = pathlib.Path(__file__).resolve().parent
RUNTIME = pathlib.Path(r"D:\Models\llamacpp\bench-runtime\b10964\unpacked")
PPL = RUNTIME / "llama-perplexity.exe"
CORPUS = pathlib.Path(r"C:\Users\cristian\Models\llamacpp\benchmark-data\mixedweb-v1.txt")
MODELS = {
    "agention-ap-q3-k-xl": pathlib.Path(r"D:\Models\llamacpp\Qwen3.8-27B-AP-GGUF\Qwen3.8-27B-AP-Q3_K_XL.gguf"),
    "unsloth-ud-q3-k-xl": pathlib.Path(r"D:\Models\llamacpp\Qwen3.8-27B-UD-Q3_K_XL-benchmark\Qwen3.8-27B-UD-Q3_K_XL.gguf"),
    "byteshape-iq4-xs": pathlib.Path(r"C:\models\Qwen3.8-27B-ByteShape-IQ4_XS\Qwen3.8-27B-IQ4_XS-3.84bpw.gguf"),
}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    md5 = hashlib.md5(CORPUS.read_bytes()).hexdigest()
    if md5 != "51e0045e8cabf37922aa82766a25b7b4":
        raise SystemExit(f"unexpected mixedweb md5: {md5}")
    results = []
    common = ["-f", str(CORPUS), "-c", "2048", "--chunks", "60", "-b", "2048", "-ngl", "999", "-dev", "CUDA1", "-sm", "none", "-mg", "0"]
    for name, model in MODELS.items():
        log_path = ROOT / f"ppl-mixedweb-{name}-cuda1.txt"
        command = [str(PPL), "-m", str(model), *common]
        start = time.perf_counter()
        with log_path.open("wb") as log:
            proc = subprocess.run(
                command,
                cwd=RUNTIME,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        elapsed = round(time.perf_counter() - start, 3)
        output = log_path.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"Final estimate: PPL = ([0-9.]+) \+/- ([0-9.]+)", output)
        if proc.returncode != 0 or not match:
            raise SystemExit(f"{name} failed ({proc.returncode}); inspect {log_path}")
        results.append(
            {
                "name": name,
                "model": str(model),
                "model_bytes": model.stat().st_size,
                "model_sha256": sha256(model),
                "command": command,
                "log": str(log_path),
                "exit_code": proc.returncode,
                "elapsed_seconds": elapsed,
                "ppl": float(match.group(1)),
                "ppl_error": float(match.group(2)),
            }
        )
        print(f"{name}: PPL {match.group(1)} +/- {match.group(2)} in {elapsed}s")
    manifest = {
        "dataset": {
            "name": "agentionai/quant-fidelity-corpora:mixedweb-v1.txt",
            "revision": "e71c458859813276ba2881ace8e25f2b792abefe",
            "license": "ODC-By-1.0; text derived from FineWeb/CommonCrawl",
            "url": "https://huggingface.co/datasets/agentionai/quant-fidelity-corpora",
            "path": str(CORPUS),
            "bytes": CORPUS.stat().st_size,
            "md5": md5,
            "sha256": sha256(CORPUS),
        },
        "runtime": {
            "build": "llama.cpp b29c606e2 (10964)",
            "perplexity_binary": str(PPL),
            "device": "CUDA1, one RTX 3090",
            "parameters": {"ctx": 2048, "chunks": 60, "batch": 2048, "gpu_layers": 999, "split_mode": "none", "main_gpu": 0},
        },
        "results": results,
    }
    out = ROOT / "ppl-mixedweb-manifest.json"
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
