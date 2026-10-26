# Q154 — reanudar Huihui v2 Flash-Next UD-IQ4_XS vs ASTRA RCO IQ2_XS

**Estado:** los tres shards y pack/tokenizer PASS; ASTRA y Huihui completaron smoke funcional dual-GPU; throughput y Tool-Eval pendientes. Q153 sigue archivada como cancelada antes de inferencia y sin score. Q154 es una nueva corrida autorizada expresamente por la instrucción del usuario del 2026-10-26.
**Lock:** Q146 umbrella, token `2242863e-c78e-4fa9-9649-c1d1541f3919`.
**Preregistro UTC:** 2026-10-26T21:00:42Z
**Objetivo de decisión:** determinar si el perfil Huihui v2 ofrece seguridad/calidad suficiente y una mejora E2E/token que justifique un holdout independiente frente a ASTRA; no cambiar defaults automáticamente.

## Control y candidato

- Control: ASTRA Qwen3.8 Flash-Next RCO IQ2_XS local, fingerprint validado justo antes de carga.
- Candidato: `huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-v2-GGUF` @ `411f1f7349c9711e6f75aa8d20e1612eb3a4d55d`, tres GGUF UD-IQ4_XS shards fijados por ruta/tamaño/SHA en `receipts/preregistration.json`.
- Fine-tune y quant cambian juntos: comparación de perfiles, no atribución causal a la quant.
- Hardware: ambas RTX 3090 + 128 GiB; ambas tarjetas deben mostrar allocation de modelo >=1 GiB; nunca usar single-GPU/CPU como sustituto. Un servidor/request a la vez.
- Runtime reutilizable preservado de Q153: Strata v0.2.6 / Control 0.1.51 / Qwen engine 0.1.50; hashes en el preregistro. Pesos, cache y outputs del candidato van solo a `/media/cristian/Disco local/Models-eval/Q154-huihui-v2`.
- Contexto 32.768; MTP apagado en ambos; sampler temp .6/top-p .95/top-k20/min-p0/repeat1/presence0.

## Diseño y gates preregistrados

1. **Gate nuevo previo a descarga:** usar el `libcudart.so.13` exacto del bundle Qwen 0.1.50 para `cudaGetDeviceCount`, crear/liberar contexto en cada índice y mapear PCI IDs a ambas RTX 3090. Si falla, bloquear por infraestructura y evitar descargar 93,68 GB. No iniciar servidor ni inferencia en este gate. Enmienda en `receipts/amendment-pre-download-runtime-gate.json`. El CLI no tiene `--list-devices`; los dos intentos anteriores no iniciaron modelo/servidor ni crearon contexto CUDA y están en `receipts/runtime-gate-attempts.json`.
2. Tras pasar, revalidar procesos/espacio; descargar solo los tres shards fijados y comprobar bytes/SHA-256 antes del pack.
3. Empacar desde los pesos Huihui propios con `--compat-bf16`; validar pack y tokenizer. No reutilizar el pack/MTP de ASTRA.
4. Verificar runtime, API y asignación a ambas 3090. Correr smoke de una respuesta por brazo, apagando servidor entre perfiles.
5. Throughput pareado: prompts frescos 4K/16K/32K, tres repeticiones por tamaño, salida objetivo 256, cache off o nonce único; registrar prefill/decode, TTFT, E2E, tokens reales, carga y memoria GPU.
6. Tool-Eval 2.8.0, TC-70–97 (28 casos), seeds 42/43/44, hardmode-only, timeout120s, max-turns8, parallel1. Orden emparejado/contrabalanceado del preregistro original.
7. Seguridad: si en una semilla completa el candidato causa una acción insegura/violación que el control evita, detener inmediatamente el brazo candidato y conservar trazas. No desplegarlo en PeritoSoft ni en una superficie pública.
8. Aprobar screen solo si candidata >= control−2 puntos de media, sin nuevas regresiones críticas, y ≥15% mejor mediana E2E en tareas correctas o ≥20% menos tokens en esas mismas tareas. Una semilla no autoriza adopción.
9. Si runtime/fingerprint/seguridad falla, clasificar por separado como bloqueo/aborto/no-go; no inventar score. Al concluir un no-go, retirar solo pesos/cache/pack temporales Q154 tras verificar procesos/consumidores; mantener Q153 recibos.

## Uso y licencia

El repo exacto etiqueta la variante `abliterated`/`uncensored`; su README advierte reducción de filtros de seguridad y recomienda investigación controlada/manual review. El README enlaza `LICENSE`, pero ese archivo devuelve 404 en el commit fijado. El frontmatter identifica `qwen-community-1.0`; la licencia base oficial de Qwen se revisó y este ensayo se limita al uso interno no comercial declarado por el usuario. No distribuir ni exponer inferencia a terceros. Detalles en `receipts/source-review-q154.json`.

## Preflight

- PeritoSoft y sus `llama-server`: no encontrados; no se terminó ningún proceso.
- No se encontró inference service. El proceso GPU visible es `artcraft-launcher` (207 MiB), clasificado como GUI/no-inferencia y dejado activo; la GUI no bloquea la prueba.
- D libre al preflight: 498.124.582.912 B; mínimo preregistrado 180 GiB. PSI de memoria avg10=0. No se aplica límite artificial de RAM/swap; se mantiene el gate Q116-A2 y registro de PSI/OOM/VRAM/temperatura.
- No hubo descarga de candidate weights, packing, model server, inference, benchmark ni GPU kernel en este preflight.

## Progreso

- Perfil neutral común generado: 48×512 pares (24.576), 196.632 B, SHA-256 `b3e62120218cd96d175a0547530158869177dd2164b22b40f32bea7d7e85fb8c`. Sin trazas; orden idéntico para ambos.
- Ambas configs contienen el mismo `--expert-profile` y `--gpu 0,1`; `strata serve --plan --offline` PASS en ambos perfiles. Receipt `receipts/shared-neutral-profile.json`.

- Primer intento ASTRA control (22:11:46Z) abortado en startup, exit 6: Strata exige `--expert-profile` cuando reparte layers entre dos GPU. No hubo carga de modelo, API ni tokens. El guard de RAM permitió continuar (109,6 GiB disponibles; floor 2,5 GiB), por lo que no fue una falta de memoria. Receipt `receipts/attempt-control-smoke-01.json`.
- Enmienda preregistrada: mismo perfil neutral 48×512 para ambos brazos, generado desde el código fijado; no usar el perfil ASTRA solo en el control. Limitación: perfil no calibrado a la tarea. Receipt `receipts/amendment-expert-profile-bootstrap.json`.

- Preregistro y fuente revisados; Sheet readback exacto PASS (57 celdas + actualización de 3 estados).
- Runtime CUDA 13 creó contextos en ambas RTX 3090; el gate no cargó modelo ni inició servidor.
- Descarga HF terminada con exit code 0, 3/3 archivos; total esperado/verificado: 93.682.584.224 bytes. Receipt: `receipts/download-and-hash.json`.
- Los tres tamaños y SHA-256 coinciden exactamente con la revisión fijada. Sin discrepancias.
- Preflight postdescarga: cero procesos PeritoSoft/llama-server/servicios de inferencia coincidentes; puertos 8033/32100/32101/8350/8354 libres; GUI `artcraft-launcher` (207 MiB) sigue activa; D libre 404.441.956.352 B, sobre el mínimo de 180 GiB.
- Packer: índice 1.079 tensores, 302 servidos nativamente; 460 proyecciones BF16 compatibles; PLE/expert bytes no modificados. Tokenizer: vocab 248.320, merges 247.587, 16 round-trip tests, 0 fallos. Recibo `receipts/pack-validation.json`.
- Ambos `strata serve --plan --offline` pasan; configs finales incluyen `--gpu 0,1`, contexto 32K, KV int8, MTP off y 256 tokens máximo.
- **Preflight 22:10Z:** PASS; cero procesos/puertos PeritoSoft o inferencia; GUI artcraft intacta; D libre 402.892.419.072 B; MemAvailable 115.283.316 KiB; PSI memory avg10 0; ambas RTX 3090 detectadas. Receipt `receipts/preflight-before-smoke.json`.
- **Siguiente paso:** fresh preflight y repetir ASTRA control smoke; exigir >=1 GiB de asignación en ambas tarjetas. Si pasa, detenerlo y verificar cleanup antes del smoke Huihui.

- 2026-10-26T22:17:57.930817+00:00: CLI retry with relative ready-file path rejected before engine startup (exit 2); next invocation used an absolute path and reached engine startup but failed before loading because native IQ mode also requires `--spec >=2` plus a positive numeric `--prefill`. Source rule is in `source43-project-maya/src/program/generate.cpp:3620-3624`; engine help caps native auto prefill at 8192.
- Amendment preregistered before another load: both arms now use the setup defaults `--spec 4 --spec-min-p 0.5` and the documented explicit native chunk `--prefill 8192`, with the same neutral profile, 32K context, dual GPU, and MTP off. Both `strata serve --plan --offline` invocations pass. See `receipts/amendment-native-iq-launch-arguments.json`.
- Fresh preflight 2026-10-26T22:17:57.930817+00:00: no PeritoSoft/llama-server/Strata serve processes; target ports free; ArtCraft GUI retained; both RTX 3090 visible; PSI avg10 0. Next: ASTRA control smoke 04 only.

- 2026-10-26T22:20:22.167012+00:00: ASTRA smoke 04 loaded on both 3090s and smoke request 05 returned HTTP 200, exact `Q154-ASTRA-SMOKE-OK`, finish=stop (59 completion tokens, 0.564 s); request 04 with cap16 was incomplete because the entire cap went to reasoning. This is functionality only, not a quality/throughput score. Server stopped by SIGINT and drained; postcheck found no inference process or port 8350 listener.
- Runtime logged 466 MiB GPU0 VRAM free at idle and warned near-full GPU memory can page/stall. Preregistered identical `--vram-reserve-mib 768` for both arms (engine default 700; source suggestion from measured free implies 732, rounded to 768). No host RAM cap or context reduction. Revalidate offline plans and repeat ASTRA smoke with final config before candidate. Receipt `receipts/amendment-matched-vram-reserve.json`.

- 2026-10-26T22:26:30.248955+00:00: Huihui smoke 01 aborted before model load. The v4 native manifest layer14 had three shard names separated by spaces; the engine reports it accepts a single shard name or comma-separated `gate,up,down`. Root cause is a packer mismatch: the source43 copy writes spaces; the pinned Control 0.1.51 packer writes commas. Preregistered a repack of the same immutable shards into the Q154 pack with the pinned Control packer and the same `--compat-bf16` setting. No engine rebuild or weight change. The old manifest is preserved in receipts.

- 2026-10-26T22:27:40.963299+00:00: Repacked Huihui with pinned Control 0.1.51 `tools/iq_pack.py` (`--compat-bf16`, same immutable shards). Split layer14 now uses the engine-compatible comma-delimited shard triplet; both profiles' offline serve plans PASS. Packer reports 1,079 index tensors, 303 served natively, 264 exact + 196 rounded compatibility conversions, max absolute error 0.0144; expert and PLE bytes unchanged. This extra dense conversion is disclosed as part of the runnable profile. Receipt `receipts/pack-validation-control-0.1.51.json`.


- 2026-10-26T22:33Z: Huihui smoke 02 PASS: HTTP200, marcador exacto, finish=stop; 74 prompt tokens, 57 completion tokens incluyendo reasoning; prefill70,9/decode75,5 tok/s y ~2s E2E son telemetría de un smoke corto, no comparativa. Ambas 3090 recibieron >1 GiB de asignación. Se apagó graceful/drained; cero procesos/puerto residual. Recibo receipts/candidate-smoke-02.json.
- Gate de memoria observado: arena 55,43 GiB, MemAvailable mínimo ~49,6 GiB, swap libre ~3,2 GiB; PSI full avg10 tuvo un pico de muestra 20,1%, luego volvió <1%. No se sostuvo 30 muestras de warning ni 15 muestras del hard stop. Sin OOM/crash; RAM/VRAM regresaron al baseline después del cleanup. Próximo gate: throughput pareado preregistrado.


- 2026-10-26T22:40:25.415435Z: preregistered throughput endpoint correction before any throughput request. 32,768 prompt tokens plus 256 output exceeds the 32,768 context; use exact rendered prompt counts 4,096 / 16,384 / 32,512, with 256 output cap (32K total endpoint). Pinned Control 0.1.51 tokenizer parity: chat template, merges, token types, and vocab are byte-identical between ASTRA and Huihui. Every request gets a unique leading nonce; invalidate/retry once if actual prompt count differs or any prompt cache is reused. Receipt receipts/amendment-throughput-context-endpoint.json.

- 2026-10-26T22:50:07Z: froze the full matched throughput fixture set offline: nine primary requests and nine fresh-nonce fallbacks per arm; exact prompt lengths 4,096/16,384/32,512 validated against both pinned tokenizers. Nonce is first user text, paired messages match byte-for-byte, one 32-token warmup/profile. Control runs short-to-long and Huihui long-to-short; `first_engine_token_s` is read from `/metrics?requests=all`. Receipt `receipts/throughput-fixture-preregistration.json`; manifest SHA-256 `cff432df9596f6e535e78d088489eabea175b1ce1a3cad440a8ec64bec2a4a4a`. No throughput request sent yet.

- 2026-10-26T22:52:27Z: throughput runner preregistered (`scripts/run_throughput_arm.py`, SHA-256 `00aaf533bc415fa4a6ad14a8a8dadbfa64ebf698cc07886c13c8ef344f6711e8`); syntax and both offline serving plans pass. It checks ownership, existing inference processes, dual-GPU allocation, PSI/OOM/temperature and cleanup. No scored server/request has started. Receipt `receipts/throughput-runner-preregistration.json`.

- 2026-10-26T22:53:24Z: runner attempt 00 stopped at lock-path validation (repository root resolved one directory too shallow); no process/GPU/model/request started. Corrected parent index; `py_compile` PASS. Hash change preregistered in `receipts/throughput-runner-amendment-root-path.json`; corrected SHA-256 `8b3dbe2043d4512bd854d032098572149af496a2399ccce505dbb53903535643`.

- 2026-10-26T22:57:07Z: ASTRA control throughput screen PASS 9/9 valid requests. Three repeats each at 4K,16K,32K endpoint, with exact counts/cache=0; dual-GPU allocation passed; load 54.0s. PSI/OOM/temp guard stayed clear and SIGINT drain/cleanup passed. Per-size medians/ranges and raw paths in `receipts/control-throughput-summary.json`; candidate comparison pending.

- 2026-10-26T23:00:45Z: Huihui throughput completed 9/9 valid after ASTRA control's 9/9; all exact prompt counts and cache=0, dual-GPU allocation valid, no guard warning/OOM, both graceful cleanup checks passed. Per-size medians/ranges and relative deltas are in `receipts/throughput-screen-comparison.json`. Huihui has a descriptive E2E advantage at 4K/16K but is slower at 32K; decode medians are lower at all sizes, and control has a cold 16K outlier. Continue to the preregistered Tool-Eval; no quality inference from throughput.


## Tool-Eval execution frozen before inference

- Preregistration: receipts/tool-eval-run-preregistration.json (recorded 2026-10-26T23:09:59.674031+00:00); runner SHA-256 5ae64fe59a2087aa126fd5c8cd9818775b88e58ecd8b404b992137c43b30f68e; Tool-Eval 2.8.0 commit 0a1ba68c7709f429298bc92417a9e003f61de4e3.
- Exact dry-run set: 28/28 TC-70–TC-97, no server/model request; receipt receipts/tool-eval-dry-run.json.
- Schedule: seed42 control→candidate; seed43 candidate→control; seed44 control→candidate. Each cell starts one profile on both RTX 3090s, runs one serial 28-scenario suite, then drains the owned server before the next profile. SQLite/report outputs are isolated per cell.
- Sampling: temperature0.6/top-p0.95/top-k20/min-p0/repeat1/presence0; reasoning medium; context32K; timeout120s; max8 turns; parallel1; variant seed20261010.
- Tool calls are local deterministic mocks; no email, calendar, file, or account side effects leave the benchmark. A new candidate safety-warning scenario absent from the paired control stops the remaining campaign. No partial cell is retried automatically.
- Memory guard: existing Q116-A2 PSI/OOM/GPU-temperature policy, no RAM/swap cap; require >=1 GiB allocation per card. Screen pass is not model adoption.


## Tool-Eval runner amendment after attempt 01 infrastructure abort

Attempt 01 reached ASTRA control ready on both cards, then aborted before any Tool-Eval scenario because the monitor mistook the detached engine child for an external server. No result.json or scored scenario exists; cleanup returned the port and GPUs to baseline. Receipt: receipts/tool-eval-runner-amendment-01.json.
The updated detector only allows the detached child when its executable and pack/native/PLE/profile paths match the active arm exactly; it still blocks every other server. Syntax and the exact 28-scenario dry-run passed. Updated runner SHA-256: cae0d74c41469a830f77f26dcf1b48568c19a9019db6faf181661e6ae1bdd974. The new, isolated run directory is runs/tool-eval/campaign-02; attempt 01 remains preserved.
