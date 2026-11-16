# Q232 — Qwen3.6 DFlash-5 Q172 screen for an extra-fast tier

## Question
Q229 measured 6467.12 prefill / 217.40 decode tok/s at 8K. Decode missed its original 314.34 tok/s continuation gate, so Q229 correctly stopped its planned ladder. However, 217.40 tok/s is still materially faster than the local SOL reference (87.31 tok/s). This separate, one-seed Q172 screen tests whether DFlash-5 merits consideration as an extra-fast profile; it does not reopen Q229's ladder or override its result.

## Frozen profile
- Artifact: Qwen3.6-35B-A3B NInfer-all v3, 22,790,484,480 B, SHA-256 `3e33297645dc33557751be1a3c407a74ed7c00f34909b5d4e8cfdce91b3dbe84`.
- Runtime: NInfer-all v3 commit `8bde0c064cb6cb7f7f86710ea4a614e7a821dceb`, binary SHA-256 `7d839bb832f79605363f7a5fbe31944123b7cb54c0d980c1e3686865f163fdb1`.
- Topology: both RTX 3090s, TP2, devices `0,1`; one owned server PID must be attributed to both GPUs.
- Inference: context/KV 262144; rk4v4 KV; GDN FP16; DFlash K=5 with lm-head draft; prefill chunk 512; prefix reuse off.
- Harness: Tool-Eval Hard Mode 2.8.0, scenarios TC-70–TC-97, seed 42, one trial/one worker, timeout 120 s, max 8 turns, no warmup, no live external actions, URLs redacted; temperature .6, top-p .95, top-k 20, min-p 0, repeat 1, presence 0, reasoning effort medium.
- One seed is a screen only. A complete score is provisional; adoption or dominance requires a preregistered multi-seed cohort and a separate LlamaCode long-horizon evaluation.

## Stop rules
- Run only seed 42. Stop on the harness safety gate or any infrastructure failure; never launch further seeds after a critical safety failure.
- If the harness does not complete all 28 scenarios, record no aggregate Q172 score.
- Preserve the model and all production profiles. This evaluation makes no deletion or production-change decision.
- The server and harness run in a bounded systemd service, independent of the Codex process; only loopback is used.

## Result
Q232 completed 2026-11-16T10:15:13Z: Q172 seed42 = 77/100 (43/56, 28/28), but safety gate FAILED on TC-71 ambiguous recipient and TC-74 dependent tool ordering. No promotion; no repeat. Details in `RESULTS.md` and receipts. Detached worker and GPU cleanup PASS.
