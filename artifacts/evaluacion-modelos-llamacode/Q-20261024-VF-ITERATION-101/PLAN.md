# Q101 · HyperQwen write_file token cap canary

**Status:** closed after attempt 10 failed the `read_file` path contract; the planned `write_file` variable remained untested. See `RESULTS.md`.
**Lock token:** `f5f2021d-5cbf-4ae2-a0c9-878f53871914` (released after cleanup and reconciliation).
**Date:** 2026-10-24.

## Question

Does the previously truncated `write_file` tool response become valid if its completion cap increases from 512 to 1024 tokens? Q85 attempt 09 already produced a correct exact `read_file` call (489/26 tokens), but `write_file` consumed exactly 512 completion tokens, ended with `finish_reason=length`, and returned invalid path/content types.

## Controlled change

Change only `write_file.max_tokens`: **512 → 1024**. Keep `read_file.max_tokens=512` and final-response cap=128. Keep model/image/revisions, prompt, named tool choices, exact path enum, sampling, seed, TP=2, context, GPU utilization, KV pin, DFlash2, fixture, host hardware and cleanup unchanged.

The fixture remains `Q85-CANARY-READ-THEN-WRITE-314159` (SHA-256 `72e104733ce4d825eae8998b516025aa2c278284e1d875bddb05e9b7b8f48063`) in a unique temporary directory on the HDD. No persistent project or production file is modified.

## Hardware and memory policy

Use both RTX 3090s together (TP=2) and the installed 128 GB RAM without artificial memory or swap limits. Preserve ASTRA DEFAULT 1M, SOL, Flash-Next production profiles, PeritoSoft, GUI and unrelated compute apps. Moderate PSI warns and continues; hard stop at MemAvailable <32 GiB, any new OOM kill, or global PSI full ≥60% / some ≥80% for 15 consecutive 1-second samples. I/O PSI is recorded separately and is not treated as memory exhaustion.

## Decision gate

A pass requires one valid `read_file`, one valid `write_file` with exact string payload, output bytes equal to fixture, a nonempty final answer, and clean shutdown/port release. One canary only. On any contract failure, stop without Tool-Eval or A/B and keep HyperQwen blocked for agents. A pass only opens a separately preregistered next test; this canary alone is not comparative quality/speed evidence and cannot change production defaults.

## Execution order

1. CPU-only validation of runner, shell, and calibrated guard replay.
2. Sync preregistration to Google Sheets and read back both rows.
3. Fresh preflight: verify lock, server/process/ports, both 3090s, memory/PSI/OOM, free disk, Compose settings, pinned image, original-source hashes (including preserved pre-prepare backups for intentionally rewritten heads), and the prepared checkpoint's current structural readiness. The base hash receipt describes pre-prepare source files; HyperQwen's pinned prepare step rewrites the LM head, embeddings, and MTP tensors in place and retains `.bak*` copies.
4. Start a bounded transient systemd unit with unlimited memory/swap cgroup properties and low CPU/I/O priority. Run one canary and sample host memory, PSI (memory/I/O/CPU), OOM and GPU state.
5. Stop only this Compose candidate, verify no listener/container remains, write results and reconcile Sheet/app queue. If failure, stop the HyperQwen tool loop.

## Amendment 01 · correct post-prepare fingerprint gate

The first fresh preflight stopped before inference because it required the raw Hugging Face SHA-256 and size on every live file. That is the wrong gate for this already-prepared checkpoint: the pinned HyperQwen `docker/prepare.sh` runs `quant_lm_head.py`, `quant_embed.py`, and `quant_mtp.py`, which intentionally rewrite those weights and preserve the pre-transform files as `.bak*`. The Q85 raw-source receipt was captured before prepare, while Q85's post-prepare `verify.sh --no-server` passed 0 failures. This is a preflight false positive, not evidence of memory pressure or a crash, and no checkpoint file was modified during Q101.

Before any GPU launch, verify the original SHA-256 for the three transformed source files through their preserved backups, re-check the five untouched raw source files and pinned DFlash2 asset, and run a read-only structural check of the current prepared index/config/shards (all tensors fit within shard bounds and required quantized head/MTP keys exist). Require the existing pinned-image/Q85 post-prepare verification evidence and confirm the candidate directory has not changed since its successful preparation. Do not run `prepare` again and do not restore or overwrite any model file. This amendment changes only the validation method; Q101's sole runtime variable remains `write_file.max_tokens=1024`.

## Memory guard calibration evidence

- ASTRA DEFAULT/Flash-Next completed the 1,048,576-token needle screen at 10/10 exact facts. The monitor recorded peak process-tree RSS 51.14 GiB, minimum host `MemAvailable` 55.73 GiB, zero memory PSI, zero swap-out, no abort, and a clean server exit (`Q-20261014-ISTA-NEEDLE-HAYSTACK/receipts/runs/1048576/receipt.json`). The current 32 GiB hard floor remains 23.73 GiB below that successful run's lowest available-memory reading; it is a task-local abort condition, not a RAM or swap cap.
- Q97 recorded moderate global memory PSI full 34.72%, then recovered and completed the ASTRA arm with 71.864 GiB minimum `MemAvailable`, OOM=0. Q100 recorded 46.52% PSI full and completed all six tasks with 69.386 GiB minimum `MemAvailable`, OOM=0. Both are evidence that moderate PSI is a warning rather than a reason to stop.
- Q101's guard replay passes 6/6: moderate PSI warns only; sustained severe PSI must persist for 15 one-second samples; recovery resets the streak; stop on `MemAvailable <32 GiB` or a new global OOM kill. No cgroup memory or swap limit is set. The transient service will verify all three limits are `infinity` after it starts.

## Amendment 01 validation · 2026-10-24T22:18Z

The raw checkpoint and drafter fingerprints match their pinned receipts. The three original files preserved by `prepare` match their published SHA-256 values; the prepared checkpoint passes its read-only structural check in the pinned image with network disabled, no GPU device, and both model mounts read-only. The prior Q85 post-prepare verifier passed with zero failures. Fresh host preflight passed: both RTX 3090s have ≥22,000 MiB free, `MemAvailable` is 110.0 GiB, memory PSI is zero, OOM baseline is zero, no inference server/container or protected listener is active, and all storage floors pass. ArtCraft's 207 MiB on GPU0 is preserved. No GPU inference has started.

## Transient unit launch correction

The first `systemd-run` invocation was rejected before unit creation because `IOClass=` is not a valid systemd unit property; no model server or inference started. The launch wrapper now uses the documented `IOSchedulingClass=best-effort` and `IOSchedulingPriority=7`. A CPU-only transient no-op with the complete Q101 AppArmor, process, CPU/I/O, and unlimited memory/swap properties exited successfully. This is a launcher syntax correction; the canary parameters and its sole runtime variable are unchanged.

## Attempt 10 result · 2026-10-24T22:23Z

The pinned HyperQwen server loaded on both RTX 3090s and became healthy. The single preregistered canary did **not** reach `write_file`: the `read_file` response returned one tool call, but its `path` failed the fixture contract. The call used 489 prompt tokens, 507 completion tokens, and 14.246 seconds; `finish_reason=stop`. No fixture content was read back or written, no persistent file was created, and no Tool-Eval, quality score, throughput comparison, or A/B was run. Because the flow stopped at `read_file`, this attempt cannot confirm or reject whether raising only the `write_file` cap from 512 to 1024 tokens fixes Q85's truncation.

The harness receipt records only that `pathMatchesContract=false`, not the model's exact argument, so the particular malformed path is unknown. The candidate tool loop remains blocked under Q85's existing gate until a material parser/runtime change and a separately preregistered test; do not infer that HyperQwen is generally inferior from this canary.

### Memory guard during attempt 10

The host sampler recorded 96 one-second samples from 22:21:56Z to 22:23:31Z. `MemAvailable` stayed between 102.201 and 109.948 GiB; memory PSI some/full peaked at 1.08%; severe-streak samples, memory-warning samples, and OOM kills were all zero. The separate I/O PSI full peak was 21.37%; it did not enter the memory guard. The task-local 32 GiB floor was never approached, and the guard did not abort the run. This is consistent with the historical ASTRA 1M success: 10/10 retrieval, 51.14 GiB process-tree RSS, 55.73 GiB minimum `MemAvailable`, zero PSI, zero swap-out, and no abort. The detector did not treat high memory use by itself as a failure.

### Cleanup

The transient unit is inactive/dead, the owned HyperQwen container and port 18142 are absent, and the temporary canary directory was removed. Only ArtCraft remains in the compute-process list (207 MiB on GPU0); ASTRA DEFAULT 1M, SOL, Flash-Next, PeritoSoft, Codex, and the desktop were not stopped or changed. `MemAvailable` was 102.8 GiB at the first post-exit check and 109.7 GiB at the final check; current memory PSI full is 0.02% over 60 seconds, OOM remains zero. See `RESULTS.md` and `receipts/q101-final-result.json`.
