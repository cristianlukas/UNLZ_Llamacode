# Q240 — LlamaCode prefix-cache A/B, Qwen3.8-27B

Decision question: does the existing llama.cpp Q210 profile report and reuse a longer prompt prefix when a rolling tool transcript keeps tool-schema key order stable, compared with the same synthetic tool history where the key order changes?

Preregistered arms: `rolling-tool` (canonical schema) vs `unstable-prefix` (same schema keys in different JSON insertion order), both `cache_prompt=true`; 3 passes × 6 sequential turns each, 36 requests total. Same model, server, prompt construction and limits. Tool calls are transcript-only (`tool_choice=none`); no tools execute and no filesystem/network side effects occur. This is a cache-path screening, not a quality/Q172/LHA test.

Model: Qwen3.8-27B UD-Q4_K_XL `/media/cristian/Disco local/Models/llamacpp/Qwen3.8-27B-GGUF/Qwen3.8-27B-UD-Q4_K_XL.gguf`, expected SHA-256 `3f227079003add2511437e5b1e94812e363385225bf6a9b47b0054a72bc8b01e`.
Runtime: Q210 Tandem llama.cpp `/home/cristian/.cache/llamacode-evaluations/Q210-tandem-sm86-20261115/llama.cpp/build/bin/llama-server`, expected SHA-256 `31de89f011944d9f88d7f8fd188df04d6d1c93db5faad1a697820ad36c0eae96`.
Hardware: ASUS RTX 3090 GPU0 + PNY RTX 3090 GPU1, layer split 1:1; ASUS memory quarantine/helper must remain active. Context 8320; q8_0 KV; no drafter; reasoning off; endpoint loopback only.

Metrics: HTTP success fraction, median request wall time by arm, server-reported prompt/cache tokens (`cached_tokens` or `cache_n`), API-ready time, process exit/cleanup. The current runner does not score answer correctness; no quality conclusion will be made. Decision gate: only consider a follow-up if all 36 requests succeed and server reports cache metrics; a candidate cache win requires ≥10% lower median wall time or ≥10% higher median cached tokens for canonical schema, and must be replicated before changing defaults. Missing metrics or a smaller/noisy delta = no change.

Stop: foreign inference/compute process, protection preflight failure, API error/timeout, OOM/kernel fault, temperature ≥84°C, RAM available <32 GiB, PSI avg10 ≥1%, or cleanup failure. Worker is a detached user-systemd service, 15-minute runtime cap, 64 GiB memory cap, 500% CPU cap, control-group cleanup. No app/Codex process dependency.
