# Q161 results — Gyro-Coder-L v1.1 with explicit reasoning budget

**Final screen: 1/8 passed; no-go for further testing of this profile.** All 8 requests returned final code (8/8 transport, 0 sandbox errors, 0 empty outputs); seven solutions failed the functional grader and BigCodeBench/952 passed. The preregistered gate was at least 4/8. The single passing task does not justify a matched three-seed campaign. This is a narrow BCB-Hard-8 screen, not a universal claim about the model.

Q161 used the same GGUF, runtime, dual-RTX3090 split, context, seed, fixture, sampler and max output as Q152. The only request change was sending `reasoning_budget_tokens=2048` for the `swift` arm. The change eliminated the six no-final-content outcomes seen in Q152, but raised functional success only from 0/8 to 1/8. Q152's unbounded reasoning profile and Q161's budgeted profile are both no-go. Historical ASTRA Q97 was 2/8 on a different runtime, so this screen does not establish a matched superiority/inferiority comparison.

- Median wall time: 38.90 s/request; mean 38.63 s/request.
- Median prefill: 494.82 tok/s; median decode: 61.12 tok/s. Decode includes reasoning and final tokens; it is not useful-code throughput.
- 18,693 completion tokens total; all 8 cases returned code; only BigCodeBench/952 passed.
- Memory remained available: minimum MemAvailable 104.82 GiB; minimum swap free 3.30 GiB; memory PSI some/full avg10 max 0.00%/0.00%; OOM-kill delta 0. No artificial RAM/swap limits and no stop triggered.
- Peak candidate VRAM: GPU0 15,304 MiB; GPU1 14,322 MiB.
- Cleanup: Q161's server process group exited after SIGTERM. No process or LISTEN socket remains on 18383; only two TCP TIME-WAIT entries remain, which explain the supervisor's conservative bind-based `port18383FreeAfterCleanup=false`. Both GPUs returned to 0% compute.

**Recommendation:** do not continue this candidate to additional seeds or promote it. It has no verified PeritoSoft or product consumer, and the user has authorized removal of non-ASTRA/non-SOL models that are not used by PeritoSoft. The exact 83,975,624,672-byte evaluation GGUF was removed after verifying its SHA, single hard link, no open consumer, and no profile/config reference. The filesystem reported +83,975,626,752 bytes available. ASTRA, SOL, shared runtime/build, MTP artifacts, PeritoSoft data/configuration, and historical receipts remain.

Receipts: `receipts/preregistration.json`, `receipts/script-hashes.json`, `receipts/host-preflight.json`, `receipts/screen-run-20261027T040010Z.json`, `receipts/postflight-interpretation.json`, `receipts/candidate-retirement-preregistration.json`, `receipts/candidate-retirement-completion.json`; full per-case data and logs are under `runs/`.
