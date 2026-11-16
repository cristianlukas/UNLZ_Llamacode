# Q225 · Speedy v0.4.0 / IQ3_S · Q173-style 8K screen

## A07 result

- Cold initialization to API readiness: **1,070.778 s** (17m50.8s); hot initialization: **N/D**.
- First request, seed 42, exact 8,192 prompt / 128 target: **failed before generating tokens**. `verify: instantiate: out of memory` while capturing the fifth speculative verification window.
- Free VRAM reported before failure: CUDA0 2,480 MiB; CUDA1 435 MiB. Strata explicitly recommended `--vram-reserve-later-mib 833` (current 500) or lowering max context.
- Completed requests: 0/3. Seeds 43/44 not run. Prefill, decode, and Q172 quality: **N/D**.
- The detached A07 service was stopped after Strata started an automatic engine reload, preventing repeated disk reloads. No test server, runner, benchmark client, or port 18489 remains.

A08 is preregistered to change only the late-window VRAM reserve to 833 MiB and to terminate the harness immediately if the engine reports CUDA OOM. No speed or quality superiority is inferred from A07.

Full evidence and hashes: `receipts/attempt-a07-inference-oom.json`.

## A08 result

- **Pre-inference setup failure**: `serve.server` rejected the reused `server-ready.json` path with exit code 2 before CUDA or benchmark requests.
- No GPU compute, prefill, decode, or Q172 measurement occurred.
- Receipt: `receipts/attempt-a08-preinference-ready-file-collision.json`. A09 has distinct readiness/log/run paths and retains the 833 MiB reserve fix.

## A09 result

- **Pre-inference configuration failure**: server exited before CUDA because its engine log path was relative to the source `cwd`; no model load or benchmark request occurred.
- No GPU compute, prefill, decode, or Q172 measurement. Port 18489 is free.
- Receipt: `receipts/attempt-a09-preinference-relative-logpath.json`. A10 resolves the log path absolutely while retaining reserve833.

## A10 result — inference OOM at verifier window 5

- The detached server reached API health in **917.501 s** with the model loaded. Both GPUs were assigned: ASUS used 21,698/24,576 MiB; PNY used 23,408/24,576 MiB (1,168 MiB free). Host MemAvailable was 61.96 GiB and PSI avg10 was 0.
- First Q173-style request (exact 8,192 prompt tokens, seed 42, output target 128) failed before token 1: Strata captured verifier windows 1–4, then `verify: instantiate: out of memory` at window 5. **0/3 requests; 0 tokens; P/D and Q172 N/D.** A07 also failed at window 5 with only 435 MiB free on CUDA1.
- The isolated systemd service stopped and released both GPUs; there is no server left on port 18489. Peak cgroup memory was 87.3 GiB, with no host memory pressure.
- Receipt: `receipts/attempt-a10-inference-oom-window5.json` (SHA-256 ca10b9cbc0eafae57eef2ab64bb73602c2755a0ee12dfa3b0c0610a24352c3cb).

## A11 preregistered

- Single change: raise later-card reserve from 833 to 2,048 MiB to leave more VRAM on CUDA1 for verifier graph capture. All other artifacts and benchmark settings remain fixed. This is a bounded 8K throughput screen, not Q172 or a superiority test.
- Amendment SHA-256 00625b6fcbf10889775e7fdc89d1b6356c115c6a21495132e1802420bd090f10; config 77dafc96dd27404e1516306d20b16b1864c4d2a8a0145f72c6d8971835c05467; runner fe128fab4b6f0ef076d25290d00e73cbf30ff9657fd13bc9676c49c18ea44418.
- Next: preflight and launch only under detached systemd; stop on first OOM and record exact outcome.

## A11 result — setup failure before CUDA

- The isolated runner passed its artifact/preflight checks, but the server exited before loading or using a GPU: its engine log path was relative to the server working directory. No inference or benchmark request occurred; P/D and Q172 are N/D.
- This is a harness/configuration error, not evidence about Speedy or the IQ3_S model. Receipt `receipts/attempt-a11-preinference-relative-logpath.json` SHA-256 830e1a61de0afdcf14b7af7df9a6d3468e5189d1bf3e2fc7dc6b788a6b334c0e.

## A12 preregistered

- Retain reserve-later 2,048 MiB; fix the A11 setup defect by resolving the per-attempt engine log to an absolute path and keep unique outputs. All model/runtime/context/harness settings stay matched to the Q173 screen.
- Amendment SHA-256 3d53f5d1c6db83813dd40ea008d923c26c1326c8f08b59a3701a25145b16b5e9; config 91fdb63ebf299bb3bae054790827076774b3ad506c19e2019d49bd2742afa229; runner 411eb3f7b278a41b0bb0d84a46cc96f343e6cb561a979bc7859dadf82d5f85cd.
- Next: run the same 3-seed Q173-style screen in detached systemd; stop on first OOM; no Q172 claim.

## A12 launch

- Detached systemd unit `q225-speedy-iq3s-q173-8k-a12.service` started at 2026-11-16 01:59:59 -03 (invocation `70229b97d0bb4e409377ddf7ab9d9597`). Initial runner state: loading; no CUDA compute yet. Launch receipt `receipts/launch-a12.json` SHA-256 2771243fc45e8b2cedd6073480354d58f9c65c8ce7884d148934d2ec08c1c716.
- It retains the 2,048 MiB later-card reserve and uses an absolute log path. Wait for an actual inference outcome before reporting P/D.

### A12 progress at 387 s

- Both GPUs now have the Strata process; host MemAvailable 64.0 GiB, PSI avg10 0.05%; service memory 78.3 GiB; 37.43 GB physical reads. Strata has entered the 46 GiB expert-arena stage; benchmark requests have not started. Progress receipt SHA-256 `c484ea9395a6a8e44aaf32850015f3fdc0ccb0201a7e246c894d8f130080e4e9`.

### A12 progress at 601.6 s

- Physical reads 53.02 GB, service memory 87.6 GiB, host MemAvailable64.2 GiB, PSI avg10 0.08%; both RTX3090s active. Strata still starting at589 s; no request yet. Receipt SHA-256 `4d9071b255c08bc08fe8e428fbc974f0d5b1c1a84321f33f5ebcd371ec2b7e3b`.

### A12 progress at 927.7 s

- Still loading, physical reads77.92GB, service87.6GiB, MemAvailable64.2GiB, PSI0; both GPUs remain assigned. No request yet. Progress receipt SHA-256 `ee31897657e0270f20950ece6f686a7688f9b8db68e18ebe2c7fb4af264fec62`.

## A12 result — reserve2048 still OOM at verifier window 5

- API health reached in **1050.06 s**. At readiness: ASUS used 21,698 MiB and PNY 22,194 MiB; after all weights the engine log reported CUDA0 2,476 MiB and CUDA1 1,983 MiB free. Host MemAvailable was 61.83 GiB, PSI avg10 0.29%.
- Exact Q173-style seed42 request (8192 prompt / 128 target) failed before token1: verifier windows1–4 captured; window5 OOM. **0/3 requests; 0 tokens; P/D/Q172 N/D.** The detached systemd unit stopped, released both GPUs, and left port18489 free.
- Receipt `receipts/attempt-a12-inference-oom-window5-reserve2048.json` SHA-256 6ef26ac6d8ee73bd931320160c303538649254bc6c06482348487e745d15ff61.

## A13 preregistered

- Single experimental change: MTP speculative width4→2; reserve2048 and all remaining settings stay fixed. This directly avoids the verifier window5 allocation that failed in A07/A10/A12. The screen is Q173-style throughput only; no Q172 quality result.
- Amendment SHA-256 8925dca879ea4ada012ef4c6caa1d519934cda1d9e516dfa2c21736587a79eb7; config 32d34fb69d10fe54b6c65e3e10af66d33b423b8317d00e14cc6c541c2e08e439; runner 3d85a4f90d074ac750f98977d7d78463e5c1679fcb4c9197d47511e13a9b3ed4.
- Next: fresh preflight and one detached three-seed A13 screen; abort on first OOM.

## A13 result — missing config path before CUDA

- The runner failed immediately because its `CONFIG` constant referred to `...a13-reserve2048.json`, while the file created was `...a13-reserve2048-spec2.json`. No model load/GPU inference occurred; this is a preparation error only. Receipt `receipts/attempt-a13-preinference-config-filename.json` SHA-256 2db1c46707dd6376a2cc6769cc865cadf899e57276493cb74f7c023a40217aad.

## A14 preregistered

- Keep spec2 and reserve2048; make the config filename exactly match the runner constant and assert file existence/hash before launch. No model or performance parameter changes from A13.
- Amendment SHA-256 73be8ebc933848cec92276ee983dd4bab332079450aba3023ed87d7ddd4f66fc; config 2ac9fedd4209694a2125ee8a28e466c35cbc969a705529e021226d22a66e26f0; runner 088c61bdd8ea2b9de508b7b745b99309d999aa6d0c58a7bbedf4a3c47aad2152.
- Next: fresh preflight, detached A14 screen; stop on first OOM.

## A14 launch

- Detached unit `q225-speedy-iq3s-q173-8k-a14.service` started 2026-11-16 02:22:18 -03, invocation `d5443a2c7eb4400586d5d917cb1dc749`. Exact runner config path/hash, spec2/reserve2048, absolute engine log, static compile, and free port were checked before launch. Initial state loading at0.1s; no inference yet. Receipt SHA-256 `7daeed275647151c79c911c62d84369adc3fe574119a9f84c889a26a6790868b`.

## A14 result — verifier graph OOM before first token

- A14 reached API health in **1069.953s**, but the engine then failed during first-window graph instantiation: `verify: instantiate: out of memory`. Free VRAM after weights was 2,438 MiB on ASUS GPU0 and 2,007 MiB on PNY GPU1. Host MemAvailable was 61.94 GiB and PSI avg10 0.09%; there was no host or cgroup OOM kill.
- Runner stopped the server before submitting the first Q173 request: **0/3 requests, 0 tokens; P/D/Q172 N/D**. Unit exited 1 on the engine error; port18489 and both GPUs are free. API-health time is diagnostic, not a valid cold-init measurement.
- Failure receipt `artifacts/evaluacion-modelos-llamacode/Q-20261116-Q225-SPEEDY040-IQ3S-Q173/profiles/speedy-iq3s/receipts/attempt-a14-verifier-instantiate-oom.json`; SHA-256 `a898b23bbc42cda42ec37949bf1088eda31280419b4fba0166e6ff938e5b89e9`.

## A15 preregistered — MTP retained, pipelined duplicate verifier disabled

- A14 was an inference/runtime failure, not a setup error: API health at 1069.953 s, then first verifier CUDA graph instantiation OOM at 2438 MiB free on GPU0 / 2007 MiB on GPU1; 0 requests and 0 tokens.
- A15 changes only pipeline mode `--pipeline-windows 2→0` and removes its paired `STRATA_PIPELINE_PENALTIES=1`; MTP spec2, reserve2048, model, GPUs, prompt, seeds, harness, and gates stay fixed. Speedy source says PW2 adds a second verifier per stage; this tests its documented no-pipeline memory fallback.
- Config SHA-256 `a8dfc3f2ad27cd498418cc132501bf3c808c17e42e8371c0d76f1c3710a0b40f`; runner SHA-256 `bb9982e5e280ac2668a566ea1ad4275dc7e6197ba3bd0288aace4d9166504107`; prereg receipt SHA-256 `66670e32184e8a4ad01ca8d78977d5a6e785d932f1143f998aa3ae44552d38bf`. Static compile PASS. Sheet prereg/readback is required before launch.

## A15 preflight correction (no GPU started)

- Static verification caught a typo introduced by the filename rename: the expected pack-receipt SHA had been altered; the pack receipt itself matched the original hash. No server/CUDA/request started. Restored the immutable SHA pin and changed the A15 runner to append, preserving A14 history. Corrected runner SHA `d4f31e904fbc627681a6be597c9a0af28daf7351887ae25f016110d63cbc97f1`; correction receipt `artifacts/evaluacion-modelos-llamacode/Q-20261116-Q225-SPEEDY040-IQ3S-Q173/profiles/speedy-iq3s/receipts/preflight-a15-attempt01-checksum-pin.json` SHA `bea61a756a98dc9b93a0b4076f7e4eba0e316eeed3a8e3f5151a9d58b7c67728`.

## A15 launch attempt 01 — blocked before CUDA; corrected

- Python server failed to open relative engine log `artifacts/.../logs/strata-engine-a15.log` while constructing StrataEngine. The engine binary never launched; no model load/CUDA/request. Port18489 and GPUs stayed free.
- Corrected only config log path to absolute `/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode/artifacts/evaluacion-modelos-llamacode/Q-20261116-Q225-SPEEDY040-IQ3S-Q173/profiles/speedy-iq3s/logs/strata-engine-a15.log`. Benchmark factor `--pipeline-windows 0` and all protocol/model settings are unchanged. Config SHA `c9e2d065c25fa37de74a9af368492babf39adafcd273ae6f3f4536c4646c17f5`; runner SHA `dede6f73d609b8f54dd621bffb80548fd86f0611922e288d0ea8417ac93537d0`; failure receipt SHA `7b3c4edfbe16f55b7763a5b534462d6c0df59877c277c0853c0dcc372c45a174`.

## A15 launch 02 result — verifier device arena did not fit

- **FAIL_INFERENCE_VERIFIER_DEVICE_ARENA_NO_FIT**. The full model loaded and the Strata engine session started on both RTX 3090s, but API readiness failed when the first verifier device arena (63.6 MiB) did not fit. The benchmark submitted 0 requests and generated 0 tokens; P/D and Q172 are N/D.
- Engine expert load took 1,027 s; 83.40 GB were read from the HDD. At failure: ASUS/PNY used 18,415/21,816 MiB; MemAvailable 63.9 GiB; cgroup peak 91.9 GiB; no cgroup OOM. Cleanup verified port18489 free and GPUs at 915/108 MiB.
- Receipt `artifacts/evaluacion-modelos-llamacode/Q-20261116-Q225-SPEEDY040-IQ3S-Q173/profiles/speedy-iq3s/receipts/attempt-a15-verifier-arena-no-fit.json` SHA-256 `326992641f9ec06663b8b981c495c38f2a4c0b76f4c52a57fc1d46d77abd23dc`. A16 targets this verifier allocation by increasing only reserve-later 2,048→4,096 MiB; see preregistration.

## A16 preregistered — one VRAM-reserve adjustment

- Change only `--vram-reserve-later-mib 2048→4096`; preserve pipeline-windows0 and MTP spec2. A15 loaded the model but could not allocate the 63.6 MiB verifier arena, with CUDA1 auto expert cache 17.23 GiB.
- Same Q173 8K×3 screen, weights, GPUs, harness, sampler and gate. The screen is throughput-only; no Q172.
- Amendment SHA `2b6e40ebb10528f12d43c723af603531b95898adeb8c2937b770b76613089cdc`; config `7538a22c71c8562ee2ed83c4b7794468d381a14e748d8434f6c959054b3778fe`; runner `ed5ebd914b3fb6890125bb08c9289ac66874177c8beda9411543a63af0438af6`. Static compile PASS. Sheet readback and fresh preflight precede CUDA.
- A16 fresh preflight PASS at `2026-11-16T06:21:47Z`: both expected RTX3090s idle, MemAvailable113.54GiB, PSI0%, P2P bidirectional OK, 3090 HELPER ASUS reservation1636/1636, gpu_unlock both cards, zero foreign servers. Receipt SHA `4b477f0ab3b5af846ec9b8adfdfcdfaf3172249e007771b71404588c5b91d7e6`.

## A16 launch attempt 01 — relative log path (before CUDA)

The server failed before spawning Strata because the copied A16 config still had a relative `log` path. No model/GPU/request started. Receipt `artifacts/evaluacion-modelos-llamacode/Q-20261116-Q225-SPEEDY040-IQ3S-Q173/profiles/speedy-iq3s/receipts/attempt-a16-preinference-relative-log-path.json` SHA `f51ca7c3954c36f68afc35e8c74f3732fcf4bef0c1f6bcddca4071dd92abea7e`. Correct only the path to an absolute resolved path and pin-check it before relaunch; reserve-later4096 remains the sole inference change.

## A16 setup correction — before CUDA

A16 attempt01 exposed a relative `log` path caused by stringifying a relative `Path`. Corrected it with a resolved absolute path and added a static guard requiring the config log to equal the runner's absolute `ENGINE_LOG`. No model/runtime factor changed. Static compile PASS; config SHA `4968e962884348232835fa81ff1ad1a9517827df17594e213ee2516d6b8b794b`, runner SHA `2a2112ea2aa5c2b484a695a3ee3c4f90d9f70572f9698eee1ba9e7cd3c439fae`, updated amendment SHA `af2785cbac40f3425eb440215bc987a0b1ecb00ab6293362c998ed837824b59f`. Fresh preflight and Sheet readback required before retry.
- Corrected A16 preflight PASS at `2026-11-16T06:25:26Z`: 113.63GiB available, no compute/foreign server, P2P and helper PASS. Receipt SHA `3bbd6388cb1b4e30b973e7347a44096ed918be2f84b792c0c07f17c2dd8a04ce`. Relaunching after Sheet readback.

## A16 launch02 result — verifier arena still does not fit

- **FAIL_INFERENCE_VERIFIER_DEVICE_ARENA_NO_FIT**. Full model and MTP draft loaded, dual-GPU engine session started. Increasing later reserve to4096 reduced CUDA1 auto expert cache from17.23GiB (A15) to15.23GiB, but the 63.6MiB verifier arena still did not fit before API health. 0 requests/0 tokens; P/D/Q172 N/D.
- Engine expert load46.84GiB/1008s; MTP draft uses813MiB; CUDA1 prompt path borrows3.09GiB. Cgroup peak96.0GiB, max events95 but no OOM; host available64.2GiB, PSI0. Cleanup GPUs921/108MiB, port free.
- Receipt `artifacts/evaluacion-modelos-llamacode/Q-20261116-Q225-SPEEDY040-IQ3S-Q173/profiles/speedy-iq3s/receipts/attempt-a16-verifier-arena-no-fit.json` SHA `b73ef18308fe3ffd190d5ed8e2753b35139fe3f77200085604a43946fd8ddae6`. Next diagnostic screen removes MTP/draft only, retaining reserve4096 and pipeline0.

## A17 preregistered — MTP off, prompt lookup retained

After A16 loaded the dual-GPU model but could not reserve the 63.6 MiB verifier arena, A17 disables the MTP draft layer (`mtp=false`, `drafting=off`; removes `--mtp` and `--spec-min-p`) while retaining prompt-lookup `--spec 2`, reserve-later4096 and pipeline-windows0. This tests whether removing the ~813 MiB draft footprint makes the verifier fit. Exact same Q173 8K×3 workload and gate; no Q172.

Config SHA-256 `611b6bf7e75b478b55ca4ca54562b6981882b5ad78064aff9884e708b1072053`; runner SHA-256 `053b578060a34be3fd97c1dc6287416696e0a2e7d4218c44d92a0a64713a0969`; static compile PASS. Fresh preflight and Sheet preregistration readback required before CUDA.

## A17 final — MTP off did not resolve verifier arena allocation

The engine loaded the full model and experts (46.84 GiB at 0.07 GiB/s) on the dual-3090 split and filled expert caches (CUDA0 14.06 GiB; CUDA1 16.24 GiB). Effective argv had no MTP/drafter flags, confirming the factor was applied. With prompt-lookup `--spec 2` retained, the engine still failed before API readiness: `verify: the device arena (63 MiB) does not fit`. **0 requests, 0 tokens; P/D/Q172 N/D.** Detached cleanup and postflight PASS: port free, no compute/server, helper/P2P/unlock intact. This is a launch failure, not evidence about model quality/speed.

Result receipt `artifacts/evaluacion-modelos-llamacode/Q-20261116-Q225-SPEEDY040-IQ3S-Q173/profiles/speedy-iq3s/receipts/attempt-a17-verifier-arena-no-fit.json` SHA-256 `10c897a8a1e47d4253d1e32cdc6131c6a61bdc73c3c1858955193bb656173574`; engine log SHA-256 `65ac7007df761b08326b0ea5a98cfce2393f25ee26c43f72491dfb9e057b7cba`; server log SHA-256 `1f6d46461c20c5163e5ba8c1af21ae8d225c832cd57fa3efbcb01c4370cab232`. Next diagnostic: turn off prompt-lookup speculation (`--spec 2`→`--spec 0`) to remove the verifier window as well; keep the other settings fixed.

## A18 preregistered — plain decode to remove verifier window

A17 proved that MTP-off alone still leaves the 63.6 MiB verifier arena when `--spec 2` is retained. The pinned Speedy source documents `--spec 0` as plain decode. A18 changes only `--spec 2`→`--spec 0`, retaining the A17 MTP-off config, reserve-later4096, pipeline-windows0 and exact Q173 screen. No Q172.

Config SHA-256 `5daef1891087bf510b292312c2495c4f80752b2e54351f34687b4eea246a00b7`; runner SHA-256 `87dcd823dffd21c238e70fc1acdf10d6bcb38bfe3cfc15bd32bf5a4d7c75002a`; Python compile PASS. Fresh preflight and Sheet prereg readback before CUDA.

## A18 final — invalid `--spec 0` for native IQ pack (pre-CUDA)

A18 stopped before weight loading: Speedy rejects `--spec 0` for a native IQ pack (`--spec T`, T >= 2). No CUDA compute, model load, API, request, tokens, throughput, or Q172. Worker cleanup and fresh postflight PASS. This test does not change the A17 arena diagnosis; the next valid diagnostic caps the first GPU expert cache at 6000 slots instead of auto.

Receipt `artifacts/evaluacion-modelos-llamacode/Q-20261116-Q225-SPEEDY040-IQ3S-Q173/profiles/speedy-iq3s/receipts/attempt-a18-preinference-spec-minimum.json` SHA-256 `7d0407c7bdf20b01e0667dc1bd7a61cc854a9acc1a63d7e7450e1bdfebcc0c05`; server log SHA-256 `2e13737a5039fbc94602bcb785546bb2067c2e54a531c1b04c5fa5836a5d8a08`; engine log SHA-256 `ed12ccb70b2e5ea2d74bab96a0f82d0557872c260fec8454410ab8eda35b67c3`.

## A19 final — cache6000 opened the server; Q173 harness screen invalid

Server reached readiness after551s and loaded46.84GiB experts at0.09GiB/s; effective cache8201 experts /14.88GiB VRAM. Three serial API requests ran and cleanup/postflight passed. However benchy could not parse pack `added_tokens` and fell back to GPT-2; actual prompts were7573/7344/7496 tokens, not8192. Seed43 emitted only6 tokens; benchy prefill values were null or nonsensical. Therefore no valid exact Q173 TPS is reported. Engine logs give diagnostic prompt P2250.5/2445.9/2490.5 and decode D23.2/19.2/25.1; mean decode for the two full128-token responses is24.15 tok/s, below the90 tok/s follow-up gate. Q172 not run. Do not continue the long-context ladder from this screen.

Receipt `artifacts/evaluacion-modelos-llamacode/Q-20261116-Q225-SPEEDY040-IQ3S-Q173/profiles/speedy-iq3s/receipts/attempt-a19-q173-screen-invalid-tokenizer.json` SHA-256 `4c43a421c72f1fe53424ff6d318447e56fdb3c149d57e3a58254d258ff45279a`; postflight PASS.
