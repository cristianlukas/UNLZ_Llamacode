# Q159 results · official CUDA source compatibility preflight

**Outcome:** stopped before build and GPU use because the exact pinned source commit has no `TQ3_0` type/loader for the preregistered Gyro-Coder-L file.

- Shallow source checkout verified at `dc255f2a4b6e4211b555b0c05260b2523281f314`.
- Static inspection of the exact source tree found `TQ2_0`, `TQ2_T`, `TQK6`, and `TQK7` support, but no `TQ3_0` registration/loader. The candidate name is explicitly `Qwen3.8-Flash-Next-Gyro-Coder-L-TQ3_0-v1.1.gguf`.
- Because the preregistered format gate failed, no CMake configure, build, `--list-devices`, model download, server, inference, benchmark, or GPU kernel was started. This is a compatibility blocker, not a model-quality result.
- Removed the Q159-only 213,319,428-byte source checkout from D; no build directory had been created. Kept the logs/receipts in this repo.
- Q152 stays blocked until the vendor publishes/identifies a CUDA runtime that supports this exact TQ3_0 artifact and enumerates both 3090s, or the vendor confirms the pinned file actually uses a supported GGUF type. Do not substitute a TQ2 model.
- PeritoSoft/llama-server had 0 running processes; no process was killed. The two old vLLM Docker containers were exited and left untouched. ASTRA, SOL, PeritoSoft models/config, and ArtCraft were preserved.

Receipts: `receipts/source-compatibility.json`, `receipts/cleanup.json`, `receipts/actionable-sync.json`.
