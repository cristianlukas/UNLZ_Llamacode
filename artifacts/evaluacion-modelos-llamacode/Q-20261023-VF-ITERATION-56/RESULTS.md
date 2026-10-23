# Q56 — Resultado final

**Estado final: completada; el gate candidato de formato JSON crudo pasó en el alcance preregistrado.** Los seis requests seriales del intento 5 terminaron con HTTP 200 y `finish_reason=stop`. `response_format=json_schema` pasó 3/3 con estructura JSON cruda y 5/5 valores exactos por fixture (15/15); el brazo plain pasó 2/3 parseos estrictos y 10/15 facts bajo el parser sin normalización.

La auditoría posthoc del tercer plain halló una única cerca exterior Markdown (`\`\`\`json ... \`\`\``). Al quitar sólo esa cerca, el JSON parsea y recupera 5/5 valores; por tanto, la recuperación semántica normalizada fue 15/15 en ambos modos. No se demuestra ventaja de calidad/retrieval. El camino response_format es directiva de prompt más validación, no decodificación restringida. Sólo se recomienda para consumidores de JSON crudo si además validan el esquema; alternativamente, un cliente puede quitar una cerca Markdown exterior bien formada y luego validar. Sin cambio de producción, perfil, ASTRA, SOL, PeritoSoft ni default/contexto. Los tres prompts ya usados son sintéticos y no son holdout; los TPS/timing de n=3 son descriptivos.

Medias plain: prefill 2548,62 tok/s, decode 104,27 tok/s, 268,361 s/request. Medias response_format: 2530,47 tok/s, 102,37 tok/s y 270,338 s/request (+1,977 s; +0,74%). No hay claim de mejora de velocidad. Modelo cargó en 25,573 s. Servicio terminó con código 0, sin kill forzado; no quedaron procesos/listeners, puerto 8352 libre; postflight MemAvailable 124.009.934.848 bytes, swap 0, OOM 0 y PSI memory 0.

**Límite del hallazgo:** el gate candidato pasa exclusivamente para salida estructurada en este fixture/modelo/runtime/contexto. No prueba calidad general ni justifica ampliar/cambiar contexto. Qwen3.8 Flash-Next permanece candidato de evaluación; producción y defaults intactos.

Resumen final: `receipts/final-result.json`; auditoría de normalización: `receipts/posthoc-json-fence-audit.json`; resultado detallado de seis requests: `receipts/700k-json-schema-ab-attempt-04.json`.

## Historia de bloqueo y reanudación


## Recheck después del update

Recheck posterior al update (2026-10-23T14:39Z): `nvidia-smi` sigue en exit 18 (NVML 615.71.09, módulo activo 610.57.04), pero ya no hay paquetes NVIDIA sin configurar. `dpkg-query` confirma `ii` para `nvidia-dkms-615-open`, `nvidia-driver-615-open`, `nvidia-utils-615`, `libnvidia-compute-615` y `linux-modules-nvidia-615-open-7.0.0-38-generic`; `modinfo` selecciona 615.71.09 para el kernel actual. El arranque actual fue 2026-10-22T22:26:57Z y el upgrade que instaló 615 terminó el 2026-10-23T11:33:29Z, por lo que ese arranque precede al update. No hace falta repetir la instalación: hace falta reiniciar ahora para cargar el módulo 615, y luego verificar igualdad de versiones con un preflight fresco. No se inició servidor, request ni trabajo de GPU; el staging verificado y el origen en HDD siguen intactos. Evidencia ampliada en `receipts/post-update-driver-check.json`.


Google Sheets actualizado y leído de vuelta 2026-10-23T14:44:35Z: `Evaluaciones LlamaCode` C286 y G286:J286, `Accionables` D3/H3/K3/N3 e `Inventario de modelos` C11/R11. Se corrigió el destino J286, que por encabezado es `WORK_QUEUE.md · fuente canónica`; el progreso quedó en G286 y la condición en H286. Sólo se modificó `userEnteredValue`; `IA local!K34`, formato, validaciones y otras pestañas no se tocaron. Recibo `receipts/google-sheet-sync-post-update-driver-check.json`.


## Q64 recheck — 2026-10-23T16:51:20Z

Ubuntu seguía arrancado antes del update (`2026-10-22 22:26:57`); módulo activo `610.57.04` vs NVML/modinfo `615.71.09`; `nvidia-smi` exit 18; marcador de reinicio presente. No se encontró inference server y no se iniciaron server/requests/GPU. Q56 continúa bloqueada hasta reiniciar Ubuntu. Detalle: `artifacts/evaluacion-modelos-llamacode/Q-20261023-VF-ITERATION-64/RESULTS.md`.


## Reanudación post-reinicio y enmienda A2 · 2026-10-23T21:25:36.122246+00:00

Ubuntu reinició el 2026-10-23 18:17:11. El módulo en RAM y NVML son 615.71.09, `nvidia-smi` exit 0, sin marcador `reboot-required`; Codex 26.1016.61520 está vivo desde 18:18:12 con ejecutable instalado y sin `(deleted)`. No hay servidores de inferencia ni listeners en 8352/35751. MemAvailable 116.2 GiB, PSI some/full 0, RTX 3090 libres 23,094/24,070 MiB y SSD C: staging conserva 47,971,672,064 bytes.

La auditoría CPU estática halló que el runner A1 abortaría antes de arrancar por hash de config obsoleto, comparación literal de rutas A1 y lock token ya liberado. Se preregistró A2 para corregir sólo estos guardas, fijar el SHA de la config S55 y transferir la identidad de lock. El orden de seis requests y el resto del diseño no cambian. En este punto no se inició servidor ni se emitió request.


## Servicio Q56 intento 1 · 2026-10-23T21:30:24.728332+00:00

El servicio systemd aplicó el cgroup esperado, pero el runner salió en el guard de log relativo antes de arrancar Strata. 0 carga de modelo y 0 requests; el estado no es resultado del modelo. Diagnóstico y estado GPU/listeners: `receipts/service-launch-attempt-01.json`. Registrada A3 para corregir sólo la ruta de log aislada; no se ha repetido ninguna solicitud.


## Intento 2 en carga · 2026-10-23T21:33:32.243007+00:00

`q56-s55-jsonschema.service` está activo en `background.slice` con 86/96/1 GiB, RuntimeMax 4h, OOMPolicy=kill, Restart=no. Runner Q56 en `loading`; servidor PID 35183; 0/6 requests hasta READY. El staging y preflight A3 se verificaron; no hay inference externa. Recibos: `receipts/service-launch-attempt-02.json`, `receipts/google-sheet-sync-attempt02-loading.json`.


## Intento 2 · llegó a READY pero abortó antes del primer prompt · 2026-10-23T21:34:35.399667+00:00

Modelo cargado y READY en 40.936 s; error del runner: `AttributeError: module 'iq3xxs_context262k_runner' has no attribute 'tree_cmdlines'`. Ninguna solicitud `chat/completions` ni resultado de evaluación. El servidor se detuvo limpiamente; MemAvailable final 114.81 GiB, swap 0, OOM 0, puerto libre. A4 preregistrada para corregir la referencia de helper solamente.


## Intento 3 · preservación del resultado previo · 2026-10-23T21:36:57.780302+00:00

La protección de no sobrescribir rechazó el intento antes de iniciar el modelo. Se conservó el receipt fallido del intento 2; 0 cargas/requests de benchmark adicionales. A5 crea paths únicos para el intento 4, sin tocar el diseño.


## CPU tokenizer y A6 · 2026-10-23T21:38:15.658994+00:00

El test con `/usr/bin/python3` falló antes de GPU por `regex` ausente. Con el Python 3.12.3 del venv Strata, el tokenizer cargó, sus cuatro hashes coincidieron con S55 y los conteos fueron 679995, 679998 y 679963 (igualdad exacta). A6 fija ese intérprete para el wrapper; ningún paquete del sistema fue instalado.


## Intento 4 · guard de log previo al servidor · 2026-10-23T21:40:17.781702+00:00

Abortó por discrepancia entre el guard de log antiguo y el path exclusivo A5. Cero carga de modelo, GPU y prompts; no se generó resultado de intento 4. A7 preregistra la corrección.


## Ejecución final · Q68 / intento 5 · 2026-10-23T22:09Z

La matriz preregistrada concluyó 6/6, en tres pares y con prompts offline de 679.963–679.998 tokens. Todos los requests fueron HTTP 200/stop. El receipt fuente indica `candidateGatePass=true`: response_format JSON crudo exacto 3/3, 15/15 facts. Plain estricto 2/3 y 10/15; la salida restante estaba envuelta en una cerca Markdown, no tenía datos erróneos. `posthoc-json-fence-audit.json` quita sólo esa envoltura y confirma JSON válido, claves idénticas y 5/5 valores exactos. Así que, tras normalizar esa presentación, ambas condiciones recuperan 15/15; la diferencia es parseabilidad cruda en esta muestra, no calidad.

Medias calculadas desde timings por request: plain {'prefillTokensPerSecond': 2548.63, 'decodeTokensPerSecond': 104.27, 'elapsedSeconds': 268.361}; response_format {'prefillTokensPerSecond': 2530.47, 'decodeTokensPerSecond': 102.37, 'elapsedSeconds': 270.338}. La diferencia temporal es descriptiva con tres prompts reutilizados. El runtime no fuerza decodificación JSON; el consumidor debe validar. No se cambió el perfil de producción ni el contexto por defecto. El modelo sigue aislado como candidato de evaluación y PeritoSoft no está verificado.

Servicio systemd de prueba: salida limpia 0, sin kill forzado; ninguna inferencia/listener residual y 8352 libre. Postflight: MemAvailable 124009934848 B, swap 0, OOM 0, PSI memory 0. GUI preservada. Recibo original: `receipts/700k-json-schema-ab-attempt-04.json`.
