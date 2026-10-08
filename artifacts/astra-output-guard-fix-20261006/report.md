# ASTRA output guard and isolated retest

Date: 2026-10-06. Scope: ASTRA IQ3_S Strata launch and the pre-tool output guard
used by agent benchmarks.

## Diagnosis and changes

The guard used `streamingText`, a UI snapshot composed from reasoning and visible
answer text. As `<think>` grows before the answer, snapshots are not prefix
monotonic; a delta computed from them can recount answer characters. This could
falsely trip the 64,000-character pre-tool limit even when the model generated
only a small number of tokens.

`LlamaAgentBackend` now emits `generationProgress(messageIndex, generatedChars)`
from the raw reasoning-plus-content stream. The benchmark guard accumulates this
per message, handles a restarted generation, and leaves the hard limit in place.
Tool-call detection continues to use the structured/tool lifecycle path.

The isolated retest also exposed a setup trap: the system ASTRA profile was
started without the Strata root/config in its test-mode process, so two retries
failed before model load. That startup-only record was removed from test-mode
benchmark history and excluded from quality scoring. The real rerun passed the
root/config explicitly and launched Strata under LlamaCode supervision. For
external OpenAI-compatible backends, `cloudBaseUrl` must be the server root
without `/v1`; LlamaCode appends `/v1` for generation and checks `/health` at the
root. A remote HTTP 404 is accepted as reachability only for a remote backend;
transport failures remain failures.

## Verification

| Check | Result |
|---|---|
| `./scripts/build-linux.sh Debug` | Passed; binary: `/home/cristian/.cache/llamacode/build_linux/LlamaCode` |
| `./scripts/tests-linux.sh Release` | 77/77 passed, including raw-generation delta and remote 404 health regressions |
| ASTRA TaskFlow fixed-gold run | Started and finished normally; 4/14 after two repair attempts, 117.493 s total; no false pre-tool 64K failure |
| ASTRA run transport | 3 tool calls; first tool at 81.519 s; generation 114.020 s; 92.566 tok/s average |
| Cleanup | Benchmark stopped, ASTRA server stopped, test daemon stopped, ports 8350/8898 closed; GPU memory returned to 0.68/0.11 GiB |

TaskFlow passes: `py_compile`, completion gate, recurrence, concurrency. The ten
failing checks were model-validation/tag normalization, serialization,
service/filter API, dependency reporting, both undo cases, storage roundtrip,
missing/corrupt storage behavior, combined query filters, and exports. This is a
valid quality failure for this fixed suite, not an infrastructure failure.

## Comparison limits and verdict

The earlier ASTRA TaskFlow ULTRA result was 12/13 in 177.390 s. It used a
different task contract and profile fingerprint, so it is evidence that ASTRA
worked before, but not an apples-to-apples repeat of this 4/14 result. Do not
interpret either as a universal model ranking. The new run verifies that the
output-guard/process fix works; it does not establish that this ASTRA
configuration is reliable enough to replace SOL. Keep SOL as the dependable
profile until ASTRA repeats the same fixed suite successfully.

Machine-readable receipt: `result.json`. Full run data remains in the isolated
test-mode record at
`/home/cristian/.qttest/share/LlamaCode/LlamaCode/benchmarks/d849e1a0-1578-45f0-bd62-82ce5a8b5e7b.json`.
