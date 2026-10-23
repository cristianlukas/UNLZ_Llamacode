# Q56 — JSON Schema con retrieval a ~680K cargado desde SSD

- **Estado final:** completada bajo Q68. Gate candidato de JSON crudo aprobado 3/3 en este fixture; recuperación semántica posthoc 15/15 en ambos modos tras quitar sólo una cerca Markdown del control. Sin cambio de producción/contexto.
- **Task:** `Q-20261023-VF-ITERATION-56`.
- **Experiment ID:** `VF-20261019-01-S55-IQ3XXS-YARN700K-JSON-SCHEMA-AB-SSD-C-STAGED`.
- **Token original de Q56:** `3f628b9f-27c2-4675-a960-1350fc7f44d6` (expiró al liberarse el turno anterior). **Ejecución final Q68:** `0bbd4847-1a31-436c-a45e-785a230d9c8f`.
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


## Enmienda A2 · reanudación y guardas del runner

- Registrada 2026-10-23T21:25:36.122246+00:00. El reboot posterior al update cargó NVIDIA 615.71.09; NVML/módulo coinciden y `nvidia-smi` responde. Codex es 26.1016.61520 ejecutándose desde `/usr/lib/chatgpt/ChatGPT`; el listener ajeno observado antes (35751) ya no existe.
- Auditoría CPU-only encontró tres defectos de preflight: token embebido de Q56 ya liberado; `EXPECTED_CONFIG_SHA` 04ca… no coincide con el archivo A1 (SHA actual exacto en `receipts/preregistration.json`); y comparación literal de args/tokenizer que rechazaría las rutas A1 trasladadas al SSD C:.
- El runner ahora permite diferencias sólo en `--pack`, `--native`, `--ple-gguf` bajo el staging registrado y `tokenizer == pack/tokenizer`; todos los otros argumentos y claves de config se comparan con S55. También fija el hash del config fuente S55. Se actualizan token/hash del runner en el preregistro.
- **No cambia** experimento/factor/fixtures/seeds/orden/seis requests/umbrales/criterio. No hubo servidor, requests ni workload GPU durante esta enmienda. Se exige prueba CPU del validador y readback del Sheet antes del canario y preflight fresco.


## Confirmación A2 en Google Sheets · 2026-10-23T21:27:33.085233+00:00

El readback vivo de `Evaluaciones LlamaCode!C286:J286`, `Accionables!D3:N3` e `Inventario de modelos!C11:R11` contiene la enmienda A2, el estado post-reinicio, el guard A2 y el siguiente paso. No hizo falta modificar celdas en esta comprobación. Recibo: `receipts/google-sheet-sync-amendment-A2.json`. Se marca la preregistración como leída de vuelta antes del canario.


## Canario systemd aprobado · 2026-10-23T21:28:14.196192+00:00

El canario `q56-cgroup-canary-20261023.service` pasó: transient user service dentro de `background.slice`, cgroup v2 efectivo con `memory.high=92341796864`, `memory.max=103079215104`, `memory.swap.max=1073741824`, `OOMPolicy=kill`, `Restart=no`; contadores OOM en cero. Se detuvo y el manager lo recolectó (`LoadState=not-found`, inactivo). No cargó modelo ni usó GPU/red. Recibo: `receipts/q56-service-canary.json`.


## Preflight y Sheet antes del servicio · 2026-10-23T21:29:20.134580+00:00

El preflight vigente pasó 17/17. El estado se actualizó y leyó de vuelta en las tres filas relevantes del Sheet; recibo `receipts/google-sheet-sync-preflight-A2.json`. El recibo de lanzamiento `receipts/service-launch.json` congela comando, runner y propiedades systemd. No se han iniciado modelo ni solicitudes.


## Enmienda A3 · guard de ruta de log antes de cargar modelo · 2026-10-23T21:30:24.728332+00:00

El primer servicio Q56 falló en la validación local previa a `Popen`: `model_name` coincidía, pero el `log` configurado era relativo y el runner exige la ruta aislada absoluta en `receipts/strata-format-ab.log`. No se inició Strata ni se cargó modelo, no se usó GPU por Q56 ni se envió ninguna solicitud. El recibo `receipts/service-launch-attempt-01.json` conserva el intento. A3 cambia únicamente ese log a `/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode/artifacts/evaluacion-modelos-llamacode/Q-20261023-VF-ITERATION-56/receipts/strata-format-ab.log` y actualiza los hashes de config/runner; todo el diseño del experimento permanece congelado. Deben pasar py_compile, validaciones CPU, preflight fresco y readback del Sheet antes del nuevo servicio. Registro A3: `receipts/amendment-A3.json`.


## A3 validada y sincronizada · 2026-10-23T21:31:47.610843+00:00

`py_compile` y las siete validaciones CPU pasan; el preflight A3 volvió a pasar 17/17 inmediatamente antes de continuar. El readback de A3 de Evaluaciones, Accionables e Inventario está en `receipts/google-sheet-sync-amendment-A3.json`; la preregistración ya no está pendiente. El intento 1 fue un fallo de guard sin cargar modelo ni request. El intento 2 reutiliza el mismo servicio transitorio y límites verificados.


## Ajuste operativo del intento 2 · 2026-10-23T21:32:19.571660+00:00

Tras `reset-failed`, systemd recolectó el unit viejo; `systemctl start` devolvió `Unit not found` y no ejecutó el proceso. A3 no cambia. Se recreará el mismo unit transitorio con `systemd-run` y las mismas propiedades verificadas. Sin modelo, GPU por Q56 ni solicitudes. Recibo: `receipts/service-launch-attempt-02-adjustment.json`.


## Enmienda A4 · helper `tree_cmdlines` · 2026-10-23T21:34:35.399667+00:00

El intento 2 cargó el modelo y alcanzó READY en 40.936 s; antes del primer prompt de benchmark, el runner llamó `tree_cmdlines` sobre el módulo helper equivocado. La función existe en el wrapper S55 importado, no en su módulo base. Strata se detuvo limpiamente, OOM=0, sin prompts de evaluación. A4 retiene el wrapper S55 y llama su función existente; cambia solo la observabilidad del árbol del proceso. Recibos: `receipts/service-launch-attempt-02-result.json` y `receipts/amendment-A4.json`.


## A4 Sheet readback y preparación del intento 3 · 2026-10-23T21:35:46.864889+00:00

Readback verificado en Evaluaciones, Accionables e Inventario; recibo `receipts/google-sheet-sync-amendment-A4.json`. El intento 2 llegó a READY pero se detuvo antes de un prompt. El intento 3 solo recupera la matriz de seis prompts aún no ejecutada, con diseño sin cambios y el helper A4; preregistro `receipts/service-launch-attempt-03-preregistration.json`. Se exige preflight fresco antes de la carga.


## Enmienda A5 · conservar recibos y logs de cada intento · 2026-10-23T21:36:57.780302+00:00

El intento 3 fue rechazado por la protección de no sobrescribir: el resultado de error del intento 2 se conserva en `receipts/700k-json-schema-ab-result.json`. No se inició servidor ni se usó GPU. A5 fija rutas únicas para el intento 4: `receipts/700k-json-schema-ab-attempt-04.json`, `receipts/strata-format-ab-wrapper-attempt-04.log` y `/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode/artifacts/evaluacion-modelos-llamacode/Q-20261023-VF-ITERATION-56/receipts/strata-format-ab-attempt-04.log`. Solo cambia trazabilidad/rutas de log, y hashes de config/runner; modelo, contexto, prompts, seeds, orden y factor siguen congelados. Antes de la carga se validará tokenizer en CPU, helper, preflight y readback.


## Enmienda A6 · wrapper en el Python del entorno Strata · 2026-10-23T21:38:15.658994+00:00

A5 detectó en CPU que `/usr/bin/python3` no tiene `regex`, dependencia de `strata_tokenizer.py`. El venv fijado de Strata es Python 3.12.3 con `regex` 2026.9.10; cargó el tokenizer, igualó los cuatro hashes de S55 y reprodujo los tres conteos de tokens. A6 cambia solo el intérprete del wrapper del unit al Python de ese venv; el servidor ya usaba ese mismo Python. No se instala nada ni cambia el host. Antes de carga: readback Sheet A6 y preflight fresco. Recibos: `amendment-A6.json`, `a5-cpu-validation-system-python.json`, `a6-cpu-validation-venv.json`.


## A6 Sheet readback · 2026-10-23T21:39:13.775596+00:00

Se leyó de vuelta el estado A6 en las tres filas del Sheet, incluyendo el intento 3 sin carga y el wrapper en venv. Recibo `receipts/google-sheet-sync-amendment-A6.json`. La preregistración está sincronizada antes del cuarto inicio.


## Enmienda A7 · guard de log por intento · 2026-10-23T21:40:17.781702+00:00

El intento 4 fue abortado antes de `Popen`: el guard de config todavía esperaba el nombre de log original, mientras A5 ya había preregistrado `strata-format-ab-attempt-04.log`. No se cargó modelo ni se usó GPU; 0 prompts. A7 alinea únicamente ese literal del guard y actualiza el hash del runner. El intento 5 se preregistra con rutas A5 e intérprete A6. Recibos: `service-launch-attempt-04-result.json`, `amendment-A7.json`, `service-launch-attempt-05-preregistration.json`.


## A7 validada y sincronizada · 2026-10-23T21:41:29.939590+00:00

Prestart audit CPU 15/15; preflight actual 17/17; readback A7 verificado en las tres filas del Sheet. Recibos `a7-prestart-cpu-audit.json`, `preflight.json` y `google-sheet-sync-amendment-A7.json`. Sin modelo/GPU desde el fallo pre-Popen del intento 4.


## Cierre final

Las seis solicitudes se completaron en orden serial. El gate es sólo de formato/consumibilidad JSON en tres fixtures sintéticos ya usados (~680K). No es holdout ni prueba de superioridad de calidad o throughput. La respuesta del control que falló al parser estricto se recupera íntegra al remover una única cerca exterior; el cliente recomendado debe validar esquema después de parsing. No modificar defaults ni producción. Resultado: `receipts/final-result.json`; auditoría posthoc: `receipts/posthoc-json-fence-audit.json`.
