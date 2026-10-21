# Iteración VF — Harness² / ASTRA

**Estado de la iteración:** bloqueada por el guard de PSI durante la carga local de ASTRA. El canary no llegó a `ready`, no emitió una llamada de herramienta y no puntuó código generado. La suite mecánica del grader sí pasó con una referencia conocida. No se modificaron perfiles ni pesos productivos.

## Trabajo realizado

- Se corrigieron los destinos de montaje del sandbox para mantener runtime/modelos en solo lectura dentro de `/media` y scratch bajo `/tmp`; la copia del perfil productivo quedó oculta.
- El preflight exacto pasó: namespace sólo con loopback y sin ruta por defecto; TEST-NET devolvió `ENETUNREACH`; los dos shards ASTRA, tokenizer, MTP y runtime fueron visibles y de sólo lectura; configuración aislada con contexto/KV 8K; no había servidor externo; límites cgroup admitidos.
- El grader aislado pasó **10/10** casos con una solución de referencia conocida. Esto valida el fixture y el ejecutor, no ASTRA.

## Canary ASTRA

Se intentó una carga con la configuración original de 32K. El proceso fue abortado tras cuatro muestras consecutivas con PSI full avg10 >25%. No hubo readiness, solicitud API, llamada de herramienta ni ejecución del holdout. El scope registró pico de 29,8 GiB y 0 B de swap; después del aborto no quedaron procesos/listeners propios. El resumen del intento 01 se reconstruyó de la salida observada y el journal porque su recibo principal fue sustituido por el reintento antes de copiarlo; el recibo identifica explícitamente esa limitación.

Se preregistró un único reintento con contexto y KV de 8K, suficiente para este ejercicio corto, conservando el mismo modelo, runtime, prompt, sampling, holdout y guard de seguridad. El preflight volvió a pasar, pero la carga alcanzó PSI 25,84%, 41,65%, 48,03% y 52,58% en muestras consecutivas; MemAvailable descendió de 118,3 a 82,9 GB. El guard detuvo el proceso a los 31 s, antes de readiness. El scope registró pico de 37,3 GiB, 0 B de swap y no produjo `probe.json`; el postflight confirmó que procesos y listeners propios se cerraron y GPU volvió al consumo de escritorio. Reducir contexto no eliminó la presión observada.

**Conclusión:** no hay resultado de tool calling ni de calidad Harness². No repetir este camino de carga ni relajar el guard PSI. Reabrir el canary sólo si aparece una estrategia de carga/runtime materialmente distinta que permanezca bajo el umbral registrado. Aunque el canary técnico pasara, la evaluación de calidad Harness² seguiría necesitando un workflow concreto de LlamaCode y un holdout sintético fijo.

## Recibos

- Prerregistro y enmiendas: `receipts/harness2-astra-tool-canary-preregistration.json`, `receipts/harness2-astra-tool-canary-preregistration-amendment-*.json`.
- Preflights y enmiendas de montaje: `receipts/harness2-astra-tool-canary-preflight*.json`.
- Canary 8K: `receipts/harness2-astra-tool-canary-result.json` y copia preservada `receipts/harness2-astra-tool-canary-result-attempt-02.json`.
- Canary 32K, resumen reconstruido con procedencia explícita: `receipts/harness2-astra-tool-canary-result-attempt-01-summary-reconstructed.json`.
- Grader de referencia 10/10: `receipts/harness2-interval-union-grader-selftest.json`.
- Runner y holdout: `work/harness2_astra_tool_canary.py`, `work/test_interval_union.py`.


## Cierre de iteración

Cierre UTC: `2026-10-21T04:24:07Z`. Se verificó que todos los recibos JSON parsean, el hash del runner coincide con el del intento 8K, el grader de referencia conserva el resultado 10/10 y el canary sigue sin producir readiness, solicitud ni score. El lock se libera sólo después de guardar este cierre y verificar su token. La cola general sigue incompleta: los demás pendientes conservan sus condiciones externas documentadas en `WORK_QUEUE.md`.
