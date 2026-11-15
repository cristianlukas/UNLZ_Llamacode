# Q209 · Maya-XS DS4_SPLIT=39,1 · Q173 ladder

## Objetivo

Medir prefill y decode del perfil exacto Maya-XS IQ1_S / Project Maya v1.1.37 que ya tiene Q172 y LHA-1 locales: PNY física GPU1 primero, ASUS física GPU0 segunda, `CUDA_VISIBLE_DEVICES=1,0`, `gpu=[1,0]`, `DS4_SPLIT=39,1`, TP2. El propósito es llenar la medición de velocidad faltante para este fingerprint y no heredar el Q173 histórico del Maya genérico.

## Preregistro

- ID: `Q209-MAYA-DS4SPLIT39-Q173`.
- Lock raíz: tarea Q202, token `d9029f6b-c649-4291-b0be-f14d77dc737e`.
- Artefacto: los mismos cinco shards Maya-XS IQ1_S de Q189; tamaño esperado total 276,626,308,260 bytes; manifest `8f097ebbe0c42e5f2edf40ccab3daadfbc04910f2ce9bbfcd170e51c08bc2a45`; fingerprint externo `6f0833fcf977726db71c537b71a6843d65e8b834e33f0e7fbaac65eff354fadc`.
- Runtime: Project Maya v1.1.37; ejecutable SHA-256 `b4d00bcb0dc1b6680158749941601e79f669af6b1ae5c2d28c5feaa0cc72df17`; launcher SHA-256 `95087759f61e581888fadbb3e9f84128197a7d908628ccb65e3298e82748b`.
- Configuración: servicio aislado de usuario, loopback `127.0.0.1:18628`, servidor ctx=262144, TP2, visión off, reasoning medium, temperatura .6, top-p .95, `DS4_SPLIT=39,1`.
- Harness: llama-benchy 0.4.0, SHA-256 `e8a892fe937d5ae1b6a43c31e8cb286ce4774f70396f62ab71008c9ddb0a01a1`; tokenizer DeepSeek pinned SHA-256 `c90dfa01249db1be4245780a052ede752e1361c612ac6d08e2bdada7d599476b`.
- Ladder: prompt tokens 8192 (3 repeticiones), 32768, 65536, 131072 y 261888 (una repetición cada uno); generación exacta de 128 tokens; concurrencia 1; seed 42; sin cache del harness. No medir 512K/523K.
- Prefill principal: tokens reales de prompt / tiempo desde inicio de solicitud al primer token con contenido, a partir del flujo de eventos; el `pp_throughput` reportado por el harness queda como diagnóstico y no sustituye el cálculo E2E. Decode: media de `tg_throughput` del mismo resultado. Informar cada contexto y promedio aritmético equiponderado, junto con n y dispersión disponible.
- Gate de validez: conteo de prompt y salida exactos, todas las solicitudes terminadas sin error, readiness de API, mismo servicio con PID de cómputo en ambos UUID físicos, ninguna inferencia ajena, helper/P2P/quarantine/unlock PASS, salida limpia y puerto libre.
- Guardia de operación: detener solamente el servicio Q209 propio si MemAvailable cae bajo 16 GiB en dos muestras consecutivas, si aparece una inferencia ajena, si falta una GPU o si falla un gate. El servicio tiene límite RuntimeMaxSec=7200 para no quedar huérfano tras caída del controlador.
- Calidad: Q173 no mide calidad. Q172 exacto del perfil ya registrado en Q206 es 89.33/100, n=3 (88/89/91), con fallo crítico TC-92 en las tres semillas; LHA-1 76/100 es otra suite/cohorte. No mezclar los scores ni promover el perfil a uso multi-tenant.
- Decisión: esta prueba puede completar la fila comparativa, pero por sí sola no prueba dominancia sobre ASTRA DSX: el Q190 histórico usó otro perfil Maya y cohortes previas. No borrar pesos por diferencias de esta prueba sin comparación emparejada y auditoría de dependencias.

## Estado

Plan y preregistro local preparados y sincronizados en `Resultados!A496:AH496`; `Modelos locales por peso!J6:K6` muestran Q173 pendiente. El primer preflight terminó antes de iniciar el servidor por un bug del runner (`KeyError: config_sha256`). Enmienda01 corrigió la ruta del SHA de config, el SHA esperado del launcher y agregó recibos incrementales de hash; script `py_compile` PASS. Se requiere actualizar/readback de la enmienda en Sheets y repetir full-hash/live preflight antes de inferencia.

### Checkpoint de sync — 2026-11-15T06:56:52+00:00

Enmienda01 leída de vuelta en Google Sheets; `Resultados!A496:AH496` conserva el estado de preflight fallido y `Modelos locales por peso!J6:K6` sigue en N/D pendiente. Próximo paso exacto: revalidar gates/lock y ejecutar el preflight completo con hash de cinco shards; Q173 8K×3 sólo si pasa. ASUS debe aparecer asignada al mismo PID junto con PNY al iniciar el perfil.

### Checkpoint amendment02 — 2026-11-15T07:10:38+00:00

Attempt02 fully verified all five shards, then stopped before live gates because the pinned wrapper SHA had a typo. The observed wrapper digest matches the historical Q206 receipts and its 2026-10-29 mtime. No server or GPU compute was started. The corrected wrapper pin and failure are preregistered; sync/readback before retry.

### Checkpoint de Sheet — 2026-11-15T07:11:48+00:00

Attempt02 y amendment02 quedaron leídos de vuelta; valores y formato correctos. Siguiente paso: gates frescos y full preflight corregido.

### Checkpoint preflight PASS — 2026-11-15T07:22:24+00:00

Full asset hashes and live gates passed; Sheets values and formatting read back. No inference has started. The next action is the preregistered 8192×3 ladder point after a fresh live gate check.

### Q173 context 8192 checkpoint — 2026-11-15T07:38:03+00:00

First ladder point passed on both ASUS and PNY. Effective P/D 393.593/31.023 tok/s (n=3; provisional). Server readiness 477.877 s, not cold/hot. Sheet readback is complete. Next exact point: 32768×1 after fresh gate check.

### Q173 context 32768 checkpoint — 2026-11-15T07:42:23Z

PASS dual ASUS+PNY, 32.798 prompt tokens,128 output: effective E2E prefill540,474 tok/s; decode26,058 tok/s; TTFT60,684s; readiness101,341s (no cold/hot classification). Same compute PID on both cards; OOM0, cleanup PASS. Google Sheet row496 and inventory row6 were read back with values/format intact; receipt SHA-256 `3710e04e36b6f8e1473769e59e68692a8de850892dac88c9e9445c029eed3c7f`. Provisional equal-context mean for completed 8K×3 and32K×1: P467,033/D28,540 tok/s. Next: fresh gates, then65536×1 dual-GPU.

### Fresh gate before 65536 — PASS, 2026-11-15T07:57:07Z

Full hashes of five shards (276,626,308,260 B) and five support artifacts passed. Both physical GPUs were present; helper, ASUS quarantine, bidirectional P2P, gpu_unlock, no-server, port-free and memory/OOM checks passed. MemAvailable115.95GiB; output volume free25.63GiB. Receipt `receipts/preflight-context65536.json`. Proceed only with preregistered 65536×1 dual-GPU point.

### Q173 context 65536 controller failure — 2026-11-15

The 64K request produced no result. The Codex-side `run_q173.py` controller session vanished while the separately `systemd-run`-launched Maya service remained. Maya reached API readiness after≈5m20s; systemd terminated it at its 2h `RuntimeMaxSec`, marking `Result=timeout`. No request JSON or events were produced. GPU process had used ASUS+PNY, then both were clear; memory recovered to≈116.2GiB. Failure receipt `receipts/q173-context-65536-failure.json`; no 64K metric is added to the average.

Do not restart Q173 through a foreground Codex exec session. Next: preregister and implement a detached systemd worker for the entire controller, with a worker stop hook that always stops its child Maya unit; verify the fake-job detached lifecycle and cleanup without GPU, record/read back its receipts and Sheet, then retry 64K only if the detached worker succeeds.

The 64K no-result/orphan record was synchronized/read back in Results row496 and inventory row6 notes; no numeric averages were changed. Readback receipt SHA-256 `4e13dbce0b8de52e670948eadd6bf5ae3658329ee0f49e4dbec15e7a23d0eebb`.

- 2026-11-15T14:58:00+00:00 — Q209 detached-controller remediation preregistered before testing. Replaced the foreground-only Q173 run path with a token-checked user-systemd worker launcher, bounded outer controller (3900s/8GiB) and Maya child (3600s/96GiB, no swap, OOMPolicy=kill); exact identity-gated ExecStopPost cleanup writes durable receipts. Preregistered CPU-only fake-job lifecycle gate `Q209-CONTROLLER-DETACHED-CPU-01`: launch returns immediately, controller must keep running after caller exit, then hit its 8s cap and stop only its fake child. No GPU/model/inference calls. Sheet sync/readback is required before the smoke; GPU retry remains blocked until PASS. Runner SHA `a4f54ecec98bfce1f9fd01f2c233f2367e8e904a2a605015e1d49fbe9fd2d411`, detached launcher SHA `a2a4ff0f19842c3f34fa3d8ce8e5479be894fe74de686aff92dfb192b5f9a010`, cleanup SHA `05dd9013063ed2a29d0442e5dd2dd11de1fba08a7b6cb0770a789cc9bdb49853`, smoke SHA `2a5e419ca620e0228d55ee3a95543a3b9c4b82c7012406a12579389be698cfab`. Prereg SHA `1e4fa706714463eb754981e963c7ca96739b1be982f49888f92c5ff2a68fc873`.

- 2026-11-15T15:00:10+00:00 — Q209-CONTROLLER-DETACHED-CPU-01 syntax gate PASS: `py_compile` succeeded for the runner, detached launcher, cleanup hook, and lifecycle smoke script; no GPU/model used. Receipt `artifacts/evaluacion-modelos-llamacode/Q-20261115-MAYA-DS4SPLIT39-Q173/profiles/maya-xs-iq1s-pny-ds4split39-q173/receipts/detached-worker-syntax-gate.json` SHA-256 `54f29e9e8d290bf14d99f9c80491baa3c2c2b30fcac8fbbbed33d6d923cf9507`. Sheet preregistration was already read back; immediately syncing this test result before the lifecycle test.

- 2026-11-15T15:02:58+00:00 — Q209-CONTROLLER-DETACHED-CPU-01 amendment01 syntax gate PASS after registering the lock re-check and identity-limited emergency cleanup. `py_compile` passed for all four current files; lock Q202 verified; no GPU/model used. Receipt `artifacts/evaluacion-modelos-llamacode/Q-20261115-MAYA-DS4SPLIT39-Q173/profiles/maya-xs-iq1s-pny-ds4split39-q173/receipts/detached-worker-syntax-gate-amend01.json` SHA-256 `e39532d3106fd1f9e5fa5ea63915cf5c0c11d4e38a01bb1792a5d6c2bbded500`. The amended preregistration was synchronized and read back from `Resultados!E496/AD496/AF496`; next is the two-stage CPU-only systemd lifecycle smoke.

- 2026-11-15T15:05:45+00:00 — Q209-CONTROLLER-DETACHED-CPU-01 PASS. The systemd-run caller returned immediately; the fake controller continued after that process exited, hit its registered 8s timeout, and `ExecStopPost` stopped only the child whose exact Q209 smoke description matched. Worker result=timeout; child inactive; no model/GPU or other unit touched. Summary `artifacts/evaluacion-modelos-llamacode/Q-20261115-MAYA-DS4SPLIT39-Q173/profiles/maya-xs-iq1s-pny-ds4split39-q173/receipts/detached-worker-cpu-smoke-summary.json` SHA-256 `2c74f6586821c1bae756577ebeb411944b4c5c8a6b8b82f7ce89e29430fc4cf7`; worker receipt SHA `00558c6a0d913473e87cfd5ed40e2e1506a5eb2b7c6e7869b99c36c6266edbe7`; cleanup receipt SHA `fedd48f7e51a51926d9f9b3f9eb4c23c1e404a323039cc4ce3a301737244c2cc`. Next: sheet update/readback, then one detached bounded retry of Q209 64K; 128K/261888 remain gated.

- 2026-11-15T15:05Z — Google Sheet final correction/readback for Q209-CONTROLLER-DETACHED-CPU-01 PASS: Results row496 and Modelos locales por peso row6 notes now carry the detached-worker smoke status; numeric P/D means unchanged. Readback receipt SHA-256 `1bc43d1a9d2f398077c9ac16792bfe1f03911ff13063822c85b39a669f6dd491`. Cleared the failed state of only the generated fake worker unit; fake child was already inactive. No model service or GPU used by this smoke.

- 2026-11-15T15:12Z — Q209 prelaunch cached-preflight refresh PASS: reused the previous five-shard full-SHA result only after all shard path/device/inode/size/mtime_ns snapshots matched and all five supporting files rehashed to pinned SHA; fresh helper, ASUS quarantine, P2P, gpu_unlock, port, memory, both GPU UUIDs and zero other compute apps/inference servers passed. MemAvailable 124,667,830,272 B; output volume free 27,512,774,656 B. Did not launch inference. Receipt `profiles/maya-xs-iq1s-pny-ds4split39-q173/receipts/preflight-cached-refresh.json` SHA-256 `4a9c769a8b9c46f5dc66069cb701b584a7f7e878628a7ec3abdd5682196d96f5`; Google Sheet readback `sheet-preflight-cached-refresh-corrected-readback.json` SHA-256 `abfbfd45d02fe5a9545f4b8b270b735a799c34d3966db24a082d6e401f4c1f53`. Next: one detached bounded Q209 Q173 64K attempt a02; no new full model hash scan.

- 2026-11-15T15:12:28Z — Q209 Q173 context65536 retry attempt a02 launched with `launch_detached_q173.py` as independent systemd user worker; launcher returned in <1s while worker stays active. Worker unit `q209-maya-q173-pp65536-worker-a02`, engine unit `q209-maya-q173-pp65536-a02`; both active. At initial snapshot controller RSS≈14MiB, Maya service MemoryCurrent≈6.67GiB and rising during startup; no Q173 metrics yet. Outer bounds3900s/8GiB; engine bounds3600s/96GiB, swap0, KillMode=cgroup, exact ExecStopPost. Launch receipt SHA-256 `986a97b294972f2dee5162929f256ac2a4ed6bf01f9007f7cd6b17f4edace974`.


## Q209 cierre final — 2026-11-15

Q173 ladder completado hasta261888;523904 excluido por límite del usuario. La medición final corrió bajo worker y engine user-systemd independientes de Codex y ambos terminaron exit0; postflight confirmó servicios/puerto/GPU compute limpios y OOMKill0. Promedio equiponderado descriptivo de cinco contextos P514.864/D19.573 tok/s; Q173 no puntúa calidad ni cold/hot init. Google Sheet actualizado/readback PASS. Recibo consolidado `receipts/q173-context-261888-completion-amendment.json`.

**Regla de operación a futuro:** una inferencia larga nunca debe ser hija de un `exec` interactivo ni depender de que ChatGPT/Codex siga abierto. Lanzar como worker `systemd` detached con límites de tiempo/memoria, identidad y limpieza comprobables; el lanzador solo inicia y registra. Al volver, consultar el estado del worker y verificar el postflight antes de otro uso de GPU. Esto reduce el riesgo de procesos huérfanos; no identifica la causa raíz de los cierres de Codex.
