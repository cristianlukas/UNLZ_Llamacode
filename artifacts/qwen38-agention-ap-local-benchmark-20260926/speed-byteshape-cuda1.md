ggml_cuda_init: found 2 CUDA devices (Total VRAM: 49151 MiB):
  Device 0: NVIDIA GeForce RTX 3090, compute capability 8.6, VMM: yes, VRAM: 24575 MiB
  Device 1: NVIDIA GeForce RTX 3090, compute capability 8.6, VMM: yes, VRAM: 24575 MiB
load_backend: loaded CUDA backend from D:\Models\llamacpp\bench-runtime\b10964\unpacked\ggml-cuda.dll
load_backend: loaded RPC backend from D:\Models\llamacpp\bench-runtime\b10964\unpacked\ggml-rpc.dll
load_backend: loaded CPU backend from D:\Models\llamacpp\bench-runtime\b10964\unpacked\ggml-cpu-zen4.dll
| model                          |       size |     params | backend    | ngl |     sm |  fa | dev          |            test |                  t/s |
| ------------------------------ | ---------: | ---------: | ---------- | --: | -----: | --: | ------------ | --------------: | -------------------: |
| qwen35 27B (guessed) all F32   |  12.17 GiB |    27.32 B | CUDA       | 999 |   none |   1 | CUDA1        |          pp2048 |      1108.86 ± 13.27 |
| qwen35 27B (guessed) all F32   |  12.17 GiB |    27.32 B | CUDA       | 999 |   none |   1 | CUDA1        |           tg128 |         36.20 ± 0.33 |

build: b29c606e2 (10964)
