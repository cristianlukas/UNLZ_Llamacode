# ASTRA local tool-call canary for Harness²

**Test ID:** `Q-20261021-H2-ASTRA-LOCAL-TOOL-CANARY`
**Parent actionable:** VF-20261019-01 source #13, `f23604a1-ff2e-4d28-9e09-2b5cf01d9b69`
**Status:** canary attempted at 32K and, after preregistered amendment, 8K; both loads aborted before readiness under the unchanged PSI guard. No API request or model-quality score was produced. The known-answer grader self-test passed 10/10. See [`RESULTS.md`](RESULTS.md).

## Decision question

Can the existing production ASTRA Qwen3.8 Flash-Next IQ2_XS + Strata stack, through its local OpenAI-compatible chat tool-call interface, produce and deliver a small synthetic coding artifact? This is a gate for investigating a local-only Harness² workflow. It is not a Harness² quality result, a model comparison, or grounds to promote/replace a model.

## Fixed synthetic task and holdout

One request will ask the model to implement `covered_duration(intervals)` for half-open integer intervals `[start, end)`, returning the length of their union. Empty intervals contribute zero; `start > end` must raise `ValueError`. The prompt includes the function signature and contract, but not the hidden cases. A single `write_file` function is offered with `tool_choice=auto`; only a validated call targeting `solution.py` in the test scratch directory will be written by the runner. The model cannot invoke a shell or access other files.

The fixed local holdout has ten deterministic cases: empty input, zero-length interval, one interval, overlapping pair, nested pair, disjoint negative/positive intervals, duplicate interval, touching intervals, multiple overlaps, and reversed interval raising `ValueError`. All ten must pass for a canary pass. The runner records the prompt and tool schema hashes, not raw request/response bodies.

## Model/runtime and bounds

- Model: local ASTRA `qwen3.8-flash-next-iq2_xs`; pinned model files/config/runtime are checked against existing local receipts before launch.
- Serving: existing Strata 0.1.41 `.venv` and engine; two RTX 3090s; isolated copied config only; context 8,192 for this short task; explicit profile sampling `temperature=0.6, top_p=0.95, top_k=20, min_p=0, repeat_penalty=1, presence_penalty=0`.
- One sequential server, one model request, maximum 2,048 generated tokens; no Codex CLI, cloud endpoint, public dataset, benchmark download, app/profile edit, or external network route.
- Loopback-only port 8354 in an unshared network namespace; model/runtime mounts read-only, scratch workspace and receipt output only writable. A temporary cgroup limits the serving process tree to `MemoryHigh=64G`, `MemoryMax=72G`, and `TasksMax=512` if the host supports those properties. The generated-code grader runs separately with `MemoryHigh=1G`, `MemoryMax=2G`, `TasksMax=64`, a 40-second timeout, and scope termination on timeout.
- Preflight must find no inference server/API, port 8354 free, `MemAvailable >= 64 GiB`, memory PSI full avg10 <=10%, both GPUs >=20 GiB free and <85 C, and at least 20 GiB free on the scratch volume. ArtCraft/desktop GUI is allowed and left open.
- Abort on external inference server appearance, lost lock, `MemAvailable <48 GiB`, PSI full avg10 >25% in four consecutive 5-second samples, swap growth >1 GiB, any GPU >=85 C, process/cgroup failure, or 600-second readiness / 180-second request timeout. Stop only this test's owned process group and verify clean ports/processes.

## Amendments before the model request

- `harness2-astra-tool-canary-preregistration-amendment-01.json`: added independent memory/process limits to the generated-code grader and timeout cleanup.
- `harness2-astra-tool-canary-preregistration-amendment-02.json`: added a known-answer self-test of the grader after the initial model load aborted before emitting code.
- `harness2-astra-tool-canary-preregistration-amendment-03.json`: after the initial 32K-context startup crossed the registered PSI abort guard before readiness, set only the isolated canary context and KV residency to 8K. This synthetic function needs far less context; model, sampling, prompt, holdout, isolation, PSI threshold and decision rule stay fixed. The first attempt made no API request, and the retry remains limited to one API request.

## Result interpretation

Pass: one valid `write_file` tool call, a compilable artifact, and 10/10 holdout tests. Fail: no usable tool call, wrong path/schema, invalid artifact, or fewer than 10 holdout tests. Either outcome answers only the local ASTRA tool-call gate. Even a pass leaves Harness²'s quality comparison blocked until a local model-backed proposer/solver path and a two-task synthetic generalization workflow are fixed and preregistered. No promotion decision is made.
