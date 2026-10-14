---
license: apache-2.0
base_model: caiovicentino1/Ekbasis-27B
base_model_relation: quantized
library_name: transformers
pipeline_tag: text-classification
inference: false
tags:
- world-model
- consequence-model
- agent-safety
- ai-agents
- git
- calibration
- typed-decisions
- openinterp
- image-classification
- multimodal
- compressed-tensors
- vllm
- gptq
- int4
---

# Ekbasis-27B-INT4

![Ekbasis overview: git consequences against Claude and Qwen, the git guard on fresh real repositories, and speed against a reasoning model](https://huggingface.co/caiovicentino1/Ekbasis-27B/resolve/main/assets/ekbasis_launch.png)

**Papers:** [Look When Unsure, Check When Sure](https://doi.org/10.5281/zenodo.23146970) · DOI [10.5281/zenodo.23146970](https://doi.org/10.5281/zenodo.23146970) · [When Does a Consequence Model Make AI Agents Safer?](https://doi.org/10.5281/zenodo.23197341) · DOI [10.5281/zenodo.23197341](https://doi.org/10.5281/zenodo.23197341) · **Code:** [github.com/OpenInterpretability/ekbasis](https://github.com/OpenInterpretability/ekbasis) · **Site:** [openinterp.org/ekbasis](https://openinterp.org/ekbasis)

**INT4 build of [Ekbasis-27B](https://huggingface.co/caiovicentino1/Ekbasis-27B)**, an open world model for
agents: given the current state and an action, it predicts what the action will do — will this lose work? will it
fail? what will X be afterwards? — as calibrated, typed answers, in one forward pass. Not a model that thinks, nor one
that judges: a model that foresees.

Weights in 4 bits (GPTQ `W4A16`, groups of 128, static activation order) made with llm-compressor (compressed-tensors format), calibrated on 256 items of the training mixture (never on evaluation items). The vision tower, MTP layers, embeddings and LM head stay in bf16. vLLM runs it with Marlin kernels: it saves memory (a 27B on a 24–32 GB GPU), not time. The prompt format, the letter readout and the calibration (`calib.json`, T = 1) are the same as the bf16
model. See the [Ekbasis-27B card](https://huggingface.co/caiovicentino1/Ekbasis-27B) for what the model is, how it was
trained, the full evaluation, its limits, and how to let it look at the real state when unsure (predict, observe,
correct) over long sequences.

**Context window:** 262,144 tokens, as the bf16 model (the architecture's); the serving commands set 16,384 (4,096 in the 24 GB command below), and the evaluation's prompts average 0.7–1.6K tokens per state.

## Use

**Requires vLLM ≥ 0.30.0.** One GPU; the API and the client are the same as for
[Ekbasis-27B](https://huggingface.co/caiovicentino1/Ekbasis-27B).

```bash
hf download caiovicentino1/Ekbasis-27B-INT4 --local-dir Ekbasis-27B-INT4
bash Ekbasis-27B-INT4/serve_vllm.sh Ekbasis-27B-INT4 8001          # vLLM on 127.0.0.1:8001
python Ekbasis-27B-INT4/serve.py --model Ekbasis-27B-INT4 --vllm-url http://127.0.0.1:8001 --port 8000   # the API
pip install ekbasis                                                                                 # the client
EKBASIS_URL=http://127.0.0.1:8000 ekbasis git-check -- "git reset --hard"
```

**On a 24 GB GPU** (RTX 3090/4090 class), text only, with a 4k context (Ekbasis' prompts take about 2k tokens). We
checked this setting by limiting vLLM to 95% of 24 GB: 60 of 60 held-out git answers the same as at full
memory, 0.10 s per question (with the default settings, 24 GB leaves no memory for the cache).

```bash
vllm serve Ekbasis-27B-INT4 --host 127.0.0.1 --port 8001 --served-model-name decider --dtype bfloat16 \
  --gpu-memory-utilization 0.95 --max-model-len 4096 --max-num-batched-tokens 2048 --max-num-seqs 4 --enforce-eager \
  --limit-mm-per-prompt '{"image": 0, "video": 0}' --enable-prefix-caching --mamba-cache-mode align \
  --logprobs-mode processed_logprobs --max-logprobs 600
```

## Quality against bf16

The same sets and scripts as the release evaluation, the build served the same way (vLLM 0.30, one RTX PRO 6000).

| | Ekbasis-27B (bf16) | Ekbasis-27B-INT4 |
|---|---|---|
| Size | 55 GB | 18.6 GB |
| Git, all 3,105 questions (seen + never-seen command types), % | 96.6 | 96.4 |
| "Will work be lost?" AUROC — seen / never-seen types | 0.998 / 0.989 | 0.998 / 0.991 |
| Work-losing flagged at P ≥ 0.2 — seen / never-seen, % | 98.0 / 95.2 | 98.0 / 97.6 |
| False alarms at P ≥ 0.2 — seen / never-seen, % | 0.0 / 2.4 | 0.0 / 4.8 |
| 16 fresh real-repository scenarios: work-losing flagged / false alarms / "fails?" right | 3/3 · 1/13 · 16/17 | 3/3 · 1/13 · 16/17 |
| Never-trained worlds, answers the actions change — one prompt per question / read-once, % | 81.2 / 78.0 | 81.0 / 77.1 |
| `ftest_family`, answers the actions change, % | 81.9 | 80.9 |
| The 240-question git comparison — seen / never-seen types, % | 95.8 / 85.8 | 95.0 / 86.7 |
| ECE on git (lower is better) | 0.024 | 0.025 |
| Same answer as bf16 — all / bf16-confident (≥ 0.9), % | — | 97.4 / 99.7 |
| One check, one GPU — latency / checks per second with 16 in parallel | 0.088 s / 23 | 0.082 s / 21 |
| Forecasts of 10–30 actions, one GPU — median seconds one at a time / per minute with 16 in parallel (one prompt per question) | 5.0 s / 14.9 | 5.1 s / 13.3 |
| Same, reading the state once per step | 4.1 s / 28.2 | 4.0 s / 25.6 |

It meets 11 of the 12 criteria of the pre-registered quality gate. Where it differs from bf16:

- On command types never seen in training it raised 2 false alarms in the 42 cases that lose nothing, against 1 for bf16 (one case is 2.4 points; the criterion allows 1).
- The git answers that crossed the 0.2 flag (work lost: bf16 7% → 27%; nothing lost: bf16 13% → 56%) are three-command sequences with command types the model never saw; the AUROC there moves by +0.002.

The gate was written before the first builds existed, for V42's (`PREREG_quantized.md` in the repository:
accuracy within 1 point of bf16; every work-losing real-repository scenario flagged, and flag and false-alarm rates
within 1 point; ECE within 0.01; at least 97% of answers unchanged, 99% where bf16 is confident), and is applied
unchanged to this release's builds, against this release's bf16. It informs; every build that works is released, so
each machine can run the one that fits.

## Which build

| Build | Size | Runs on | Speed (one RTX PRO 6000) |
|---|---|---|---|
| [Ekbasis-27B](https://huggingface.co/caiovicentino1/Ekbasis-27B) (bf16) | 55 GB | GPUs with 80 GB | the reference |
| [Ekbasis-27B-FP8](https://huggingface.co/caiovicentino1/Ekbasis-27B-FP8) | 30.4 GB | GPUs with 48 GB; fastest with FP8 kernels (Ada, Hopper, Blackwell) | 1.6× the throughput of bf16 |
| [Ekbasis-27B-INT4](https://huggingface.co/caiovicentino1/Ekbasis-27B-INT4) | 18.6 GB | GPUs with 32 GB; 24 GB with text only and a 4k context (command in its card) | about bf16's |
| [Ekbasis-27B-MLX-4bit](https://huggingface.co/caiovicentino1/Ekbasis-27B-MLX-4bit) | 15 GB | Macs with Apple Silicon (32 GB or more recommended) | — |

GPU sizes were tested by limiting vLLM to that much memory on one RTX PRO 6000 and checking that the answers match the
build at full memory; the MLX build was validated with MLX on a Linux GPU, not on a Mac.


## License

Apache-2.0 (`LICENSE`). Built on Eikos-27B (MIT, `LICENSE-Eikos`) and Qwen3.8-27B (Apache-2.0, `LICENSE-Qwen`);
attributions in `NOTICE`.

## References

See the [Ekbasis-27B card](https://huggingface.co/caiovicentino1/Ekbasis-27B#references): every entry checked against
its source.

## Contact

Questions, collaborations and commercial use: caio@openinterp.org.
Found a way to make the guard approve a destructive action? Please email it before publishing (SECURITY.md in the
repository).

## Acknowledgments

Ekbasis was built by Caio Vicentino (OpenInterp) with the help of
[Claude Opus 5.5](https://www.anthropic.com/claude-opus-5-5) (Anthropic). Claude worked on the project with him:
- planning and running the experiments;
- writing and reviewing the code and the documentation;
- checking the numbers and the references in this card.
