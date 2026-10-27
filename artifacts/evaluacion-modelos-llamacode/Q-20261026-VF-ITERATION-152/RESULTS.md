# Q152 results — Gyro-Coder-L v1.1 dual-RTX3090 BCB-Hard-8 screen

**Final screen: 0/8 passed; no-go for the tested unbounded-reasoning request profile.** The exact candidate completed all eight requests (8/8 transport, zero sandbox errors), but six responses exhausted the 6,144-token completion limit in `reasoning_content` without final code; the other two returned code that failed the grader. This is a profile-specific screen, not proof that the model is generally inferior.

The test ran on the pinned Agention CUDA build from Q160 (`9aa51ce4fdd3435a91531ffe16a17414ccc6dc6f`) and both RTX 3090s. Candidate SHA-256 was verified against Hugging Face LFS: `377d5aa5b473a89b4d0d0c9fbd54fd8fcc46da19c16fc881860577189c1403df` (83,975,624,672 bytes). Context 8,192; split `1,1`; reasoning on; seed 4242; conservative sampling; one request at a time. Detailed run: `runs/gyro-coder-l-screen-seed-4242-20261027T033641Z/` and receipt `receipts/screen-run-20261027T033641Z.json`.

Median request wall time was 103.9 s, median prefill 436.3 tok/s, and median decode 59.5 tok/s. Decode includes reasoning tokens and must not be reported as useful-code throughput. The model generated 45,190 completion tokens across the screen. Minimum host `MemAvailable` was 104.06 GiB, minimum swap free 3.3 GiB, peak memory PSI some/full avg10 3.04%, and the global OOM-kill counter did not increase. Peak candidate VRAM was 15,304 MiB on GPU0 and 14,322 MiB on GPU1. No artificial RAM/swap caps were used.

Cleanup sent SIGTERM only to the owned server process group and confirmed it exited. Port 18382 had no listener afterward; the supervisor's `port18382FreeAfterCleanup=false` reflects a TCP `TIME-WAIT` socket, not a surviving server. No PeritoSoft or other inference server was active at preflight, so nothing unrelated was terminated; the desktop GUI remained untouched.

**Protocol issue found:** the Q89 runner records `reasoningBudgetTokens=2048` in result metadata for both arms but only sends `reasoning_budget_tokens` in the HTTP body for `arm=astra`. Q152 used `arm=swift`, so its request did not contain the declared budget. Q161 explicitly sent 2,048 budget tokens with the same model, runtime, seed, fixture, and other settings; it passed 1/8 and failed the preregistered ≥4/8 gate. The bounded profile also closed no-go, with no more seeds justified. Q152 remains the unbounded-request profile result.

Do not add Q152 to a productive profile or infer superiority over ASTRA/SOL from this one-seed screen. ASTRA, SOL, PeritoSoft data/configuration, and unrelated GUI processes were not modified.

## Revalidación Q158/Q159 · 2026-10-27T02:16:29Z

- Q158 probó la imagen GHCR oficial fijada `sha256:0f0547624f92df823ef7bdbfc1e497a3674cebeaaaefb2c59012ba1716799fc6` con `NVIDIA_DRIVER_CAPABILITIES=all`; `/app/llama-server --list-devices` devolvió `(none)`. La imagen se retiró después; no hubo modelo/inferencia.
- Q159 inspeccionó el fork oficial en `dc255f2a4b6e4211b555b0c05260b2523281f314`: los tipos registrados incluyen TQ2_0/TQ2_T/TQK6/TQK7, no TQ3_0. Se paró antes de build y GPU.
- Q152 queda bloqueada por soporte del formato exacto. No es una evaluación de calidad. Recibos Q158/Q159 enlazados en WORK_QUEUE.md.

## Reapertura Q160 · runtime CUDA y descarga · 2026-10-27

- El gate de filename de Q159 fue corregido: `TQ3_0` en el nombre del GGUF es una clase de tamaño Hub, no el tipo interno. El build CUDA fijado de Agention enumera ambas RTX 3090; véanse los recibos Q160.
- La descarga del artefacto exacto se reanudó con `hf-xet` autenticado hacia `/media/cristian/Disco local/Models-eval/Q152-GyroCoderL/`. El parcial observó 5,009,312,296 B a las 02:48:10Z y 5,161,540,396 B a las 02:48:25Z; el tamaño esperado es 83,975,624,672 B. Recibo: `receipts/download-progress-20261027T024810Z.json`.
- Aún no se verificó SHA-256; no se inició el servidor, request de inferencia ni benchmark. El hash completo es gate obligatorio. La pausa del primer intento no dejó un parcial utilizable; el intento Xet actual transfiere bytes.
- La comprobación solicitada de PeritoSoft/`llama-server` no encontró procesos o listeners objetivo; no se envió ninguna señal. ASTRA, SOL, archivos/configuración de PeritoSoft y GUI permanecen intactos.
- Antes de iniciar inferencia quedó preregistrado `scripts/q152_supervise_bcb.py` (SHA-256 `352cae1540078f7824b3cac8042a42cda70fba66176a1e4332600895d7e6faaf`). Verifica hashes/puerto/GPU, exige el proceso propio en ambas tarjetas, toma muestras de RAM/swap/PSI/OOM/VRAM cada segundo y limpia sólo grupos de procesos que el mismo script lanzó. No fija límites de memoria. A las 02:52:02Z el GGUF parcial era 12,249,554,610 B; hash final e inferencia pendientes.

- Prueba offline del supervisor (2026-10-27T02:56:31Z): sintaxis, dos GPU visibles, puerto libre, ausencia de servidor externo, muestreo, umbral PSI sintético y limpieza aislada de grupo de procesos pasaron; no hubo inferencia ni uso de GPU compute. SHA del script `352cae1540078f7824b3cac8042a42cda70fba66176a1e4332600895d7e6faaf`. Recibo: `receipts/supervisor-self-test-20261027T025631Z.json`.

- Control Q97 revalidado antes de correr candidato (2026-10-27T03:04:50Z): ASTRA 2/8, transport 8/8, sandbox 0, final vacío 0; IDs aprobados 870 y 310; artifact SHA-256 `b083f22b0965864c6393b5af28cdf0683a7d3d345ae63687a961fc2e7d919d97`. Es un control histórico con runtime/perfil distinto. Recibo: `receipts/control-revalidation-20261027T030450Z.json`.

- Revisión final del supervisor (2026-10-27T03:12:16Z): se añadió detección inmediata de salida del server durante el grading para no esperar el timeout HTTP; nuevo SHA `72acdbb1b68e897f09ca6473b1aa7438ca0bba8ff1ebe5a70aa48e81edcf2ddf`. Sintaxis, gate PSI y terminación de grupo propio volvieron a pasar. Recibos: `receipts/supervisor-preregistration-20261027T031216Z.json` y `receipts/supervisor-self-test-20261027T031216Z.json`.

- Descarga final verificada (2026-10-27T03:30:33Z): archivo `Qwen3.8-Flash-Next-Gyro-Coder-L-TQ3_0-v1.1.gguf` mide 83,975,624,672 B; el recibo inicial guardó un valor truncado de 61 caracteres y quedó supersedido. La revalidación local con `sha256sum`/`hashlib.sha256` coincide con el LFS SHA oficial `377d5aa5b473a89b4d0d0c9fbd54fd8fcc46da19c16fc881860577189c1403df` (64 hex); tamaño 83,975,624,672 B. Server/inferencia/benchmark aún no iniciados. Recibo: `artifacts/evaluacion-modelos-llamacode/Q-20261026-VF-ITERATION-152/receipts/model-sha256-correction-20261027T033402Z.json`.
