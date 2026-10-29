# Q180 — resultados

Estado final (2026-10-29 06:55Z): Q180 A03 completado en 2×RTX 3090, layer split 1:1. Q172 seeds42/43/44: 0/100 cada una (28/28 fallos por agotamiento del techo de 16.384 tokens de razonamiento sin tool call/respuesta); safety gate PASS, warnings vacíos en las tres. Ladder de contexto completada hasta 261.888 tokens; init proceso→health 5,194 s y relanzamiento inmediato→health 5,138 s. El perfil no es apto para coding/agentes con esta configuración y no se promueve frente a SOL/ASTRA; TPS son mediciones de fixture y no reparan el fallo funcional.

Observación de recursos durante Q172 (~04:40Z): `free -h` registró 98 GiB disponibles y 6,3 GiB de swap ocupado; `vmstat 1 3` mostró intercambio inicial de 29/63 KiB y luego `si=0`, `so=0` en ambas muestras siguientes. No hay evidencia de paginación sostenida que explique los timeouts.

Lock: Q146 / `2242863e-c78e-4fa9-9649-c1d1541f3919`. Prerregistro previo a cualquier descarga/build/benchmark: `receipts/preregistration.json`.

El reintento conserva exactamente el perfil preregistrado. El runner recibió un `--help` adicional durante una comprobación de CLI; no interpreta argumentos y ejecutó el mismo `main()` sin alterar modelo, argv del servidor, harness, seeds ni gates. Se registra esta incidencia de lanzamiento para auditoría en `receipts/q180-clean-rerun-progress-20261029.json`. No tomar decisiones con resultados parciales.


### A03 limpio — Q172 seed42 completo (2026-10-29T05:04:47Z)

JSON completo: `runs/q172-seed42.json`; `status=completed`, 28/28 escenarios, **0/100** (0/56 puntos; 28 fallos). Cada caso agotó 16.384 tokens de razonamiento, sin llamada a herramienta ni respuesta final, en aproximadamente 114–115 s. El `safety_gate` global figura `passed=true` y `safety_warnings=[]`; esto no es un fallo crítico de seguridad reportado por el harness, pero sí un fallo funcional grave de tool-use/responsividad. Seed43 se lanzó conforme al prerregistro; seed44 queda condicionado a que seed43 también complete y pase el gate. La ladder y cold/hot init aún no comenzaron. No actualizar `Resultados` con agregado final hasta cerrar el perfil completo.

### A03 limpio — Q172 seed43 completo (2026-10-29T05:58Z)

JSON `runs/q172-seed43.json`: `status=completed`, 28/28, **0/100** (0/56; 28 fallos). Igual que seed42, los 28 escenarios llegaron a 16.384 tokens de razonamiento sin tool call ni respuesta final, en ~114–115 s por caso. `safety_gate.passed=true`, `safety_warnings=[]`. Como seed43 completó y pasó el gate, el prerregistro habilitó seed44, ya iniciado. Seed42 y seed43 son resultados funcionales consistentes, no evidencia de una regresión frente a control.


2026-10-29T02:39:43Z: tokenizador Qwen/Qwen3.6-35B-A3B fijado a revisión 995ad96eacd98c81ed38be0c5b274b04031597b0; tokenizer.json y tokenizer_config.json descargados a D y hashes verificados. Sin GGUF, build ni GPU todavía. Recibo `receipts/tokenizer-download.json`.


2026-10-29T02:53:19Z: GGUF completo en D; tamaño 22,853,663,008 B y SHA-256 verificado `55983c5a75a1ab969824077b3bb3de4146e82a9234072b48ad4e8f92ad3fe9f1`. No inference, build ni uso de GPU. Recibo `receipts/model-download.json`.

2026-10-29T02:54:43Z: `Inventario de modelos!A19:R19` actualizado con modelo, variante, ubicación Linux, tamaño/hash, GPU/runtime planeados y campos N/D para métricas aún no medidas. Se conservó la fila existente y su formato, sin duplicar el modelo. Lectura de vuelta verificó todas las 18 celdas. Recibo `receipts/google-sheet-q180-inventory-sync.json`.

2026-10-29T02:57:00Z: fuente `ggml-org/llama.cpp` clonada en D y `HEAD` verificado como `2e0d86bebc210947680e8f0d67daa79f3260c106`; no hay submódulos. CLI/docs upstream confirman split-mode layer, tensor-split, flash-attn, ctx/batch/ubatch, Jinja y penalizaciones fijadas. Build aún no iniciado; sin GPU. Recibo `receipts/runtime-source.json`.

2026-10-29T02:57:50Z: build attempt 01 alcanzó ~30%; `nvcc` era 12.8.93, pero `find_package(CUDAToolkit)` encontró 12.0.140 en `/usr/include`. Interrumpido por Q180 con SIGINT (exit 130); no se produjo `llama-server`, no se cargó GGUF ni hubo compute PID. El log se conserva en D como `logs/build.log`. Enmienda A01 fija `CUDAToolkit_ROOT=/usr/local/cuda-12.8`, mueve el build a `llama-build-cu128` y cambia solo el path del binario del runner; nuevo SHA antes de ejecutar. Receipt `receipts/build-attempt01-toolkit-mismatch.json`.

2026-10-29T03:03:45Z: build A01 completado: `llama-server` 0.8.0-dev, commit `2e0d86b`, SHA-256 `0f25065d4c5e304000b38c6e1d288b483aac0a1c8936f3bfdc130b5d44d15ae5`; CUDA toolkit/compilador 12.8.93, SM86. CLI relevante verificado; `ldd` resuelve cudart/cuBLAS/cuBLASLt desde `/usr/local/cuda-12.8/lib64`. Sin proceso de modelo ni inferencia. Receipt `receipts/build-success-a01.json`.

2026-10-29T03:06:10Z: preflight de solo lectura PASS: hashes de modelo, runtime, runner, tokenizador y harness coinciden; lock propio vigente; 2×RTX3090 visibles; compute-apps vacío; sin inference server ni listener 18481; D 145.357.176.832 B libres; MemAvailable 113.570.772 KiB; PSI avg10=0. Se observó memoria de escritorio (969/108 MiB) y utilización gráfica, sin PID CUDA de inferencia. Tool-Eval `--dry-run` resolvió TC-70..97 (28/28), sin requests ni GPU. Receipts `receipts/q180-preflight-before-inference.json` y `receipts/tool-eval-dry-run-seed42.json`.\n

## Incidentes de ejecución y punto de reanudación (2026-10-29T03:47:46+00:00)

Q180 todavía no tiene una medición válida de calidad, velocidad o init para publicar:

- Attempt01 cargó el modelo en ambas RTX 3090 y el smoke pasó. Tool-Eval generó un informe con score 0/completion 50%, pero TC-84..TC-97 terminaron como errores de conexión después de que PeritoSoft inició Qwen3.5-9B; por ello ese score no es comparable ni permite concluir seguridad. El intento quedó archivado en runs/attempt01-peritosoft-interference/.
- Attempt02 pasó preflight, readiness dual y smoke, y se interrumpió al comenzar Q172 cuando la guarda detectó actividad ajena. No hubo métrica válida de Q172 ni ladder de throughput. Los recibos están en runs/attempt02-peritosoft-restart/ y receipts/q180-attempt02-blocked-foreign-scope.json.
- A04 corrigió el falso positivo del detector que clasificaba shells con el texto grep llama-server. Se añadieron seis regresiones CPU-only, todas PASS; no se consumió GPU en esa reparación. Runner SHA-256: c053e71e5c7d50dad45e390bf537b01cf51d5fcd1aa78c443bab73caf0229504.
- El detector actualizado volvió a identificar procesos reales Qwen3.5-9B de PeritoSoft en PID 1874171/puerto 8033 y PID 1874366/puerto 8081. Corren bajo una scope de Claude. No se detuvo esa scope ni se lanzó inferencia Q180 mientras existan.

Reanudar A03 con el mismo protocolo cuando los dos servidores ajenos hayan dejado de relanzarse. El runner ahora distingue procesos reales de shells y abortará ante un llama-server real. Los resultados de Attempt01/02 no deben cargarse en Resultados como score del modelo.\n

### PeritoSoft relanzamiento y cierre previo al intento 03 (2026-10-29T03:49:31+00:00)

La detección A04 encontró dos servidores reales bajo PeritoSoft (PIDs 1876666/8033 y 1876874/8081) dentro de app-com.anthropic.Claude-3228104.scope. Bajo autorización explícita previa se envió SIGTERM sólo a esos dos llama-server y a su padre Electron PeritoSoft PID 1876290; la scope de Claude quedó viva. Verificación posterior: no hay procesos de inferencia ni listeners en 8033, 8081 o 18481. Receipt: receipts/peritosoft-stop-attempt03.json. Attempt03 puede iniciar con preflight fresco; si el supervisor vuelve a lanzar servidores, la guarda debe cortar Q180.


### Attempt03 — Q172 interrumpido por relanzamiento de PeritoSoft (2026-10-29T04:01:29Z)

El preflight dual y el smoke pasaron. Q172 seed42 generó 28 resultados en el JSON, pero el resumen no es válido: TC-70..TC-73 fueron timeouts reales del modelo (116–118 s); después el `llama-server` de Q180 terminó con `rc=0`, y TC-74..TC-97 quedaron como fallos de conexión. No interpretar el 0/100 del harness como score de calidad o seguridad. La corrida no llegó al ladder; no hay throughput ni init cold/hot válidos.

Durante Q172, la scope `app-com.anthropic.Claude-3228104.scope` volvió a iniciar PeritoSoft Qwen3.5-9B en 8033/8081. Se detuvieron con SIGTERM esos dos servidores, `server.js` y el job runner de esa instancia, bajo la autorización explícita del usuario. Los puertos quedaron libres y `nvidia-smi --query-compute-apps` quedó vacío. Se preservaron reporte, JSON, logs, preflight, smoke y postflight en `runs/attempt03-peritosoft-takeover/`; recibos `receipts/q180-attempt03-peritosoft-takeover.json` y `receipts/peritosoft-stop-attempt04.json`.

**Reanudación:** bloquear nuevos arranques GPU mientras la tarea supervisora siga relanzando PeritoSoft. Reanudar Q172 desde seed42 una vez que esa tarea haya terminado o el usuario autorice expresamente detener su scope. No publicar el score ni modificar `Resultados` en Sheets.


### Causa probable del relanzamiento y salida del servidor (2026-10-29T04:03:34Z)

La inspección de proceso encontró Claude Bash PID 1895866 (PPID 1554132) dentro de `app-com.anthropic.Claude-3228104.scope`, con un bucle que ejecuta `ps ... | grep llama-server ... | xargs -r kill` antes de relanzar PeritoSoft `server.js`. Ese `kill` alcanza cualquier `llama-server`, no sólo el suyo, y coincide con la salida `rc=0` del servidor Q180 y el retorno de Qwen3.5-9B en 8033/8081. Es una causa muy probable, pero no se capturó la señal exacta; se conserva como inferencia, no como hecho probado. La scope está activa. No iniciar otra inferencia mientras siga ese bucle. Receipt: `receipts/q180-autorestart-process-identification.json`.


2026-10-29T04:06Z: Q180 accionable reconciliado con Google Sheets. `Accionables!A53:N53` contiene el estado bloqueado, evidencia del Attempt03 inválido y condición de reanudación; lectura de vuelta exacta de 14/14 celdas, Arial 10, WRAP/TOP. No se modificó `Resultados`, porque no existe score/métrica válida. Receipt `receipts/google-sheet-q180-actionable-sync.json`.

### A03 limpio — Q172 seed44 completo (2026-10-29T06:52Z)

JSON `runs/q172-seed44.json`: `status=completed`, 28/28, **0/100** (0/56, 28 fallos); como en las semillas 42 y 43, todos los casos agotaron 16.384 tokens de razonamiento sin herramienta ni respuesta final (~114–115 s/caso). `safety_gate.passed=true` y `safety_warnings=[]`. Las tres semillas coinciden: calidad funcional 0/100 bajo esta configuración, sin gate crítico de seguridad señalado por el harness. Q172 está cerrado. Se conserva la ladder de contexto preregistrada; al momento de este registro el runner está en 131.072 tokens. Cold/hot init siguen pendientes.

### A03 limpio — Q172 seed44 completo (2026-10-29T06:52Z)

JSON `runs/q172-seed44.json`: `status=completed`, 28/28, **0/100** (0/56; 28 fallos), igual que seeds42 y43. Los 28 escenarios llegaron al límite de 16.384 tokens de razonamiento sin herramienta ni respuesta final (~114–115 s/caso). `safety_gate.passed=true`; `safety_warnings=[]`. El fallo es funcional (tool-use/responsividad), no un gate crítico de seguridad señalado por el harness.

### Ladder de contexto y arranque (2026-10-29T06:54Z)

Perfil fijo: GGUF UD-Q4_K_XL, llama.cpp CUDA 12.8, 2×RTX 3090, `--split-mode layer --tensor-split 1,1`, un slot, máximo nativo 262.144, salida 128 tokens, `llama-benchy 0.4.0`; 8K n=3, los demás niveles n=1.

| Contexto pedido | Prefill tok/s | Decode tok/s | TTFT E2E hasta primer token | Repeticiones |
|---|---:|---:|---:|---:|
| 8K (8,192 tokens) | 8700.30 ± 329.21 | 143.22 ± 1.50 | 1.041 s | 3 × 128 tokens |
| 32K (32,768 tokens) | 8170.13 | 129.80 | 4.092 s | 1 × 128 tokens |
| 64K (65,536 tokens) | 7143.66 | 114.76 | 9.301 s | 1 × 128 tokens |
| 128K (131,072 tokens) | 5391.61 | 99.43 | 24.497 s | 1 × 128 tokens |
| 256K (261,888 tokens) | 3614.07 | 74.69 | 72.782 s | 1 × 128 tokens |

Init medido proceso→health inicial: **5,194 s**; relanzamiento inmediato→health: **5,138 s**. No se vació explícitamente la caché de archivos, por lo que las etiquetas describen primera carga de esta sesión y relanzamiento caliente, no arranque tras reinicio del host.

No combinar un score Q172 con tok/s como un índice calidad/velocidad: son instrumentos distintos. Aquí la decisión funcional es clara por separado: 0/100 en tres seeds descarta la promoción de este perfil para agentes, aunque el fixture de throughput mida altas tasas. No afirmar superioridad frente a SOL o ASTRA con esta ladder, porque no constituye una comparación emparejada equivalente.

Postflight 06:54:46Z: summary `completed`, lista de procesos de servidor vacía, puerto 18481 libre, MemAvailable 112.823.568 KiB (~107,6 GiB), sin compute PID de Q180 en las GPU. La lectura mostró util=100% en ambas sin compute PID listado; se conserva como telemetría no atribuida, no como evidencia de un inference server. Temperatura no registrada.

Fuentes: `runs/q180-summary.json`; `runs/q172-seed42.json`, `runs/q172-seed43.json`, `runs/q172-seed44.json`; `runs/context-8192.json` y `runs/context-{32768,65536,131072,261888}.json`; `receipts/q180-launch.json`; `receipts/q180-postflight.json`; `receipts/preregistration.json`.


### Documentación cruzada del cierre — 2026-10-29T07:01Z

La fila correspondiente de `IA local` (G64:L64) quedó actualizada con Q180 y se leyó de vuelta; la evidencia completa de velocidad/calidad está en `Resultados!A413:AH417`, y la recomendación final quedó en `Accionables!A53:N53`. Recibos: `receipts/google-sheet-q180-ialocal-sync.json` y `receipts/google-sheet-q180-results-sync.json`.
