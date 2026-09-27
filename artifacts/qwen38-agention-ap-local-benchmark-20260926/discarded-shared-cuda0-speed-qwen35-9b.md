ggml_cuda_init: found 2 CUDA devices (Total VRAM: 49151 MiB):
  Device 0: NVIDIA GeForce RTX 3090, compute capability 8.6, VMM: yes, VRAM: 24575 MiB
  Device 1: NVIDIA GeForce RTX 3090, compute capability 8.6, VMM: yes, VRAM: 24575 MiB
load_backend: loaded CUDA backend from D:\Models\llamacpp\bench-runtime\b10964\unpacked\ggml-cuda.dll
load_backend: loaded RPC backend from D:\Models\llamacpp\bench-runtime\b10964\unpacked\ggml-rpc.dll
load_backend: loaded CPU backend from D:\Models\llamacpp\bench-runtime\b10964\unpacked\ggml-cpu-zen4.dll
| model                          |       size |     params | backend    | ngl |     sm |  fa | dev          |            test |                  t/s |
| ------------------------------ | ---------: | ---------: | ---------- | --: | -----: | --: | ------------ | --------------: | -------------------: |
| qwen35 9B Q4_K - Medium        |   5.28 GiB |     8.95 B | CUDA       | 999 |   none |   1 | CUDA0        |          pp2048 |      3234.67 ± 44.09 |
| qwen35 9B Q4_K - Medium        |   5.28 GiB |     8.95 B | CUDA       | 999 |   none |   1 | CUDA0        |           tg128 |         97.63 ± 1.68 |

build: b29c606e2 (10964)
