# Resultados Q209 · Maya-XS Q173 DS4_SPLIT=39,1

## Estado actual

- **Q173 ladder completo** hasta el máximo aprobado de 261888; 523904 no se ejecutó. La inferencia larga se ejecutó mediante worker/engine `systemd` detached y acotados, independiente del proceso de Codex.
- Medias equiponderadas por los cinco contextos: prefill efectivo E2E **514.864 tok/s**, decode **19.573 tok/s**; descriptivas, no una tasa estable (8K n=3; 32K, 64K, 128K y 261K n=1).
- Q173 no mide calidad; Q172 permanece separado y TC-92 sigue fallando.
- Google Sheets `Resultados` fila496 y `Modelos locales por peso` fila6 se actualizaron y leyeron de vuelta; valores/notas y formato comprobados por API. La captura visual completa no estuvo disponible por sesión Google sin autenticar y viewport.
- Recibos finales, hashes, métricas y estado de limpieza: `receipts/q173-context-261888-completion-amendment.json`.

## Calidad ya documentada, cohorte distinta

Q172 del perfil exacto DS4_SPLIT=39,1: 88/89/91, media 89.33/100 (n=3), 28/28 escenarios cada semilla. Falló TC-92 en las tres; seed42 también TC-89. LHA-1=76/100 corresponde a otra suite. No se usan como resultado de Q173 ni para seguridad multi-tenant.

## Siguiente paso

Q209/Q173 quedó cerrado hasta 261888; no repetir el ladder ni ejecutar 523904. Continúa el objetivo padre Q202: reconciliar las pestañas IA y tomar el siguiente accionable pendiente con sus gates. Toda inferencia prolongada debe usar un worker `systemd` detached, acotado y verificable, de modo que su vida no dependa de la sesión ChatGPT/Codex. Al reanudar, consultar el estado y los recibos del worker antes de lanzar cualquier trabajo; nunca dejar una inferencia ligada a un `exec` interactivo.

## Sincronización de enmienda01

- 2026-11-15T06:56:52+00:00: `Resultados!A496:AH496` y `Modelos locales por peso!J6:K6` leídos de vuelta; valores y formato coinciden. La hoja mantiene la corrida como pendiente y el intento01 como error de runner, sin atribuir resultado al hardware.
- Prereg SHA-256 `acefa6e2876a3ff51c5ef890a7c4cfe0d7987a6acd3ad653f73e767ca9328f1f`; runner SHA-256 `8e3d16ad5e07c1a7b7301175bd276dd153dbb1328d6eae5780c71e9c1d6d25d8`. Recibo local `receipts/sheet-amendment01-readback.json`.
- Próximo: preflight de assets/gates completo; no arrancar Maya si un gate falla.

## Preflight attempt02 — launcher digest pin mismatch

- 2026-11-15T07:10:38+00:00: all five model shards (276,626,308,260 B) matched their pinned SHA-256 values. Preflight stopped at the launcher support-file check: observed SHA `95087759f61e581888fadbb3e9f84128197a7d908628658ccb65e3298e82748b`, while amendment01 pinned the incorrect `95087759f61e581888fadbb3e9f84128197a7d908628ccb65e3298e82748b`. Launcher mtime is 2026-10-29 and the observed SHA matches prior Q206 receipts; no evidence the launcher changed. No server, inference, or GPU compute started.
- Amendment02 fixes only the launcher fingerprint and records this failure. Runner SHA-256 `9f5dfb07bae15324961b010292b3be718e0e7debcf70224fafb0561bf66a06df`; preregistration SHA-256 `ce14311df7f17c2157b20458cf7d736ac8ee92b2899ff83cc5bedb3dff4b8ea0`. Receipt `receipts/preflight-attempt02-launcher-hash.json`.
- Next: sync/read back amendment02 in Sheets, then repeat full pinned asset/live preflight; if PASS, run only Q173 8192×3.

## Attempt02 sincronizado

- 2026-11-15T07:11:48+00:00: fallo por pin de launcher leído de vuelta en Google Sheets; hoja marca explícitamente que no hubo servidor, inferencia ni cómputo GPU. `Resultados!E496/AD496/AF496` y notas J6:K6 coinciden; formato preservado.
- Recibo `receipts/sheet-amendment02-readback.json`; amendment prereg SHA `ce14311df7f17c2157b20458cf7d736ac8ee92b2899ff83cc5bedb3dff4b8ea0`.
- Próximo: preflight completo con pin corregido; el ladder no empieza hasta PASS.

## Preflight attempt03 PASS and Sheet readback

- 2026-11-15T07:22:24+00:00: full hashes passed for all five model shards and five pinned support assets. Live gates PASS; no server or compute app. Result synchronized/read back; no Q173 speed data yet.
- Preflight SHA-256 `e82f24c15b1ae0f5905ac264ed3a07b6a58eefcfc5be6abed07b66ff0ccace36`; Sheet readback `receipts/sheet-preflight03-readback.json`.
- Next: fresh gates, then only 8K×3 on ASUS+PNY if still clear.

## Q173 8192×3 — PASS parcial de ladder

- 2026-11-15T07:38:03+00:00: Project Maya Q189 `DS4_SPLIT=39,1`, same PID 3878694 allocated on physical ASUS GPU0 (UUID af6de4b3…) and PNY GPU1 (UUID 5b9f385f…). All three target-8K requests completed with 8,222 actual prompt tokens and 128 output tokens. Effective prefill **393.593 tok/s** (SD 0.895, n=3; prompt tokens/first content token elapsed); decode **31.023 tok/s** (SD 1.878; samples 29.329/33.641/30.099). TTFT 20.890 s mean. Server readiness 477.877 s, not separated into cold/hot. Q173 has no quality score; historical Q172 89.33 remains separate and TC-92 still fails.
- Minimum MemAvailable 16.64 GiB, OOM kills 0; peak VRAM ASUS 7,668 MiB and PNY 23,940 MiB; max temps 65°C/61°C. Server stopped cleanly, port free, no remaining servers; MemAvailable recovered to 115.56 GiB.
- Synced/read back PASS in `Resultados` row496 and `Modelos locales por peso` row6; inventory E/F show provisional 8K-only numeric values with notes; full-ladder mean pending. Receipt `receipts/sheet-q173-8192-readback.json`. Raw/result/event/startup/postflight SHA-256: `3207a38b8ca3c15d924a710d50778262a4a1ad36ed93ed0d0b133079919c600f`, `c148e67b294c0aa31cf7de106d22c4f357305246350c625c400f366c3b4ae86a`, `214aa4dc2ae73dcd8593eb61cd7ddc86d2149f4f0b211db74b52a07bdcf366a2`, `f0d894da34c45c51ddea165ce397b1cafbffc34fbe5529c8cde7f66df39ea693`, `37568cd22157c47eb52bc60afe882f6112fe2a2488c640a71ad159d34465b5d5`.
- Next: fresh gates then context32768×1.

## Q173 context 32768 checkpoint — 2026-11-15T07:42:23Z

- PASS en el perfil Project Maya Q189 exacto, `DS4_SPLIT=39,1`, dual ASUS+PNY. Prompt real 32.798 tokens y salida128. Prefill efectivo E2E 540,474 tok/s (n=1); decode26,058 tok/s (n=1); TTFT60,684 s. Readiness101,341 s, sin clasificar como cold/hot.
- El mismo PID de cómputo apareció en ambas GPU. MemAvailable mínimo durante muestreo 21,53 GiB; VRAM pico ASUS7.605MiB/PNY23.940MiB; temperatura máxima66°C/65°C; OOM0. Servicio terminó limpiamente, puerto libre y sin inference servers residuales; MemAvailable posterior23,26GiB.
- Se actualizó y leyó de vuelta el Google Sheet: `Resultados!E496`, `U496:AD496`, `AF496`, `Modelos locales por peso!E6:F6`, `J6:K6`. Formato WRAP/Arial10 de resultados y formato numérico/CLIP de inventario preservados. Recibo `receipts/sheet-q173-32768-readback.json`, SHA-256 `3710e04e36b6f8e1473769e59e68692a8de850892dac88c9e9445c029eed3c7f`.
- Promedio provisional equiponderado entre medias por contexto (8K×3 y 32K×1): prefill467,033 tok/s; decode28,540 tok/s. No equivale al promedio final del ladder; 64K,128K y261888 están pendientes. Q173 no otorga puntaje de calidad y no se calcula compuesto calidad/velocidad.
- Raw run SHA-256 `004a4a61f925f44b62c5f5d9e46fac4baeae44adaf17c6f2888b2e3fb2326b1b`; events `81fca6739fb075fca3408160c9423d4ae6f0ae3b87b61d24a936a6dceb76bb58`; result receipt `98c2e343542aee5514fb794e78728e2e8a1cad67e7bf31cf56f93c0f9a7c999b`; startup `8944d57c74bcde1a0bcb8ff2ecb13932ad8335bc0b4e8eedb2729be84f726c58`; postflight `96be4ca2596ecc8ede5b828bbe963826799a964f0567ae50e21b8f4cf00f2944`.
- Siguiente paso exacto: releer protocolos/lock, ejecutar gates vivos y, sólo si pasan, correr Q173 `65536×1` en ambas RTX3090; después sincronizar y leer de vuelta Sheets.

## Fresh dual-GPU preflight before 65536 — PASS

- 2026-11-15T07:57:07Z: all five Maya shards and five pinned support artifacts passed full SHA-256 verification (276,626,308,260 model bytes). Both physical RTX 3090 UUIDs matched the PNY-first profile; 3090 HELPER PASS, ASUS quarantine1636/1636, bidirectional P2P read/write PASS, gpu_unlock loaded for both; no foreign inference servers, port18628 free, no compute apps. MemAvailable 124,488,036,352 B (~115.95 GiB), OOM0; output volume free27,512,778,752 B (~25.63 GiB).
- Preflight receipt `receipts/preflight-context65536.json`, full-hash completion 07:57:07Z. No inference launched by preflight.
- The next permitted action is the preregistered 65536×1 Q173 point on both ASUS and PNY, then stop/verify cleanup and sync/read back Sheets.

## Q173 context 65536 attempt — NO RESULT; orphaned server timeout

- The controller session for `run_q173.py run --pp 65536 --runs 1` disappeared; polling later returned `Unknown process id 48222`, and no runner remained. Its nested `q209-maya-q173-pp65536.service` kept running separately. Maya reached API-ready at 05:04:30 local, but there is no run JSON, events file, request result, prefill/decode metric, or quality score. The captured controller stdout is empty (SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`).
- The independent Maya unit stopped only when its own `RuntimeMaxSec=7200` fired at 06:59:10; systemd marked `Result=timeout` at06:59:14. `ExecMainStatus=0` is the launcher’s exit status, not a passing benchmark. The engine reached readiness but was left unattended for nearly two hours; this is the orphaned-process failure mode the user warned about. The evidence is consistent with the Codex-side controller/session disappearing; the direct cause of Codex closing is not proven by systemd records.
- The attempt did use the same Maya process on ASUS GPU0 and PNY GPU1. The service consumed 41min29s CPU and peaked at87.4GiB memory, with zero swap. After termination there were no inference compute apps and MemAvailable recovered to≈116.2GiB. No 64K data are included in Q173 averages.
- Failure receipt `receipts/q173-context-65536-failure.json` SHA-256 `325196b1c4da71a1dea797f3b3a5bf93636e6ff23e4717e2c4887f548267e8d3`; journal `receipts/systemd-journal-context-65536.txt` SHA-256 `3883bcdd18ad738191a06ad554a5b0c559be87835f1eeed6edeede8bf254ce91`; engine log SHA-256 `7a6bda71f6a2b4ba98702bba2ffcb501b9c89ec67383ecfd5d7a990c74154701`.
- **No further GPU benchmark will start under this controller design.** Next: implement a detached, bounded systemd worker for the whole Q173 controller, make worker exit/timeout stop its child inference unit, and prove caller-exit survival plus cleanup with CPU-only fake jobs. Only after that test and Sheet/local readback may Q173 64K be retried.
- Failure state synced and read back in Sheets: `Resultados!E496`, `AD496`, `AF496`; `Modelos locales por peso!E6:F6`, `J6:K6` notes now state the 64K attempt had no result and is excluded; numeric provisional P/D values were preserved. Readback receipt SHA-256 `4e13dbce0b8de52e670948eadd6bf5ae3658329ee0f49e4dbec15e7a23d0eebb`.

- 2026-11-15T14:58:00+00:00 — Q209 detached-controller remediation preregistered before testing. Replaced the foreground-only Q173 run path with a token-checked user-systemd worker launcher, bounded outer controller (3900s/8GiB) and Maya child (3600s/96GiB, no swap, OOMPolicy=kill); exact identity-gated ExecStopPost cleanup writes durable receipts. Preregistered CPU-only fake-job lifecycle gate `Q209-CONTROLLER-DETACHED-CPU-01`: launch returns immediately, controller must keep running after caller exit, then hit its 8s cap and stop only its fake child. No GPU/model/inference calls. Sheet sync/readback is required before the smoke; GPU retry remains blocked until PASS. Runner SHA `a4f54ecec98bfce1f9fd01f2c233f2367e8e904a2a605015e1d49fbe9fd2d411`, detached launcher SHA `a2a4ff0f19842c3f34fa3d8ce8e5479be894fe74de686aff92dfb192b5f9a010`, cleanup SHA `05dd9013063ed2a29d0442e5dd2dd11de1fba08a7b6cb0770a789cc9bdb49853`, smoke SHA `2a5e419ca620e0228d55ee3a95543a3b9c4b82c7012406a12579389be698cfab`. Prereg SHA `1e4fa706714463eb754981e963c7ca96739b1be982f49888f92c5ff2a68fc873`.

- 2026-11-15T15:00:10+00:00 — Q209-CONTROLLER-DETACHED-CPU-01 syntax gate PASS: `py_compile` succeeded for the runner, detached launcher, cleanup hook, and lifecycle smoke script; no GPU/model used. Receipt `artifacts/evaluacion-modelos-llamacode/Q-20261115-MAYA-DS4SPLIT39-Q173/profiles/maya-xs-iq1s-pny-ds4split39-q173/receipts/detached-worker-syntax-gate.json` SHA-256 `54f29e9e8d290bf14d99f9c80491baa3c2c2b30fcac8fbbbed33d6d923cf9507`. Sheet preregistration was already read back; immediately syncing this test result before the lifecycle test.

- 2026-11-15T15:02:58+00:00 — Q209-CONTROLLER-DETACHED-CPU-01 amendment01 syntax gate PASS after registering the lock re-check and identity-limited emergency cleanup. `py_compile` passed for all four current files; lock Q202 verified; no GPU/model used. Receipt `artifacts/evaluacion-modelos-llamacode/Q-20261115-MAYA-DS4SPLIT39-Q173/profiles/maya-xs-iq1s-pny-ds4split39-q173/receipts/detached-worker-syntax-gate-amend01.json` SHA-256 `e39532d3106fd1f9e5fa5ea63915cf5c0c11d4e38a01bb1792a5d6c2bbded500`. The amended preregistration was synchronized and read back from `Resultados!E496/AD496/AF496`; next is the two-stage CPU-only systemd lifecycle smoke.

- 2026-11-15T15:05:45+00:00 — Q209-CONTROLLER-DETACHED-CPU-01 PASS. The systemd-run caller returned immediately; the fake controller continued after that process exited, hit its registered 8s timeout, and `ExecStopPost` stopped only the child whose exact Q209 smoke description matched. Worker result=timeout; child inactive; no model/GPU or other unit touched. Summary `artifacts/evaluacion-modelos-llamacode/Q-20261115-MAYA-DS4SPLIT39-Q173/profiles/maya-xs-iq1s-pny-ds4split39-q173/receipts/detached-worker-cpu-smoke-summary.json` SHA-256 `2c74f6586821c1bae756577ebeb411944b4c5c8a6b8b82f7ce89e29430fc4cf7`; worker receipt SHA `00558c6a0d913473e87cfd5ed40e2e1506a5eb2b7c6e7869b99c36c6266edbe7`; cleanup receipt SHA `fedd48f7e51a51926d9f9b3f9eb4c23c1e404a323039cc4ce3a301737244c2cc`. Next: sheet update/readback, then one detached bounded retry of Q209 64K; 128K/261888 remain gated.

- 2026-11-15T15:05Z — Google Sheet final correction/readback for Q209-CONTROLLER-DETACHED-CPU-01 PASS: Results row496 and Modelos locales por peso row6 notes now carry the detached-worker smoke status; numeric P/D means unchanged. Readback receipt SHA-256 `1bc43d1a9d2f398077c9ac16792bfe1f03911ff13063822c85b39a669f6dd491`. Cleared the failed state of only the generated fake worker unit; fake child was already inactive. No model service or GPU used by this smoke.

- 2026-11-15T15:12Z — Q209 prelaunch cached-preflight refresh PASS: reused the previous five-shard full-SHA result only after all shard path/device/inode/size/mtime_ns snapshots matched and all five supporting files rehashed to pinned SHA; fresh helper, ASUS quarantine, P2P, gpu_unlock, port, memory, both GPU UUIDs and zero other compute apps/inference servers passed. MemAvailable 124,667,830,272 B; output volume free 27,512,774,656 B. Did not launch inference. Receipt `profiles/maya-xs-iq1s-pny-ds4split39-q173/receipts/preflight-cached-refresh.json` SHA-256 `4a9c769a8b9c46f5dc66069cb701b584a7f7e878628a7ec3abdd5682196d96f5`; Google Sheet readback `sheet-preflight-cached-refresh-corrected-readback.json` SHA-256 `abfbfd45d02fe5a9545f4b8b270b735a799c34d3966db24a082d6e401f4c1f53`. Next: one detached bounded Q209 Q173 64K attempt a02; no new full model hash scan.

- 2026-11-15T15:12:28Z — Q209 Q173 context65536 retry attempt a02 launched with `launch_detached_q173.py` as independent systemd user worker; launcher returned in <1s while worker stays active. Worker unit `q209-maya-q173-pp65536-worker-a02`, engine unit `q209-maya-q173-pp65536-a02`; both active. At initial snapshot controller RSS≈14MiB, Maya service MemoryCurrent≈6.67GiB and rising during startup; no Q173 metrics yet. Outer bounds3900s/8GiB; engine bounds3600s/96GiB, swap0, KillMode=cgroup, exact ExecStopPost. Launch receipt SHA-256 `986a97b294972f2dee5162929f256ac2a4ed6bf01f9007f7cd6b17f4edace974`.


## Q173 context 261888×1 a01 — PASS; ladder completo

- Contexto real261888; prompt real261918; salida128; P efectivo E2E593.171452654 tok/s; D17.470870160 tok/s; TTFT441.555302144s; readiness20.335s no clasificado cold/hot.
- Ambas RTX3090 ASUS GPU0 + PNY GPU1, perfil Maya-XS IQ1_S / Project Maya v1.1.37 / `DS4_SPLIT=39,1`. Worker `q209-maya-q173-pp261888-worker-a01` y engine `q209-maya-q173-pp261888-a01`, detached y exit0. Postflight: no server ni compute app; puerto libre; OOMKill0; MemAvailable mínimo116190371840B/post123915268096B.
- Promedio descriptivo equiponderado 8K/32K/64K/128K/261K: P514.863854, D19.573140 tok/s. n=3 sólo a8K y n=1 en los otros cuatro contextos; decode64K fue4.801 tok/s. No es métrica estable ni score de calidad.
- Google Sheet readback `receipts/sheet-q173-261888-complete-readback.json` SHA-256 `5939f91eb8a5ea5dc7e0ed670b3d42fbbee22a34b4adf477fbbc62d374070cb2`; resultado `receipts/q173-context-261888.json` SHA-256 `f5b21d5cc463e61443c3606e79747c823895581e8d48e42028506a31bbe890d1`; postflight `receipts/postflight-q209-maya-q173-pp261888-a01.json` SHA-256 `301c1572646cf5672a4f88628271074008aebf9414925bee99733ab9c09bc9e7`; worker cleanup SHA-256 `ccf8a55a68077e6632b8744986c51b2706c49b10ec1bf7da392fad826f7d483b`.
- La causa exacta de los cierres de Codex no está demostrada. El desacople evita dejar la inferencia bajo el ciclo de vida de ChatGPT, pero no constituye diagnóstico del cierre. No ejecutar523904.
