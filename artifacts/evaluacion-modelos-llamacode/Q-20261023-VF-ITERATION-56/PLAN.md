# Q56 — JSON Schema con retrieval a ~680K cargado desde SSD

- **Estado:** bloqueada antes de inferencia; staging A1 completado y 11/11 SHA-256 verificados; el preflight fresco no pudo consultar las GPU por mismatch NVML/kernel de NVIDIA en Linux.
- **Task:** `Q-20261023-VF-ITERATION-56`.
- **Experiment ID:** `VF-20261019-01-S55-IQ3XXS-YARN700K-JSON-SCHEMA-AB-SSD-C-STAGED`.
- **Lock token:** `3f628b9f-27c2-4675-a960-1350fc7f44d6`.
- **Objetivo:** decidir si `response_format=json_schema` permite combinar la recuperación exacta ya observada a ~680K con salida JSON cruda para ISTA Qwen3.8-Flash-Next IQ3_XXS / Strata v0.1.41.

## Motivo de reapertura

S55 recuperó los 15/15 hechos con tres prompts de ~680K, pero una respuesta envolvió el JSON en Markdown: gate estricto 2/3. El primer Q18 preparó un A/B de formato, pero el loader desde HDD extra superó el guard de PSI antes de READY y produjo 0/6 requests. Al reanudar, se encontró que los shards y el pack ya no están en su ruta D: original; sí existen en cuarentena HDD y su carga directa repite el método de Q18. Q56 continúa con una copia temporal verificada en el SSD C:, sin tocar la cuarentena; el MTP permanece en su SSD D: original. No cambia runtime, quant, pesos, contexto ni fixtures. Los prompts ya se usaron, por lo que esto **no es holdout independiente**.

## Enmienda A1 · staging temporal en SSD C:

La ruta SSD D: que S55 usó ya no contiene los dos GGUF ni el pack IQ3_XXS. La cuarentena HDD conserva ambos shards y el pack; Q18 documentó que leerlos directamente desde HDD elevó PSI a 43,11% y abortó antes de READY. La ruta C: actual tiene 125.366.710.272 bytes libres. El staging esperado ocupa 77.387.976.778 bytes (75.839.998.528 de shards y 1.547.978.250 del pack), dejando 47.978.733.494 bytes, por encima del mínimo de 40 GiB.

Antes de copiar: la fila de evaluación, el accionable y el inventario deben contener esta enmienda y quedar leídos de vuelta desde Sheets; confirmar el espacio proyectado. Copiar sólo a `C:\Users\cristian\Models\LlamaCode-Q56-IQ3XXS-Temp\` (`/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Models/LlamaCode-Q56-IQ3XXS-Temp/`), conservando el árbol de cuarentena intacto. A1 ejecutada: SHA-256 de ambos orígenes coincide con S55; se copiaron los 2 shards y los 9 archivos del pack preservando timestamps. El recibo `receipts/staged-assets.json` confirma 11/11 SHA-256 origen/destino, origen intacto y 47.978.659.840 bytes libres tras la copia. Si el espacio libre proyectado o real baja de 40 GiB, detener y borrar únicamente el staging de Q56. No descargar, mover ni borrar el modelo de cuarentena. El MTP sigue en `/media/cristian/Disco local/Models/FlashNext-IQ3XXS-ISTA-Strata-eval-20261009/strata-data/mtp/rt`; la ruta Windows del MTP no se da por verificada. El A/B sólo interpreta el formato; no compara tiempos de carga ni rendimiento entre discos.

Esta enmienda resuelve la causa observable de Q18 mediante carga desde NVMe, no repite el loader HDD ni relaja guards de PSI/RAM/OOM. Configuración efectiva, flags no relacionados con ubicación, runtime, tokenizer, hashes de los pesos, fixtures y secuencia de requests quedan congelados.

## Hipótesis y criterio congelados

H1: en los tres fixtures ya usados, el brazo `json_schema` devuelve todos los valores exactos y JSON crudo parseable en 3/3 requests, sin errores de servicio/contexto/OOM/guard. Control plain-text y schema se comparan por pares con el mismo prompt y seed. Este resultado sólo permitiría recomendar salida estructurada para ese flujo sintético de este perfil; no prueba coding, calidad general, ni habilita cambiar perfiles/defaults.

- **Pasa candidato:** 3/3 requests schema con HTTP 200, `finish_reason=stop`, prompt API entre 679.000–699.000 tokens, JSON crudo (sin fences), exactamente las cinco claves requeridas, todos strings, sin claves extra y 5/5 valores exactos por fixture; 15/15 hechos.
- **Diseño:** seis requests seriales en un servidor, tres pares: prompt01 control→schema, prompt02 schema→control, prompt03 control→schema. Temperatura 0, top-p 1, top-k 20, seeds S55 `2026101956/57/58`, max_tokens 768, thinking desactivado, cache_prompt=false. Sólo cambia `response_format`.
- Si hay fallo de infraestructura, timeout, contexto, memoria/PSI u OOM, parar y guardar bloqueo. Si infraestructura se mantiene sana y falla el formato/semántica, completar las seis solicitudes y cerrar sin retry.

## Método, identidades y límites

- Un único Strata v0.1.41, modelo/config de S55, 700.000 tokens, YaRN ×4 desde 262.144, KV int8, RTX 3090 0+1 en serie, endpoint sólo `127.0.0.1:8352`.
- En A1, shards/pack/tokenizer se leen desde el staging temporal C: verificado; MTP, runtime, perfiles y demás rutas siguen idénticos a S55. El config conserva el mismo alias/modelo y flags, con sólo paths de shards, pack y tokenizer redirigidos al staging y la ruta de log aislada. Preflight verifica hashes del recibo de staging, size/mtime, disponibilidad de espacio y coincidencia de todos los flags no relacionados con esos paths.
- Respuesta estructurada del runtime es directiva + validación de JSON, no decodificación restringida. Scorer local revisa shape/valores exactos.
- Proceso de prueba ejecutado como unidad transitoria durable de `systemd --user` en `background.slice`, `MemoryHigh=86G`, `MemoryMax=96G`, `MemorySwapMax=1G`, `OOMPolicy=kill`, `Restart=no`, `RuntimeMaxSec=4h`. Esto aísla el árbol del supervisor de Codex; los límites contienen memoria, no reducen el presupuesto del modelo. No cerrar GUI ni detener procesos ajenos.
- Guard fresco inmediato antes de iniciar: lock token propio, cero servidores/listeners de inferencia externos, puerto 8352 libre, MemAvailable ≥40 GiB, PSI some.avg10 <10% y full.avg10 <1%, contador OOM disponible, ≥12 GiB libres en cada RTX 3090. Watchdog ya fijado: abortar si MemAvailable <32 GiB por 15 s, OOM aumenta, PSI some≥40% o full≥25% durante 4 muestras, aparece servidor/listener externo o el lock cambia. Si cgroup/servicio durable no inicia con los límites verificados, no ejecutar en foreground como sustituto.
- No tocar producción, ASTRA, SOL, Flash-Next productivo, PeritoSoft ni perfiles; la interfaz gráfica puede seguir abierta. No elevar contexto global. No repetir solicitudes después del resultado.

## Archivos y trazabilidad

- Preregistro: `PLAN.md`.
- Config: `receipts/source55-format-ab-strata-config.json`.
- Esquemas: `schemas/response-schemas.json`.
- Runner aislado: `work/run_700k_json_schema_ab.py`.
- Resultado: `receipts/700k-json-schema-ab-result.json`.
- Preflight y servicio: `receipts/preflight.json`, `receipts/service-launch.json`.
- Sheet: registrar/readback del preregistro antes de GPU; registrar/readback del cierre después.
- El S55 control previo sigue en `Q-20261020-VF-20261019-01/receipts/source-55-retrieval700k.json`; la auditoría posthoc de sus respuestas no se modifica.


## Resultado de staging y bloqueo de preflight

- Staging completado el 2026-10-23T14:31:10.090139+00:00: 11/11 archivos verificados por SHA-256; origen HDD preservado; C: conserva 47,978,659,840 bytes libres, por encima de 40 GiB.
- El resultado de staging y la actualización del bloqueo quedaron escritos y leídos de vuelta en `Evaluaciones LlamaCode`, `Accionables` e `Inventario de modelos`; recibo `receipts/google-sheet-sync-staging-preflight-block.json`.
- El preflight se detuvo antes de iniciar servidor o requests. `nvidia-smi` devolvió exit 18: NVML user-space 615.71.09 no coincide con el módulo cargado 610.57.04; `nvidia-dkms-615-open` está a medio configurar y otros paquetes 615/610 aparecen sin configurar. El módulo que `modinfo` selecciona en disco es 615.71.09, mientras `/proc/driver/nvidia/version` sigue informando 610.57.04.
- No se detectó proceso de inferencia ni listener en el puerto 8352; no hubo uso de GPU por el benchmark, servidor, ni requests (0). La GUI sigue intacta. El intento y el diagnóstico están en `receipts/preflight-attempt-01-nvml-mismatch.json`.
- **Reanudación:** completar la reparación de paquetes NVIDIA en Linux y reiniciar para que la biblioteca NVML y el módulo activo queden en la misma versión; después correr el preflight fresco completo. No iniciar servidor ni requests GPU antes de que todos los gates pasen. El staging temporal se conserva para reanudar y la cuarentena no se modifica.

- Usuario confirmó que hubo una actualización del sistema; se repitió `nvidia-smi` a 2026-10-23T14:35:50Z y el mismatch 615.71/610.57 persistió. El bloqueo requiere terminar la configuración Linux y reiniciar para alinear el módulo activo, no un cambio en Windows.
