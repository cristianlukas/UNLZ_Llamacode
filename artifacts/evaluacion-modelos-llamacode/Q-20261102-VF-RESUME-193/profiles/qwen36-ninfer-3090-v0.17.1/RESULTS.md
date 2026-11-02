# Q193 — resultados y punto de pausa

## Estado al 2026-11-02T02:37:39Z

**Pausado por instrucción del usuario antes de la inferencia.** No se inició `ninfer-serve`, no se envió el request smoke y no se ejecutaron Q173 ni Q172. Por lo tanto Q193 todavía no tiene mediciones de prefill/decode, calidad, cold init ni hot init; no agregar una fila de resultados para este runtime a `Resultados` o `Modelos locales por peso`.

El único uso de GPU en esta iteración fue la consulta de estado/preflight con `nvidia-smi`; no hubo CUDA compute apps. GPU0 es RTX 3090 PCI `01:00.0` con 957 MiB usados (escritorio visible); GPU1 es RTX 3090 PCI `03:00.0` con 108 MiB. `nvidia-smi --query-compute-apps` no mostró procesos de cómputo. No había procesos NInfer/llama-server/Ollama/vLLM ni listener en puerto 18503.

## Trabajo realizado

- Se verificó el release Linux NInfer-3090 v0.17.1, su digest oficial y los límites publicados para el pipeline de dispositivos distintos. El README advierte que el pipeline del motor de contexto actual con dos dispositivos distintos aún no está verificado; el smoke de 8K sigue siendo una compuerta obligatoria.
- Se descargó sólo el runtime, no los pesos: archive HDD extra de 1,048,862,833 B, SHA-256 `2f469d9171fa9a1e6fca1de85f6a5d5cfb7326302f69a0561dcd9ef81415febb`. La extracción inicial parcial de HDD se conserva renombrada como `incomplete-extraction-aborted-Q193`; no fue borrada. La extracción completa de 2,356,558,649 B está en D junto al modelo.
- `ninfer-serve --version`, `ninfer-serve --help`, `run.sh --help`, `bash -n run.sh` y `ldd` pasaron; no faltan bibliotecas. El binario CLI incluye `--devices N,M,...`, pero el wrapper `run.sh` no habilita dispositivos múltiples para Qwen3.6 y reserva `NINFER_DEVICES` al perfil Flash-Next. Por eso se agregó antes de GPU la enmienda 02 con lanzamiento directo y argumentos explícitos.
- Se volvió a confirmar el modelo ya presente, sin copiar ni descargar pesos: `/media/cristian/Disco local/Modelos-eval/Qwen3.6-35B-A3B-NInfer-all-20261101/qwen3_6_35b_a3b.ninfer`, 22,790,484,480 B, SHA-256 `3e33297645dc33557751be1a3c407a74ed7c00f34909b5d4e8cfdce91b3dbe84`, coincide con Q190.
- Se actualizaron `data/actionables.json` y `Accionables!A60:N60`; el readback confirma estado de pausa, preregistro del CLI directo y formato existente. La fila de Q190 en `Accionables` permanece aparte.
- La limpieza DeepSeek FP8 Engram del pedido anterior ya estaba completada en Q190/Q192: 203,080,585,216 B de shards retirados en Q190 y manifiesto residual de 294 B/directorio vacío en Q192. La ruta ya no existe. ASTRA DSX T16, Maya Q189 y sus registros permanecen preservados. Recibos: `Q-20261029-VF-ITERATION-190/receipts/remove-fp8-engram-stage-20261101.json` y `Q-20261102-VF-RESUME-192/receipts/deepseek-fp8-engram-orphan-manifest-cleanup-20261102.json`.

## Preflight vigente cuando se pausó

Leído a las `2026-11-02T02:36:49Z` (sin lanzamiento posterior): lock Q193 era propio; ambas 3090 visibles; sin procesos de servidor ni CUDA compute; puerto 18503 libre; P2P GPU0↔GPU1 `OK`; `gpu_unlock` cargado con PCI targets `01:00.0,03:00.0`; servicio ASUS de cuarentena activo y 1636/1636 frames retenidos, 0 pendientes; servicio oneshot `3090-helper-verify-boot` finalizó con `Result=success`, `ExecMainStatus=0`, y el journal del boot informa PASS de las tres protecciones. `MemAvailable=98,687,992 kB`. Espacio libre: D `85,057,601,536 B`, HDD extra `262,798,548,992 B`, `/` `2,277,285,888 B`. El gate de `/` apenas supera el mínimo preregistrado de 2,000,000,000 B; al reanudar hay que repetirlo y no continuar si cae por debajo. Sin Xid/OOM/CUDA fault registrado desde el inicio de Q193.

El servicio `3090-helper-verify-boot` aparece `inactive` porque es oneshot ya completado; no es un fallo. El servicio continuo `vram-quarantine@GPU-af6de4b3-6497-b7f8-796d-6d69cba422e6` sí está `active (running)`.

## Reanudación

Q193 queda pendiente, no cancelado. Al reanudar:

1. Leer AGENTS.md, README.md, WORK_QUEUE.md y WORK_QUEUE.lock; reclamar un lock exclusivo para Q193 antes de seguir.
2. Revalidar todos los gates en vivo, especialmente workers/protecciones ASUS, uso de procesos, almacenamiento raíz y puerto.
3. Ejecutar únicamente el smoke preregistrado de 8K con CLI directa `--devices 0,1`; detener si no devuelve salida válida o los logs no prueban etapas/uso en las dos GPU. No probar en una GPU como alternativa.
4. Si el smoke pasa, continuar serialmente Q173 8K×3, 32K, 64K, 128K y 261888 (sin 523K), luego Q172 seeds 42/43/44, actualizando el Sheet después de cada hito/semilla.
5. Mantener Q190 NInfer-all separado. No borrar ni reemplazar los pesos por este test.

Receipts de esta pausa: `receipts/live-preflight-before-pause-20261102.json`, `receipts/pause-point-20261102.json` y `receipts/sheet-sync-pause-point.json`.
