#!/usr/bin/env python3
"""Prepare a config-only source folder for the Q178 NInfer v3 GGUF importer.

The prior Q171 artifact was converted with an older schema. Reuse its exact frontend
resources and normalized model geometry, restore the current HF config fields, then
validate the resulting adapter config against the local GGUF before writing anything.
No model weights are copied here and no GPU is initialized.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

NINFER_SOURCE = Path("/tmp/q174-d/ninfer-src")
PRIOR_CONVERSION = Path(
    "/media/cristian/HDD extra/Modelos-eval/Q-20261027-VF-ITERATION-171/artifact/qwen4exp.ninfer.conversion.json"
)
PRIOR_ARTIFACT = Path(
    "/media/cristian/HDD extra/Modelos-eval/Q-20261027-VF-ITERATION-171/artifact/qwen4exp.ninfer"
)
GGUF_MODEL = Path(
    "/media/cristian/Disco local/Models/FlashNext-IQ2XS-ISTA-Strata-eval-20261012/IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf"
)
OUTPUT = Path(
    "/media/cristian/HDD extra/Modelos-eval/Q-20261028-VF-ITERATION-178/reconverted-v3/source-config"
)
RESOURCE_NAMES = (
    "tokenizer.json",
    "tokenizer_config.json",
    "chat_template.jinja",
    "generation_config.json",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    sys.path.insert(0, str(NINFER_SOURCE))
    from tools.artifact.reader import Artifact
    from tools.convert.qwen4_exp import text_config
    from tools.convert.qwen4_exp_gguf import validate
    from tools.convert.sources.gguf import GGUFFile

    if OUTPUT.exists():
        raise FileExistsError(f"refusing to overwrite {OUTPUT}")
    report = json.loads(PRIOR_CONVERSION.read_text(encoding="utf-8"))
    config = dict(report["components"]["text"]["config"])
    config["architectures"] = ["Qwen4ExpForCausalLM"]
    config.update({
        "model_type": "qwen4_exp_text",
        "hidden_act": "silu",
        "attention_bias": False,
        "mamba_ssm_dtype": "float32",
        "output_gate_type": "sigmoid",
        "indexer_kv_heads": 1,
        "seed": 1234,
    })
    rope = dict(config["rope_parameters"])
    rope["mrope_interleaved"] = True
    config["rope_parameters"] = rope
    normalized = text_config(config)
    if normalized["ple_layers"] != [1] or normalized["num_hidden_layers"] != 48:
        raise ValueError("reconstructed config does not describe full Flash-Next with PLE at block 1")

    with GGUFFile(GGUF_MODEL) as model:
        validate(model, normalized)

    OUTPUT.mkdir(parents=True)
    written: dict[str, dict[str, object]] = {}
    with Artifact(PRIOR_ARTIFACT) as artifact:
        for name in RESOURCE_NAMES:
            object_id = f"resource/text/{name}"
            data = artifact.read_object(object_id)
            if not data:
                raise ValueError(f"empty frontend resource: {object_id}")
            path = OUTPUT / name
            path.write_bytes(data)
            written[name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    config_path = OUTPUT / "config.json"
    config_bytes = (json.dumps(config, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    config_path.write_bytes(config_bytes)

    print(json.dumps({
        "status": "prepared_and_validated",
        "source_config": str(config_path),
        "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "source_gguf": str(GGUF_MODEL),
        "source_gguf_bytes": GGUF_MODEL.stat().st_size,
        "source_gguf_sha256": sha256(GGUF_MODEL),
        "prior_conversion_json_sha256": sha256(PRIOR_CONVERSION),
        "prior_artifact": str(PRIOR_ARTIFACT),
        "resources": written,
        "adapter_validation": {
            "architectures": normalized["architectures"],
            "num_hidden_layers": normalized["num_hidden_layers"],
            "num_experts": normalized["num_experts"],
            "ple_layers": normalized["ple_layers"],
            "layer_types": len(normalized["layer_types"]),
        },
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
