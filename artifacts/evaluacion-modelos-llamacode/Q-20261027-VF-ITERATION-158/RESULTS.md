# Q158 results · Gyro-Coder-L official runtime device-enumeration retry

**Outcome:** blocked at the vendor runtime preflight; no model downloaded and no benchmark started.

## Execution

- Pulled the current official `linux/amd64` GHCR manifest pinned to `sha256:0f0547624f92df823ef7bdbfc1e497a3674cebeaaaefb2c59012ba1716799fc6` (165,510,028 bytes).
- Ran the vendor-documented NVIDIA invocation with `--gpus all`, `NVIDIA_DRIVER_CAPABILITIES=all`, network disabled, no model mount or port, and `/app/llama-server --list-devices`.
- CLI exited 0 but printed `Available devices: (none)`. The preregistered gate required both local RTX 3090s; it failed. This is a device/runtime failure, not a model result.
- No HTTP server, inference request, model download, BCB score, build, or benchmark was run.

## Cleanup and host state

- No PeritoSoft, `llama-server`, Strata, or vLLM process/listener was active before or after the check. No process was killed.
- The transient CLI container auto-removed. There were no image consumers; the exact Q158 image digest was removed.
- `docker ps -a` shows two exited historical vLLM containers (`vllm-qwen38-27b-dual-fast`, `llamacode-eval-sol-qwen38-20261012`); neither is running, and both were left untouched.
- GPUs returned to 0% compute: GPU0 890 MiB display use, GPU1 110 MiB; ArtCraft remains on GPU0 at 207 MiB and was not touched. The only listeners were unrelated OpenRGB, CUPS, DNS and ArtCraft.
- Free space after image cleanup: root 9,446,719,488 B; D/NVMe 496,142,651,392 B. ASTRA, SOL, PeritoSoft files/configuration remain untouched.

## Next useful route

The official Gyro page also says NVIDIA users can build the vendor `agentionai/llama.cpp` fork with CUDA (toolkit 12.x+); this host has CUDA toolkit 12.0, CMake 3.28.3, Ninja 1.11.1, and about 496 GB free on D. Q159 preregisters checking that source-build path before any model download. If a CUDA build cannot enumerate both 3090s or cannot parse the exact Q152 file without loading it, stop and keep Q152 blocked.

Receipts: `receipts/preregistration.json`, `receipts/runtime-device-enumeration.json`, `receipts/postflight.json`.
