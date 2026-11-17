# Reconciliación de pestañas de IA — checkpoint Q202.97

## Alcance cubierto en esta pasada

Se inspeccionó el metadata actual del libro `Listado` y se cruzó una primera pasada de `IA local`, `Evaluaciones LlamaCode`, `Accionables`, `Resultados`, `Inventario de modelos`, `Modelos locales por peso`, `Sin evaluar`, `Enlaces revisados`, `Recursos` y `Perfiles de LlamaCode`. `Vista agrupada por tipo` se trata como vista derivada, no como cola independiente. Las pestañas de juegos/VR/electrónica se excluyen salvo que una fila tenga una evaluación concreta de IA.

Esta conciliación es incremental, no una declaración de que el libro entero está cerrado. Las listas largas de enlaces y propuestas aún requieren terminar el emparejamiento fila por fila con fingerprints, recibos y resultados. La cola de pruebas se toma de `Accionables` y se valida contra las demás pestañas, en vez de contar cada referencia o perfil como una prueba nueva.

## Checkpoint Q202.97 — Q204.07 sincronizado; conciliación amplia activa (2026-11-03T15:15:14Z)

Se volvió a consultar el metadata del libro `Listado`: 21 pestañas. Se confirmaron las pestañas de IA que se concilian y `Vista agrupada por tipo` como vista derivada; pestañas de juegos/VR/electrónica quedan excluidas salvo una fila con evaluación de IA concreta. Q204.07 quedó sincronizado/readback PASS en `Resultados!A471:AH471`, `Accionables!A73:N73`, `IA local!A122:O122`, `Enlaces revisados!A734:R734`, `Sin evaluar!A734:S734`, `Inventario de modelos!A74:R74` y `Modelos locales por peso!A110:Z110`. El artefacto sigue sin inferencia/Q173/Q172; tamaño 16.810.715.744 bytes y SHA-256 `a6b6a6dfe52531a1dc6b224b788d5b4599e601ee82873fdb16893b4abba98c89`. La fórmula numérica `G110` y las métricas N/D se conservaron. Recibo `profiles/kvark-sparkle-1.0/receipts/sheet-sync-q20407-download-inventory-readback-20261103T151514Z.json`, SHA-256 `51689e814cc080010e87a39b2874a5f6a1f7190f53f5edeaf5f99fd2b34a7121`.

La reconciliación completa por fila y fingerprint sigue abierta. Las entradas nuevas `Accionables!74:77` y `IA local!123:127` deben cruzarse con fuentes, inventario, `Sin evaluar`, `Enlaces revisados`, `Resultados` y recibos antes de decidir su prueba. No contar `Sin probar`, `N/D`, una fila de inventario o una propuesta técnica como prueba ejecutable sin validar artefacto, uso y dependencias. Las evaluaciones cubren modelos y las funciones AI concretas de OCR, RAG, voz, tools, agentes, seguridad e integración; los elementos de juegos/PCVR sin afirmación de IA no entran en este objetivo.

## Decisiones verificadas

- `Accionables!61:75` contiene trabajo de IA de voz, agentes, motores, OCR, herramientas, CUA, seguridad, memoria/contexto y evaluación de modelos. `Accionables!76:77` son tareas no relacionadas con benchmarks de IA y quedan fuera de esta campaña.
- Q193 Q173/Q172 terminó en Q202.74 y sus resultados se identifican por `Q193-NINFER3090-Q173-LADDER` y `Q193-NINFER3090-Q172-SEED42/43/44` en `Resultados`, además de `Accionables!60` e inventario. La cohorte Q172 66/77/73 promedia 72/100 y las tres semillas fallan gates de seguridad. No repetir Q193 ni transferir sus resultados a otra huella o perfil.
- `Accionables!72` y `IA local!121` describen el candidato Megakernel; no había prueba local asociada a esa versión. El release primario más reciente inspeccionado es v2026.11.01. El test quedó preregistrado en el perfil Q202.75; sincronizarlo con Sheets es el siguiente gate.
- SmartTurn, proactividad, CUA y Router/Worker requieren implementación; el ancla de compactación indica no correr hasta tener nueva suite. Indra OCR requiere corpus/licencia resueltos; LFM3 Omni requiere confirmar compatibilidad; Speedy/SparseKV, KVARK, ISTA Coder y QEngine mantienen gates separados. No se fusionaron con Megakernel.
- `Modelos locales por peso`, `Inventario de modelos` y `Perfiles de LlamaCode` contienen artefactos o configuraciones, no necesariamente pruebas pendientes. Un `N/D`, un perfil activo o una fila de modelo no justifica por sí solo ejecutar Q172; hay que confirmar artefacto, consumidor y modalidad.

## Siguiente reconciliación

Después de registrar el preregistro Megakernel en Sheets y completar sus fases, seguir el backlog AI de `Accionables` y enlazar cada elemento con las filas fuente de `IA local`, `Recursos`, `Sin evaluar` y `Enlaces revisados`, además de buscar ID/fingerprint exacto en `Resultados` y recibos locales. Mantener estados separados: ejecutable, requiere implementación/fixture/licencia, bloqueado externamente, duplicado o sin prueba aplicable.

## Checkpoint Q202.82 — Megakernel gate sync (2026-11-03T02:50:36Z)

The pinned Megakernel package and its 12 executable/library/script/data dependency hashes are recorded in the local preregistration. The amendment is present and read back in `Accionables!J72` and `IA local!G121`; test remains unstarted. Next is a fresh GPU/server/helper/fault preflight followed by only the packaged exactness legs if safe. The broader workbook reconciliation remains incomplete; no claim of all-tabs completion.

## Checkpoint Q202.84 — resultado Megakernel exactness (2026-11-03T02:56:11Z)

La prueba local de exactitud del paquete v2026.11.01 concluyó 10/10 assertions PASS, exit0, con recibo y JSON hash `bc4efc3750a91f5c0b2b7a1cad6a142ab67ac8d4382aaea58949d2915732cb5b`. Se sincronizará ahora en `Resultados`, `Accionables` e `IA local`. Esto no cierra la evaluación Megakernel: quedan Q173 throughput ladder y Q172 calidad/seguridad; la reconciliación de todas las filas AI del libro sigue abierta.

## Checkpoint Q202.85 — sincronización exactness (2026-11-03T02:57:48Z)

Q202.84 se leyó de vuelta en `Resultados!444`, `Accionables!72`, `IA local!121`, `Modelos locales por peso!32` (nota separada en X; métricas del perfil llama.cpp intactas) e `Inventario de modelos!41` (nota separada en R). No se completaron otras filas de IA; la reconciliación transversal sigue abierta. Próximo candidato de esta evaluación: Q173 Megakernel ladder; aún necesita preregistro detallado y preflight nuevo.


## Checkpoint Q202.86 — Q173 Megakernel preregistrado

La fila Megakernel de `Accionables!72` / `IA local!121` ahora separa Q202.84 (exactness funcional) de Q173 (rendimiento aún no medido). El preregistro Q202.86 fija exact artifact, runtime commands, tokenizer/harness/corpus, contexto hasta 261888, single-PNY GPU1, muestras, validity rules y límites de init/cache; Sheets readback PASS. No se escribió aún un resultado en `Resultados`, porque no hubo solicitud de inferencia. El snapshot read-only previo vio Xorg en la PNY sin proceso compute, por lo que se conservará el GUI y se atribuirá/medirá su carga antes de inferir. Próximo gate: preflight vivo posterior al readback; si pasa, ejecutar solo el primer punto Q173 y sincronizarlo antes de la siguiente prueba.

El inventario inter-pestaña continúa incompleto: siguen pendientes la conciliación fila-por-fila de `IA local`, `Evaluaciones LlamaCode`, `Accionables`, `Resultados`, `Inventario de modelos`, `Modelos locales por peso`, `Sin evaluar`, `Enlaces revisados`, `Recursos` y `Perfiles de LlamaCode`, incluyendo OCR/RAG/voz/herramientas/agentes/seguridad/integración. No se afirma cierre del libro.

## Checkpoint posterior Q202.96 — 2026-11-03T05:05:02Z

Q202.96 A-repeat Q173 8K ya está cerrado y su sincronización fue verificada por lectura de vuelta. El perfil de control single-PNY se mantiene en una fila distinta del Q190 dual-GPU; Q172 para esta variante de runtime sigue N/D. Detalle y recibo en `profiles/qwen38-megakernel-v2026.11.01/RESULTS.md` y `receipts/sheet-sync-q20296-result-final-readback-20261103T050502Z.json`.

La conciliación global sigue abierta. En `Accionables!61:77`, el estado observado mantiene candidatos de IA de voz/Smart Turn, proactividad/agentes, QEngine condicionado por licencia/hardware, TTS ToneColor, Ghidra MCP, CUA desktop, Router/Worker, compaction, Speedy/SparseKV, OCR Indra, LFM3 Omni, KVARK/Sparkle, ISTA Coder y rigor Q172. Cada uno requiere cotejo con las pestañas fuente, el ID/fingerprint y los recibos; no son todos benchmarks listos para ejecutar. No IA: excluir las filas de port VR/PCVR y cualquier propuesta sin evaluación de IA concreta.

Próximo trabajo del perfil en curso: preregistrar B confirmatorio de 8K con regla de atribución/interferencia por proceso y sincronizar antes de usar GPU. La bandera histórica A/B/A no se elimina. Luego continuar la evaluación del ladder y, en paralelo, conciliar candidatos de las demás pestañas; no declarar que el libro está completo por cerrar este perfil.

### Q203.00 — control de trazabilidad y siguiente candidato

El recibo JSON de preregistro Q202.95 B no parsea por las comillas sin escapar en `server_argv`; su resultado sigue preservado, pero se registra el defecto de trazabilidad. Q203.00 tiene un preregistro nuevo, legible y separado, y añadirá atribución NVML/pmon para no confundir compute del test con actividad gráfica Xorg. Está pendiente de sincronización y lectura de vuelta. No se utilizó GPU al crear el preregistro ni el supervisor.

La cola transversal de AI sigue pendiente más allá de Megakernel: candidates de voz/Smart Turn y TTS, agentes/proactividad/Router/Worker, CUA, Ghidra MCP, OCR Indra, LFM3 Omni, KVARK/Sparkle, ISTA Coder, compaction, QEngine y rigor de Q172 todavía requieren conciliación individual con fuente, fingerprint, dependencias y receipts. No ejecutar todos automáticamente: separar test local ejecutable de implementación/fixture/licencia externa y duplicados.


## Checkpoint Q202.87 — método de init cold/hot pre-registrado

Se añadió la medida de inicio cold/hot por perfil a 8K con probe local `mincore` y `fadvise` limitado al archivo de pesos; no se borra caché global ni se lee el contenido del modelo desde el probe. Se fijaron umbrales (cold <=5%, hot >=95%, MemAvailable >=32 GiB, PSI <1%) y timer spawn→health/model. La amendment quedó sincronizada/readback PASS en Accionables!72 e IA local!121; no hubo inferencia ni GPU. El próximo paso es validar el probe CPU-only tras fresh preflight y sincronizar ese resultado antes de inicializar el primer runtime. La revisión del resto de pestañas IA permanece abierta.


## Checkpoint Q202.87 — cache probe logged



## Checkpoint Q202.88 — cold-cache gate

El probe cold de `file_cache_probe.py` pasó el gate preregistrado: 0/4.286.909 páginas residentes; aplicó `POSIX_FADV_DONTNEED` sólo al GGUF exacto y no leyó su contenido ni usó GPU. No mide init ni TPS. El resultado quedó registrado y leído de vuelta en `Resultados!A446:AH446`, `Accionables!D72:N72`, `IA local!I121:L121`, `Modelos locales por peso!X32` e `Inventario de modelos!R41`; se conservaron los datos históricos y formato.

Preflight: sin servidor ni compute app, puertos de prueba libres; PNY pmon sólo Xorg; cuarentena ASUS 1636/1636, helper current-boot PASS, P2P bidireccional OK y `gpu_unlock` apunta a ambas PCI. La UI permanece activa y la carga gráfica se anota como posible ruido. Próximo: preflight nuevo, revalidar el estado cold y ejecutar únicamente init cold 8K del control llama.cpp single-PNY si todas las gates siguen pasando. La reconciliación amplia de pestañas y filas de IA permanece incompleta. Sync receipt: `profiles/qwen38-megakernel-v2026.11.01/receipts/sheet-sync-q20288-cold-cache-probe-20261103T032525Z.json`.

## Checkpoint Q202.89 — caché repoblada antes de init

El gate mincore de solo lectura volvió a observar el GGUF completamente residente (4.286.909/4.286.909; 100%). No se arrancó el servidor porque el umbral cold preregistrado es <=5%. No había servidor ni compute app, `fuser` estaba vacío, y las protecciones de ambas GPU verificaron PASS. El cache puede haberse repoblado durante el intervalo; la lectura integral de SHA-256 solicitada en ese intervalo es una causa posible, no demostrada. Se registrará este diagnóstico en `Resultados` y se actualizará la fila del accionable. Enmienda siguiente: ejecutar el cold probe y el spawn de llama.cpp en una secuencia inmediata con gate, sin lecturas completas del modelo ni sincronización entre ambos. Reconciliación global de pestañas IA sigue abierta.

La fila `Resultados!A447:AH447`, `Accionables!D72:N72`, `IA local!I121:L121`, `Modelos locales por peso!X32` e `Inventario de modelos!R41` se actualizaron y leyeron de vuelta; no se inició inferencia. Sync receipt: `profiles/qwen38-megakernel-v2026.11.01/receipts/sheet-sync-q20289-cache-rewarm-20261103T032820Z.json`.

Q202.90 cold-init 8K del control llama.cpp quedó preregistrado en `profiles/qwen38-megakernel-v2026.11.01/receipts/q20290-cold-init-prereg-amendment.json`, con runner fijado por hash. La caché se invalida sólo para el GGUF y el servidor se lanza inmediatamente después de pasar `mincore`; no se hace lectura/hash o sync entre gate y spawn. Preregistro aún debe sincronizarse y leerse de vuelta antes de la prueba; servidor aún no iniciado.

## Checkpoint Q202.90 — preregistro sincronizado y preflight actual

El preregistro fue leído de vuelta y se corrigió el hash obsoleto del runner en las dos notas de inventario. Preflight fresco 2026-11-03T03:35:16Z: no hay inference server, puertos de prueba libres, GPU1 sin proceso CUDA (Xorg permanece activo), RAM/PSI dentro de gate; helper del boot actual, cuarentena ASUS, P2P y `gpu_unlock` pasan. Los valores y formatos de Accionables!72 e IA local!121 fueron leídos de vuelta. El test sigue sin iniciar. Próximo: ejecutar una vez el runner cold-init en GPU1; si su gate `mincore <=5%` no pasa, no lanza el servidor. Luego registrar/readback en las pestañas correspondientes. Reconciliación de las otras filas y pestañas de IA continúa incompleta.

## Checkpoint Q202.90 — resultado y reconciliación de referencias

El runner Q202.90 completó una muestra diagnóstica de init cold en el control llama.cpp b67849b, con la huella fijada, PNY GPU1 y contexto 8K+256. Pasó el gate cold (0/4.286.909 páginas residentes), alcanzó `/health` y el modelo esperado en 31,857 s, y cerró su proceso hijo con código 0. No envió prompts ni generó tokens; no mide Q173, Q172, hot init ni superioridad. El resultado está en `Resultados` bajo el ID estable `VF-MEGAKERNEL-COLD-INIT-A-8K-20261103`.

El filtro/orden de `Resultados` movió filas; no deben usarse sus números como referencias duraderas. Se corrigieron las referencias numéricas de Q202.84/Q202.88/Q202.89/Q202.90 y Q45 EG2 por IDs estables. El readback confirmó las celdas afectadas y un escaneo de las 11 pestañas de IA no encontró más referencias `Resultados row/fila N`. El Q45 que no alcanzó el gate es `Q45-EG2-AGENTTOOLRUNNER-E2E`; no se cambió su resultado. El recibo de reparación es `receipts/sheet-sync-q20290-row-reference-repair-20261103T034805Z.json`.

PeritoSoft estaba abierto en GPU0 y se conservó. No había servidor de inferencia ni listener en los puertos de evaluación; GPU1 mostró Xorg en `pmon` (108 MiB; utilización global instantánea 33%). Antes de cualquier Q173, repetir preflight y anotar actividad gráfica. El siguiente test es el primer punto 8K del preregistro Q202.86 en PNY GPU1, perfil A, sólo si pasan las gates y la GPU sigue libre de inferencia/trabajo ajeno. La reconciliación completa de pestañas y filas de IA permanece abierta.

## Checkpoint Q202.91 — relectura transversal y preregistro de init caliente (2026-11-03T03:54:00Z)

Se volvió a leer el metadata y los valores ocupados de las diez pestañas objetivo. Conteos observados (filas no vacías, sin encabezado): IA local 126; Evaluaciones LlamaCode 370; Accionables 76; Resultados 447; Modelos locales por peso 102; Inventario 70; Sin evaluar 1499; Enlaces revisados 755; Recursos 139; Perfiles de LlamaCode 104. No son conteos de pruebas abiertas: `Sin evaluar`, `Enlaces revisados` y `Recursos` mezclan destinos o temas no IA; perfiles y modelos tampoco implican automáticamente un benchmark. La conciliación completa por fila, ID/fingerprint, destino y recibo sigue abierta.

Accionables contiene trabajo de IA ya cerrado, pruebas con dependencias externas y propuestas que primero requieren implementación o fixtures. Entre los pendientes registrados siguen: validación de aislamiento/orden de tools, fixture de pedido ambiguo, Q182 ISTA/Xolotl bloqueado por espacio y elegibilidad del motor dual, ruta híbrida sin llamadas externas, compatibilidad NInfer Flash-Next, Smart Turn, voz, OCR, Ghidra MCP, CUA, Router/Worker, compaction, Speedy/SparseKV, LFM3 Omni y cuatro candidatos nuevos Q202.73–Q202.76 que aún requieren reconciliarse con sus fuentes y recibos. No se los cuenta como benchmarks automáticamente ejecutables; se revisarán sus gates uno por uno.

Q202.91 hot init A ya está cerrado: pasó mincore 100% y readiness en 3,290976318 s (n=1, sin prompts); Xorg mostró actividad gráfica alta justo después y la muestra es solo diagnóstica. Resultado con ID estable `VF-MEGAKERNEL-HOT-INIT-A-8K-20261103`; Sheets se actualizó y leyó de vuelta en `Resultados`, `Accionables`, `IA local`, `Modelos locales por peso` e `Inventario de modelos`. Ver `profiles/qwen38-megakernel-v2026.11.01/receipts/q20291-hot-init-execution.json` y `profiles/qwen38-megakernel-v2026.11.01/receipts/sheet-sync-q20291-hot-init-result-20261103T035814Z.json`.

La conciliación integral por fila/ID/fingerprint de las diez pestañas objetivo continúa incompleta; los conteos de filas no se consideran pruebas pendientes. Próximo test de este perfil, no un cierre del objetivo global: Q173 8K A×3, solo PNY GPU1, después de preflight fresco y con writeback/readback antes de B. PeritoSoft y GUI quedan intactos; GPU0 no se usa en este experimento. No se ejecutará 523904.

## Checkpoint Q203.11 — CPU exactness y sincronización de resultado

El fixture local de prompts exactos pasó 12/12 (4 repeticiones por cada objetivo 65524/65525/65526); no cargó modelo, servidor ni GPU. La lectura de vuelta confirma `Resultados!A469:AH469` con `CPU_FIXTURE_PASS_GPU_PENDING`, y los estados enlazados de `Accionables`, `IA local`, `Modelos locales por peso` e `Inventario de modelos` reflejan PASS CPU y etapa GPU pendiente. Se corrigieron dos notas de perfil/inventario que aún describían el fixture como pendiente; los valores numéricos de perfiles y Q190 no se tocaron. Readback receipt: `profiles/qwen38-megakernel-v2026.11.01/receipts/sheet-sync-q20311-cpu-readback-20261103T0909Z.json`.

Esto valida solo la re-tokenización local del texto del usuario; no prueba que el servidor reporte 65536 ni mide TPS/calidad. Próximo: runner Q203.11 con fresh preflight; si alguna gate falla, registrar bloqueo y no iniciar el servidor. Sigue abierta la conciliación fila por fila de las pestañas AI y la selección de pruebas de OCR, RAG, voz, herramientas, agentes, seguridad e integración.


## Checkpoint Q202.93 — primer bloque Q173 preregistrado

La reconciliación de pestañas IA sigue abierta; este benchmark es un candidato de motor/runtime ya anotado en `IA local` y `Accionables`. El nuevo preregistro resuelve la secuencia ambigua del protocolo como A×3 → B×3 → A-repeat×3 → C×3 a 8K, y aplica el ladder completo solo hasta 261888. Q202.93 A 8K×3 está sincronizado/readback PASS en `Accionables!D72:N72` e `IA local!G121:L121`; no hay resultado de inferencia todavía. El preflight reportó Xorg gráfico en GPU1 (una muestra pmon 49% SM), que se conserva y puede contaminar velocidad; no se detuvo. Próximo: repetir gates justo antes de lanzar A; actualizar `Resultados`, `Accionables`, `IA local`, la fila correcta de `Modelos locales por peso` e `Inventario de modelos` después del bloque y leerlo de vuelta antes de B. Los demás candidatos de todas las pestañas siguen pendientes de reconciliación y selección.

- Q202.93 A 8K launch attempt 1: recorded in Resultados as setup failure before any inference (missing output directory; 0 requests/tokens). It is not a model score. Updated/read back Resultados, Accionables, IA local, Modelos locales por peso, and Inventario; retry remains pending after corrected output path and fresh preflight. Other AI-tab reconciliation remains open.

- Q202.93 A 8K attempt 2 produced three successful HTTP generations, but the actual server prompt usage was 8193 rather than the preregistered 8192; raw TPS are retained as diagnostics and excluded from comparisons. The invalid record is synchronized/read back in all linked model sheets. Corrected-count A×3 remains pending; broader evaluation of the other AI tabs also remains open.

- Q202.94 validó el primer punto de velocidad de qwen38-megakernel perfil A: 8K efectivos, 3/3 requests, P=1133,40±2,95, D=32,589±0,175 tok/s, TTFT=7,228±0,019 s. Q172 no medido. Resultados y filas enlazadas pendientes de sync/readback inmediato. La evaluación de las otras pestañas de IA sigue abierta.

- Q202.95 B 8K attempt 1: harness setup error before inference (missing preregistered output directory; 0 requests/tokens), recorded as non-model failure. Corrected directory is ready; B retry pending after fresh preflight. Broader reconciliation across all AI tabs remains open.

- Q202.95 validó Q173 perfil B a 8K efectivos: P=1395,96±19,29, D=41,869±0,167 tok/s, TTFT=5,870±0,082s; 3/3 requests exactos (8192 server tokens) sin error. La comparación A/B queda provisional hasta A-repeat; calidad Q172 pendiente. Resultado sincronizar/readback antes del siguiente bloque; el resto de pestañas IA sigue abierto.

- 2026-11-03T04:31:37Z — Q202.95 B fue verificado por readback en Resultados!A454:AH454, Accionables!D72:N72, Modelos locales por peso!X32 e Inventario de modelos!R41. Los valores exactos, estado y formato están registrados en `profiles/qwen38-megakernel-v2026.11.01/receipts/sheet-sync-q20295-result-readback-20261103T043137Z.json`. La reconciliación global sigue abierta; el siguiente tramo del ladder es A-repeat 8K×3, con preregistro y readback antes de GPU.

- 2026-11-03T04:34:42Z — Q202.96 A-repeat Q173 8K quedó preregistrado localmente (SHA-256 8f3d474409af205d6d4f626e49eb99aeb66e1dd3d259716e7c10ec1bcd891d6a); todavía no se envió al Sheet ni se ejecutó. En la auditoría de evidencia se detectó que el JSON histórico de Q202.94 tiene error sintáctico en el argumento chat-template; el nuevo prereg fija args desde Q202.93 válido y mantiene la corrida anterior como evidencia con trazabilidad reducida, sin reescribirla. La conciliación completa de pestañas IA sigue abierta.

- 2026-11-03T04:35:53Z — Q202.96 preregistro A-repeat sincronizado/readback PASS en Accionables, IA local, Modelos locales por peso e Inventario (ver `profiles/qwen38-megakernel-v2026.11.01/receipts/sheet-sync-q20296-prereg-20261103T043553Z.json`). Aún no hay prueba ejecutada; la reconciliación de todas las pestañas IA sigue abierta. Próximo: live preflight y A-repeat solo si las gates pasan.


## Checkpoint Q202.96 — attempt1 setup failure and attempt2 amendment

2026-11-03T04:49:31Z: Q202.96 attempt1 started the pinned llama.cpp server on PNY GPU1 and reached `/health`, but `python3 run_seeded_benchy.py` exited 1 before its first request with `ImportError: No module named llama_benchy`. Requests=0/3, tokens=0, no result/progress file, P/D/TTFT/Q172=N/D. This is a harness interpreter mismatch, not a model failure. The owned server was stopped; port18380 and CUDA compute apps were clear. Startup-only telemetry peaked at 17,156 MiB/36°C and global GPU1 utilization ranged 4–79%; those samples are not benchmark metrics. Attempt receipt `receipts/q20296-a-repeat-attempt01-harness-dependency-failure.json` SHA-256 `a92c9a39d700c6bd6e29777bfda8189acb0bc4cd6f012754cf178f6c9f52e10f`.

The dependency was already installed in `/home/cristian/.cache/q173-llama-benchy-0.4.0` (Python3.12.3, llama-benchy0.4.0); no package was installed or changed. Amendment `receipts/q20296-a-repeat-attempt02-python-env-amendment.json` SHA-256 `55c45eff239e541d7dc09be6d70d9c19068fe57871dd4aa316c40bb4ade9ceeb` pins that interpreter, verifies the Python/package files and pip-freeze hash, and assigns a new output folder so attempt1 logs are preserved. The model/runtime/seed/workload/GPU and validity gates are unchanged.

Attempt1 is recorded in `Resultados!A455:AH455` and read back exact (34/34); Accionables, IA local, Modelos locales por peso and Inventario were updated/read back. Receipts: `receipts/sheet-sync-q20296-attempt01-setup-failure-readback-20261103T0445Z.json` SHA-256 `b289d533c882d42746dd9a545eb7cd4dcdc587aaef9cdfe2001cc1855cf46973`; attempt2 prereg sync `receipts/sheet-sync-q20296-attempt02-amendment-20261103T0446Z.json` SHA-256 `879235b118cd6cd88a083708d0a64d017b42a4abe61dc63744fc10dd8057c829`; final Accionables status readback `receipts/sheet-sync-q20296-attempt02-final-readback-20261103T044856Z.json` SHA-256 `646a20564432092baecf4971f3cd83a5739993d8814e9a1c692c90833778fba6`.

Next: re-read the four repo instructions and run a fresh preflight, then attempt2 only if the venv still imports llama-benchy0.4.0 and all resource/temperature/protection gates pass. Keep the GUI/Xorg and GPU0 processes untouched. Sync/read back attempt2 before C. Full AI-tab reconciliation remains open.

## Q203.00 preregistro — sync/readback PASS

El test confirmatorio B 8K quedó preregistrado en Resultados!A457:AH457, lectura de vuelta exacta (34/34), con P/D/Q172 en N/D. Se actualizaron y leyeron de vuelta Accionables!D72:K72, IA local!I121/L121, Modelos locales por peso!X33 e Inventario de modelos!C41/R41; se conservaron Q202.96 A-repeat y Q190 dual-GPU como perfiles/resultados separados. Receipt profiles/qwen38-megakernel-v2026.11.01/receipts/sheet-sync-q20300-prereg-readback-20261103T051549Z.json (SHA-256 f97e01e8765b2a302490142f9856c9e4ca31bafe4e61933cfe2e069eb4be45ae). No se usó GPU ni se inició servidor. Próximo: preflight vivo y ejecutar un único bloque B×3 solo si todas las gates pasan. Esto no completa la reconciliación: las demás pestañas de IA siguen pendientes de auditoría y selección de pruebas.


## Q203.00 attempt 1 — preflight bloqueado, sin inferencia

2026-11-03 05:18 UTC: el supervisor bloqueó el ensayo B confirmatorio antes de iniciar servidor o cliente. La utilización global de GPU1 varió 37 puntos porcentuales durante la ventana de reposo, superando el gate preregistrado de ≤15 pp. No se enviaron solicitudes ni tokens; P/D/TTFT/Q172 permanecen N/D. No es fallo del modelo ni un benchmark válido. No se detuvo Xorg ni ningún proceso externo. Evidencia del supervisor: `receipts/q20300-b-confirm-preflight-blocked.json`, SHA-256 `9172fa37d0b890857032b73a4e30a5f46317836a6cd1327441c4dc2508572580`; sync/readback del resultado: `receipts/sheet-sync-q20300-blocked-preflight-readback-20261103.json`, SHA-256 `32ccb8bd4db4e48481b7fe31988cc8bc6d4b63d2260d82e79ca59091d3622f7c`. Resultados fila 457 conserva el estado bloqueado y las métricas vacías; fila 456 Q202.96 no cambió. Se corrigió en Accionables!K72 la nota contradictoria “readback pending”; el resultado PASS del readback permanece. Reintentar sólo tras una ventana de reposo nueva que cumpla ≤15 pp y los demás gates. La conciliación de todas las pestañas IA sigue abierta.

## Q203.01 — preregistered GUI-allowed confirmation (2026-11-03T05:59:09Z)

Como Q203.00 fue bloqueado antes de inferencia únicamente por variabilidad global atribuida a Xorg, se registró un intento nuevo e independiente que permite la carga gráfica de escritorio y la registra como covariable. No se mata Xorg ni otros procesos. Se conservan los controles para inference servers, CUDA compute ajeno, puertos, telemetría, memoria, PSI, temperatura, disco, fingerprints y protecciones de ambas GPU. El bloque sigue siendo Q173 de velocidad a 8K, 3 solicitudes exactas y una PNY GPU1; no mide Q172 ni dual-GPU. Prereg local `profiles/qwen38-megakernel-v2026.11.01/receipts/q20301-b-confirm-gui-prereg.json`, SHA-256 `59fe65ffa4b11d08159c56277100911f16d653c5531fcf905cc81d6c554319ac`; supervisor SHA-256 `f2d1a61b6ad2f443ff1157d68dbe33bbb147365dc3951f361562e5448a9d77c7`.

El preregistro quedó sincronizado y leído de vuelta: `Resultados!A459:AH459` (34/34), con filas456–458 preservadas; `Accionables!D72:N72`, `IA local!I121:L121`, `Modelos locales por peso!X33` e `Inventario de modelos!R41` también fueron verificados. Receipt `profiles/qwen38-megakernel-v2026.11.01/receipts/sheet-sync-q20301-prereg-readback-20261103T055840Z.json`, SHA-256 `0cbe970bae63e1e36534eb7e5ad30dcc17c73dea99660bc5cd248076f8a7ef94`. No se ha usado GPU ni iniciado servidor. Siguiente: leer de nuevo las instrucciones y el lock, inspeccionar el estado vivo de procesos/servidores y ejecutar este bloque sólo si pasan los gates restantes. La conciliación y evaluación del resto de pestañas de IA permanece abierta.


## Checkpoint Q203.01 — B confirmation result reconciled (2026-11-03T06:07:13Z)

Q203.01 completó el bloque Q173 8K del perfil Megakernel B single-PNY: 3/3 requests exactos (8192/128), prefill 1416.5927±7.0123 tok/s, decode 41.93989±0.10900 tok/s y TTFT 5783.03±28.57 ms. Los umbrales confirmatorios preregistrados pasaron (+24.89%/+28.13% frente al pooled A y +1.48%/+0.17% frente al B anterior). No mide Q172 ni contexto largo/dual GPU y no sustituye Q190. Xorg se mantuvo activo como covariable; no se detectó compute ajeno; el cleanup terminó y las protecciones del sistema pasaron.

Sheets readback PASS: `Resultados!A459:AH459` 34/34, filas456–458 intactas; Accionables!D72:N72, IA local!I121:L121, nota de Modelos locales por peso!X33 e Inventario de modelos!R41 preservadas y actualizadas. Receipt `profiles/qwen38-megakernel-v2026.11.01/receipts/sheet-sync-q20301-result-readback-20261103T060526Z.json`, SHA-256 `aaff9359410f6710db78c43f655868ab8437764903f15ac70adc78b1a9412e4c`. El recibo de ejecución local está en la tabla anterior.

Siguiente acción: preregistrar y sincronizar Q173 32K de este mismo perfil single-PNY antes de cualquier ejecución. Después continuar el ladder sólo si el preflight nuevo pasa. La conciliación amplia de todas las pestañas de IA (incluidas voz/OCR/RAG/agentes/seguridad/integración) sigue incompleta; revisar fila por fila contra fingerprints y recibos y no repetir pruebas cerradas.


## Checkpoint Q203.02 preregistro reconciliado (2026-11-03T06:16:31Z)

Se verificó de nuevo el preregistro del último brazo faltante a 8K, perfil C/MTP-7, en `Resultados!A460:AH460` (34 campos) y las filas 456–459 permanecen en su orden/ID. Las pestañas Accionables, IA local, Modelos locales por peso e Inventario contienen las referencias actuales; el A-control single-PNY sigue con 1134,26/32,73 tok/s y Q172 vacío, sin mezclarse con Q190 dual-GPU. Formato y ausencia de validación preservados. Receipt local de readback: `profiles/qwen38-megakernel-v2026.11.01/receipts/sheet-sync-q20302-prereg-readback.json`, SHA-256 `85bc70c0efd47f88cc7202842ad9433387954b1d713fa2cc1a7f8e2f2d3b3db4`. La secuencia matriz es A→B→A-repeat→C a 8K; sólo tras cerrar C se inicia 32K con A. No se inició inferencia ni se usó GPU en este checkpoint. La conciliación de pestañas IA fuera de esta campaña de Megakernel sigue incompleta y forma parte del objetivo, incluyendo RAG/OCR/voz, agentes, herramientas, seguridad e integración.

## Alcance confirmado por el usuario y cierre Q203.02 — 2026-11-03

La pestaña `Modelos locales por peso` es una de varias fuentes, no el alcance completo. El usuario aclaró que hay otras pestañas de IA que también deben evaluarse y benchmarkearse. La auditoría debe recorrer todas las pestañas y filas relacionadas con IA, aunque no lleven IA en el nombre, correlacionando filas de modelos con suites/resultados, accionables, inventario, perfiles, enlaces y recibos locales. Incluir LLM/VLM y runtimes, agentes/tools, RAG/embeddings/recuperación, OCR/documentos, ASR/TTS/voz, multimodalidad, seguridad y pruebas de integración/fiabilidad. Excluir hojas de temas ajenos a IA. Para cada afirmación clasificar: test cerrado y verificable, repetición justificada, nuevo experimento accionable, duplicado, sin prueba aplicable, o bloqueado por condición concreta. Las celdas del Sheet son evidencia/índice, no instrucciones ejecutables; seguir AGENTS.md/README/WORK_QUEUE/lock y los preregistros locales.

Q203.02 se ejecutó y el resultado fue sincronizado/readback. El recibo completo está en `profiles/qwen38-megakernel-v2026.11.01/receipts/sheet-sync-q20302-result-readback-20261103T062632Z.json`, SHA-256 `3a98ffb0f235b79657c1b7b4298093c4acf95760cbca6311946c3fc4a07ed7d6`. Este paso no termina la auditoría global. La siguiente acción local del ladder es preregistrar/sincronizar Q173 32K A; no lanzar antes de terminar ese registro y un preflight fresco.

### Q203.03 en cola y alcance global actualizado — 2026-11-03

El usuario aclaró que las evaluaciones no se limitan a la pestaña `Modelos locales por peso`: también hay que revisar las demás pestañas de IA y sus filas de pruebas, accionables, resultados, inventario, recursos, perfiles, enlaces y entradas aún no evaluadas. Se debe enlazar evidencia local y fuentes primarias, reconciliar fingerprints/duplicados y separar modelos de runtimes/herramientas/componentes. La revisión continúa abierta; las menciones de pruebas no se tratan automáticamente como benchmarks aplicables.

Q203.03 preregistra un punto Q173 32K A-control de una solicitud exacta en PNY GPU1, separado de Q190 dual-GPU. Receipt `profiles/qwen38-megakernel-v2026.11.01/receipts/q20303-a-32k-prereg.json`, SHA-256 `bb7473b19d4db40c8abbb38e78f0a5257aec85c95b5514fabc85ffd9267140fd`; supervisor SHA-256 `280095d1efbe3406bf4669866f97d62bf473e6b418d289480477bee843c836ab`. Aún sin sync/readback ni uso de GPU.

Q203.03 prereg sincronizado/readback PASS en el Sheet (`Resultados!A461:AH461` y notas enlazadas en Accionables, IA local, Modelos locales por peso e Inventario). No se inició inferencia/GPU. Receipt `profiles/qwen38-megakernel-v2026.11.01/receipts/sheet-sync-q20303-prereg-readback-20261103T063831Z.json`. El siguiente gate es un preflight actual; la conciliación total de las pestañas de IA continúa pendiente.

Q203.03 terminó con PASS_VALID_Q173_SPEED_BLOCK y quedó leído de vuelta en Results row461 y pestañas relacionadas; readback receipt `profiles/qwen38-megakernel-v2026.11.01/receipts/sheet-sync-q20303-result-readback-20261103T064515Z.json` SHA-256 `9f8007306ddbdd28868cc91d6b84c8b1cc1094cc7a8547c26e9267c20f7c343d`. Q172 y seguridad siguen N/D; Q190 dual-GPU no fue tocado. La reconciliación de todas las pestañas de IA sigue abierta.

- 2026-11-03T06:55Z — Q203.04 B/MTP-off Q173 32K preregistro verificado de nuevo en Google Sheets: Resultados fila462 (34/34 celdas), Accionables fila72, IA local fila121, Modelos locales por peso X33 e Inventario R41. Estado PREREGISTERED_NOT_STARTED; P/D/Q172 sin métricas; formato WRAP/TOP/Arial10 preservado; Q190 dual-GPU intacto. Receipt `profiles/qwen38-megakernel-v2026.11.01/receipts/sheet-sync-q20304-prereg-readback-20261103T20261103065509Z.json` SHA-256 `05e2cbe25bfddfed3ba75e3107c0c925188603fde88761b09bbaaeec5ae2c824`; prereg SHA-256 `352fb21847f540d3655e159437bf73060b9f8ceff5b738b6696451425871d82a`, runner SHA-256 `bf06f80f3ed6e4d9025ece35f81ebd16226bcc1948631a75a5774b68e5f3465d`. No se inició inferencia ni se usó GPU para el prereg/readback. Siguiente: preflight vivo y ejecutar solo B 32K si todas las gates pasan; si bloquea, registrar condición concreta. La reconciliación de todas las pestañas de IA continúa abierta.

- 2026-11-03T07:00Z — Q203.04 consistency amendment A1: pre-execution audit caught that the prereg said `--runs 1` while the original supervisor passed 3 and then required one request_end; it also compared this 32K point to pooled 8K A data with a confirmatory threshold. No model request or GPU use occurred. Corrected supervisor to exactly one request and removed the incompatible threshold, retaining only a descriptive same-context comparison to Q203.03 A-control 32K. AST/specific assertions PASS. Amendment SHA-256 `73eac5f0cb55f0b3595145611548be068418a71ce4083473afda0f46e1e634ad`; amended runner SHA-256 `0abeb564457538b18ef631e42a98008dac11f9edb7eb563d0cac6adb24846418`; original runner preserved and superseded before execution. Google Sheet updated/readback PASS: Results row462; dedicated B profile row34 in Modelos locales por peso, A row33 and C row35 preserved with numeric values/formulas intact; Inventario/Accionables/IA local linked. Local sync/readback receipt `profiles/qwen38-megakernel-v2026.11.01/receipts/sheet-sync-q20304-amendment-readback-20261103T0659Z.json`. No server/GPU used. Next: fresh full preflight; execute only B 32K if every gate passes. All-AI-tab reconciliation remains open.

- 2026-11-03T07:05Z — Q203.04 B/MTP-off, Q173 exact32K válido: 1/1 request usage32768/output128, seed42, P=1307.556471, D=40.051723 tok/s, TTFR=25060.49ms. n=1, descriptivo; contra A-control Q203.03 al mismo contexto: P +27.58%, D +29.29%, sin afirmar superioridad. Q172/calidad/seguridad y duración E2E total N/D; cold/hot no medidos. Preflight PASS: sin procesos de inferencia ni CUDA ajeno; ASUS quarantine/helper/P2P/gpu_unlock PASS; MemAvailable 109932482560B, PNY máx57°C, VRAM máx18028MiB; la utilización de escritorio se registró como covariable. Cliente exit0, server wrapper terminó por SIGTERM esperado; ports/compute apps libres. Ejecución `profiles/qwen38-megakernel-v2026.11.01/receipts/q20304-b-32k-execution.json` SHA-256 `b7e056b08615f066197cc73b44d23a518ee346d17ee01814e20f631ecf75d0d7`. Sheet Results row462 y pestañas enlazadas actualizadas/readback PASS; Modelos locales por peso row34 es perfil B independiente con P/D y Q172 N/D; A row33, C row35 y Q190 preservados. Sheet receipt `profiles/qwen38-megakernel-v2026.11.01/receipts/sheet-sync-q20304-result-readback-20261103T0705Z.json` SHA-256 `e7c5549163984a38053c240260b60b6276d97b3a10fe1f970a4219a5ae3e135f`. Siguiente: preregistrar/readback A-repeat a 32K, luego fresh preflight y ejecutar si pasan gates. Reconciliación de todas las pestañas IA sigue abierta.

- 2026-11-03T07:08Z — Q203.05 A-repeat Q173 exact32K preregistro sincronizado y leído de vuelta PASS: Results row463 (34/34 campos), Accionables row72, IA local row121, Modelos locales por peso X33, Inventario R41. P/D/output siguen vacíos; rows461 Q203.03 A y 462 Q203.04 B preservadas; formato WRAP/TOP/Arial10. Prereg SHA-256 `63d91e30c80fd40ca5fb33e7293b011e0ccb76ff5589cb2be4c74bf761d542a9`, runner SHA-256 `9abc1fcfa4d70544d4d4dd4728ac03b4a386bfda49694f2aeef4d395002d3a07`, Sheet receipt `profiles/qwen38-megakernel-v2026.11.01/receipts/sheet-sync-q20305-prereg-readback-20261103T0709Z.json` SHA-256 `5423dd59554583ac7223ffedbeb09f4ba8d108ee14a84d9e24f7aeac117d9137`. No inference/GPU iniciado. Próximo: preflight vivo y ejecutar solo A-repeat si pasan todas las gates; después sincronizar/readback y seguir con C. Reconciliación de todas las pestañas IA sigue abierta.


- 2026-11-03T07:15Z — Q203.05 A-repeat Q173 32K — PASS resultado y Sheet readback; Q203.05 A-repeat Q173 exact32K ejecutado, sincronizado y leído de vuelta PASS: request usage32768/output128, seed42, P=1023.7354386 y D=30.9591231 tok/s, TTFR=32.008s, client wall=73.945s (no estandarizado como E2E), n=1 descriptivo. Frente a Q203.03 A del mismo punto: −0.1162%/−0.0593%, repeat cercano; frente a B solo comparación descriptiva, sin ganador. Q172, seguridad, calidad, cold/hot N/D. Preflight confirmó sin inference server/compute ajeno, MemAvailable109949173760B, PNY máx59°C/18126MiB, ASUS quarantine 1636/1636 cero fallos y helper/P2P/gpu_unlock PASS; servidor propio exit0, puertos libres. Google Sheet actualizado/readback PASS en Resultados fila463 y rangos enlazados; Q190 dual-GPU y filas A/B/C separados. Medias provisionales single-PNY A por contexto: P=1079.296118/D=31.850269 tok/s (8K pooled n=6; 32K media de los dos A n=1 cada uno; media igualitaria por contexto), ladder incompleto. Ejecución receipt `profiles/qwen38-megakernel-v2026.11.01/receipts/q20305-a-repeat-32k-execution.json` SHA-256 `392bc4cb03b3052140baa0af474e26312c8f3aa1b0978ebc602f6337ab386334`; Sheet receipt `profiles/qwen38-megakernel-v2026.11.01/receipts/sheet-sync-q20305-result-readback-20261103T0715Z.json` SHA-256 `f3961972f115076b6400c9322a7cabd6b5382c9b0030bf60114ac93ed7b5743d`. Siguiente: preregistrar/readback C/MTP-7 Q173 a 32K, luego live preflight; ejecutar solo si pasa. La conciliación de todas las pestañas IA sigue abierta.

## Checkpoint Q203.06 prereg sync/readback PASS — 2026-11-03T07:24:32Z

`Resultados!A464:AH464` contiene el preregistro C/MTP-7 Q173 exact32K, 34/34 celdas leídas de vuelta; P/D/tokens siguen vacíos, Q172 y cold/hot init N/D, estilo igual a la fila463. `Accionables!D72/K72` actualizado/readback PASS; IA local, Modelos locales por peso e Inventario revisados en los rangos enlazados. No se inició inference server ni GPU. Receipt `profiles/qwen38-megakernel-v2026.11.01/receipts/sheet-sync-q20306-prereg-readback-20261103T072432Z.json`, SHA-256 `7fa6e2fc1aac01b91db073886ba374aeb189ecc36051347460a4b89ec32c1482`. Siguiente: preflight vivo, y ejecutar sólo C×3 si pasan las gates. Este checkpoint cubre únicamente este prereg; la auditoría fila por fila de IA local, Evaluaciones LlamaCode, Accionables, Resultados, Inventario, Modelos locales por peso, Sin evaluar, Enlaces revisados, Recursos y Perfiles permanece abierta.


## Q203.06 y corrección de consistencia del Sheet — 2026-11-03T07:37:15Z

Q203.06 C/MTP-7 Q173 exact32K quedó conciliado con el recibo local: 3/3 válidos, P=1301.959±6.249, D=116.484±12.856 tok/s, Q172 N/D. En una lectura en vivo se detectó que `Resultados!I464` aún decía que la ejecución estaba pendiente y `M464` describía las solicitudes como planeadas, aunque la hoja ya contenía métricas/resultados. Se actualizaron solo esas dos celdas y se leyeron de vuelta; el resto de las filas y perfiles vinculados se verificaron como preservados. Receipt `artifacts/evaluacion-modelos-llamacode/Q-20261103-VF-RESUME-202/profiles/qwen38-megakernel-v2026.11.01/receipts/sheet-sync-q20306-status-correction-20261103T073715Z.json` SHA-256 `d7b5a933cf3b46f37e9413a091a1f4eedf999c306811a44d34baacd79ab44077`.

Esto **no** completa la auditoría: el metadata actual lista pestañas AI/locales y pestañas de otros temas; queda cruzar fila por fila los candidatos y resultados de `IA local`, `Evaluaciones LlamaCode`, `Accionables`, `Resultados`, `Inventario de modelos`, `Modelos locales por peso`, `Sin evaluar`, `Enlaces revisados`, `Recursos` y `Perfiles de LlamaCode`, además de detectar otras filas AI en el workbook. La siguiente acción global es una reconciliación por ID/fingerprint y estado, no inferir que cada modelo sin métrica necesite el mismo test. Q173 64K A sigue como candidato del ladder, sin preregistro ni ejecución en este checkpoint.

 
## Checkpoint Q203.07 prereg Sheet readback — 2026-11-03T07:44:37Z

Resultados!A465:AH465 confirma el preregistro Q173 exact64K A-control; se corrigió la omisión de estado en Modelos locales por peso!X33 e Inventario de modelos!C41/O41, luego se leyeron de vuelta esos rangos, además de Accionables!D72:N72 e IA local!A121:O121. Receipt: profiles/qwen38-megakernel-v2026.11.01/receipts/sheet-sync-q20307-prereg-readback-20261103T0744Z.json. Esto reconcilia sólo el punto Q203.07, no la auditoría global. Sigue pendiente revisar fila por fila todas las pestañas y seleccionar/ejecutar otras pruebas concretas de IA. No se ejecutó inferencia ni GPU. Siguiente acción: fresh preflight Q203.07; si pasa, ejecutar ese único punto y sincronizar resultado.

## Q203.07 — A-control Q173 exact64K, ejecutado y sincronizado/readback PASS (2026-11-03T07:53:07Z)

Una solicitud exacta, usage=65536/output=128, seed42, single PNY RTX 3090 GPU1, llama.cpp CUDA b67849b profile A, q8_0 KV y caché desactivada. Prefill=872.344149 tok/s; decode=28.031274 tok/s; TTFT=75.126s; n=1 descriptivo. No mide calidad, seguridad, adopción ni rendimiento dual-GPU: Q172 permanece N/D. Preflight y limpieza pasaron: ASUS quarantine 1636/1636 sin fallos; 3090 HELPER/P2P/gpu_unlock PASS; servidor propio exit0, puertos libres y sin proceso CUDA ajeno. No se alteraron Q190, ASTRA, SOL ni PeritoSoft.

Google Sheets leído de vuelta: `Resultados!A465:AH465`, `Modelos locales por peso!A33:Z33`, `Inventario de modelos!A41:R41`, `Accionables!D72:N72` e `IA local!A121:O121`. El perfil single-PNY queda separado del perfil Q190 dual-GPU. Promedio descriptivo actual por igual peso de los contextos observados: P=1010.3121285 y D=30.5772704 tok/s; ladder incompleto y Q172 N/D. Formato WRAP/TOP/Arial10 y campos numéricos/fórmula de peso se conservaron. Recibo de readback `profiles/qwen38-megakernel-v2026.11.01/receipts/sheet-sync-q20307-result-readback-20261103T0753Z.json`, SHA-256 `f721d7f926e12a6adb8be617de86b8dd72dd677728644c356bb06ab8fd627ffb`; ejecución `receipts/q20307-a-64k-execution.json`, SHA-256 `7048ab629558b60ca1c2880afb844c0678cd4a37dcb41cf23311605f926f29c5`.

Siguiente: preregistrar y sincronizar/readback Q203.08 B-control exact64K, luego preflight vivo; ejecutar solo si pasan todas las gates. Continuar A-repeat/C y el ladder hasta 261888 conforme al preregistro gobernante. No ejecutar 523904. La conciliación de todas las pestañas IA sigue abierta.

## Q203.08 preregistro y readback — checkpoint histórico, supersedido por ejecución posterior (2026-11-03T08:00:23Z)

Q203.08 B-control Q173 exact64K es una prueba de rendimiento de modelo/runtime, registrada en `Resultados!A466:AH466` y enlazada con `Accionables!A72:N72`, `IA local!A121:O121`, `Modelos locales por peso!A34:Z34` e `Inventario de modelos!A41:R41`. Readback y formato PASS; no hay inferencia ni métricas nuevas. El candidato permanece separado del Q190 dual-GPU y de otros perfiles. La inspección transversal de IA continúa abierta: los perfiles de Megakernel no sustituyen el cruce de OCR, RAG, voz, herramientas, agentes, seguridad e integración.



## Q203.08 — B/MTP-off Q173 exact64K, resultado y Sheet readback PASS (2026-11-03T08:16:28Z)

Una solicitud medida válida: usage=65536/output=128, seed42, perfil single-PNY RTX 3090 GPU1. Prefill=1147.038910 tok/s, decode=37.037936 tok/s, TTFT=57.135s. El harness ejecutó además un warm-up 64K no puntuado, excluido de las métricas. Q172, seguridad, cold/hot init y duración E2E completa: N/D. Delta descriptivo contra A-control Q203.07 al mismo contexto: +31.49% prefill/+32.13% decode, n=1 por brazo; no establece superioridad ni adopción. Preflight y cleanup reportados PASS; ASUS quarantine 1636/1636 sin fallos, helper/P2P/gpu_unlock PASS, no quedó servidor propio ni puertos ocupados. GUI/Xorg se conservó y su actividad se registró como covariable.

Resultados sincronizados y leídos de vuelta en `Resultados!A466:AH466`, `Accionables!D72:N72`, `IA local!A121:O121`, `Modelos locales por peso!A34:Z34` e `Inventario de modelos!A41:R41`. Se corrigió el texto obsoleto que presentaba el resultado como preregistrado sin ejecutar; el checkpoint histórico se conserva marcado como supersedido. Promedios descriptivos del perfil B por igual peso de contexto (8K n=3, 32K n=1, 64K n=1): P=1290.396027 y D=39.676516 tok/s. Q190 dual-GPU permanece separado. Readback de formato: WRAP/TOP y Arial10 preservados donde estaban configurados; no se alteraron fórmulas ni valores numéricos. Verificación visual nativa no disponible porque CUA no presentó pestañas activas.

Ejecución: `artifacts/evaluacion-modelos-llamacode/Q-20261103-VF-RESUME-202/profiles/qwen38-megakernel-v2026.11.01/receipts/q20308-b-64k-execution.json` SHA-256 `a29f0d3c4a39b813fdabf238f55e5f69f790dfa03327718421a316d2fd09a6c9`. Sheet readback receipt: `artifacts/evaluacion-modelos-llamacode/Q-20261103-VF-RESUME-202/profiles/qwen38-megakernel-v2026.11.01/receipts/sheet-sync-q20308-result-readback-20261103T081628Z.json` SHA-256 `623350252f43f07e216be7ddcfaee4f718184cb2d55bfacd074c8c2e6e28f262`.

Checkpoint histórico supersedido: Q203.09 se completó y sincronizó; Q203.10 está preregistrado y leído de vuelta. La conciliación de pestañas y pruebas de IA fuera de este perfil sigue abierta.

## Q203.09 — A-repeat Q173 exact64K, PASS y Sheet readback verificado

Una solicitud válida en PNY RTX 3090 GPU1: usage=65536/output=128, seed42; prefill=872.123911 y decode=27.990477 tok/s; TTFT=75.145285 s. Frente a Q203.07 A-control del mismo contexto, los deltas fueron −0.0252% y −0.1455%, dentro de la tolerancia preregistrada ±15%. Es una repetición descriptiva n=1; no es resultado de calidad ni una afirmación de adopción. Q172 y cold/hot init siguen N/D. La ASUS permaneció en cuarentena; helper/P2P/gpu_unlock PASS. No quedó servidor ni puerto propio activo.

Resultados!A467:AH467 y las pestañas Accionables, IA local, Modelos locales por peso e Inventario se actualizaron y leyeron de vuelta. Execution receipt `receipts/q20309-a-repeat-64k-execution.json` SHA-256 `7f72d0cce18294149d2d1ade86b8af21a7ca5e3c1ca6dd8a1f44562058079b13`; Sheet readback `receipts/sheet-sync-q20309-result-readback-20261103T083025Z.json` SHA-256 `de408e2b1472b4a95762e654250b8b67731508550b4f727f47502d94b5ac1509`.

## Q203.10 — C/MTP-7 Q173 exact64K preregistrado y sincronizado

El preregistro `receipts/q20310-c-mtp7-64k-prereg.json` especifica tres requests seriales de uso exacto65536/output hasta128, en Megakernel C con MTP-7 sobre una PNY RTX 3090 GPU1; ASUS GPU0 queda excluida y su cuarentena intacta. Compara descriptivamente contra A/B/A-repeat al mismo contexto; no mide Q172, seguridad, calidad general, rendimiento dual-GPU ni adopción. No iniciar si falla cualquier gate.

Google Sheet: Resultados!A468:AH468 (34/34), Accionables!D72:N72, IA local!I121:L121, Modelos locales por peso!X35 e Inventario de modelos!C41:R41 quedaron leídos de vuelta; métricas todavía vacías/N/D y status `PREREGISTERED_NOT_STARTED`. Receipt `receipts/sheet-sync-q20310-prereg-readback-20261103T083713Z.json` SHA-256 `c518ee2341289b301528d683e09d3569a610b7786c26bcb81bd4b28865d23651`; prereg SHA-256 `e504cddee5ee90c09a81b9e82ff590702f4c69bf1364865adb332197a765f5b5`; runner SHA-256 `a4cbbebc6dafde55682facbdc09ea8cb4f693a5ea8dcc2d3a3bd6f4300083e2b`.

Preflight puntual más reciente: no aparece inference server ni listener de prueba; GPU1 muestra Xorg/actividad gráfica, permitido y medido como covariable. Esto no sustituye el idle baseline fresco de 30 s del runner. Siguiente paso: ejecutar el runner para ese preflight; este enviará C×3 solamente si todas las gates pasan. La conciliación fila por fila de todas las pestañas de IA continúa abierta. No ejecutar 523904; preservar ASTRA, SOL, PeritoSoft y GUI.

## Q203.10 — C/MTP-7 Q173 exact64K, ejecución inválida por token count (2026-11-03)

El runner pasó las gates duras y ejecutó el bloque C/MTP-7 serial en 1×PNY RTX 3090 GPU1. El cliente acabó con exit0 y `bench_complete=ok`, pero la validación preregistrada requiere 3/3 prompts de uso exacto65536: los conteos fueron 65536/65536/65537, por lo que el bloque queda `INVALID_Q173_EXACT64K_BLOCK`. Las salidas fueron 128 tokens cada una. P/D del harness por request se conservaron como datos parciales, sin agregarlos a la media del perfil: P 1145.334051/1134.543944/1129.318256 y D 77.364770/90.451296/78.385484 tok/s. TTFT por request 57.220/57.764/58.032s. El aggregate P=1136.398750±6.668665 y D=82.067183±5.943090 es de prompts con longitudes mezcladas y no se usa como resultado válido a 64K. Q172, calidad general, seguridad y cold/hot init N/D.

El baseline gráfico idle de GPU1 varió 40 puntos porcentuales; conforme al preregistro, las comparaciones de velocidad entre perfiles quedan contaminadas. La corrida fue una observación aislada, sin afirmación de superioridad. No había servidor ni compute ajeno; durante la prueba hubo cero foreign compute. El servidor propio se limpió; exit SIGTERM esperado, puertos18379/18380 libres y compute apps vacíos. MemAvailable 109.58GB, PSI pasó, PNY máx70°C y VRAM máx19604MiB. ASUS quedó excluida y su cuarentena/helper/P2P/gpu_unlock siguieron PASS; GUI conservada.

Google Sheet actualizado y leído de vuelta: `Resultados!A468:AH468`, `Accionables!D72:N72`, `IA local!I121:L121`, `Modelos locales por peso!X35:Z35` e `Inventario de modelos!C41`, `N41:O41`, `R41`. Los campos resumen prefill/decode de Resultados quedaron N/D y los promedios numéricos preexistentes del perfil C no cambiaron. Sheet receipt `profiles/qwen38-megakernel-v2026.11.01/receipts/sheet-sync-q20310-result-readback-20261103.json` SHA-256 `2addcef10064510d3e9e55521835c65012d22992019245adad94708243916e2e`; execution receipt `profiles/qwen38-megakernel-v2026.11.01/receipts/q20310-c-mtp7-64k-execution.json` SHA-256 `a42e720d77b6d65bf698d248035a2b78d7bd1103f0ffd97193929e69bb7ff539`.

Siguiente: preregistrar Q203.12 con prompt local objetivo65535 para compensar el token extra observado del chat template, validar el target en CPU, sincronizar/readback y correr preflight fresco. Ejecutar solo si todas las gates pasan. La auditoría fila por fila de las pestañas de IA sigue abierta. No ejecutar 523904; conservar ASTRA, SOL, PeritoSoft y GUI.

## Checkpoint Q203.11 — server-side exact64K attempt abortado

El fixture CPU (12/12) verificó longitudes del texto local, no el conteo después del chat template. En la ejecución single-PNY con preflight completo PASS, el primer request medido reportó server usage65537 frente al objetivo65536. Se completó una respuesta de128 tokens; P=1169/D=73.3 del log son únicamente diagnósticos, no métricas aceptadas. La solicitud medida siguiente empezó con el mismo desfase y se interrumpió; no hubo resumen de harness ni P/D válido. El supervisor propio limpió el server y los puertos; cero compute ajeno, ASUS quarantine/helper/P2P/gpu_unlock PASS y GUI conservada. La fila `Resultados!A469:AH469` mantiene Prefill/Decode=N/D; perfiles Q190/ASTRA/SOL y dependencias PeritoSoft siguen intactos.

Siguiente elemento de esta evaluación: Q203.12, ajuste preregistrado de un token en el texto local (objetivo65535) para lograr server usage65536; CPU fixture y Sheet sync/readback antes de otro preflight. Esto no cierra la conciliación general. Todavía hay que resolver las filas de IA de OCR/RAG/voz/herramientas/agentes/seguridad/integración y otras candidaturas por ID/fingerprint, recibo y prueba aplicable.


## 2026-11-03 checkpoint — all-AI-tab scope retained

Q203.12 prereg is now in Results row470 with linked notes synchronized/read back. This is one model-speed correction only. The audit still must reconcile every AI-related tab and evidence source row by stable test ID/fingerprint: `IA local`, `Evaluaciones LlamaCode`, `Accionables`, `Resultados`, `Inventario de modelos`, `Modelos locales por peso`, `Sin evaluar`, `Enlaces revisados`, `Recursos`, `Perfiles de LlamaCode`, plus any other rows containing AI evaluations. Include tools/agents/security, retrieval/RAG, OCR/documents, voice/audio, vision/multimodal and integration work; do not treat every model row as a benchmark. Q203.12 CPU fixture and GPU test are separate gates; only the latter uses GPU.


Q203.12 CPU fixture is PASS/readback PASS. It is a prompt-generator utility check, not a model benchmark or quality result. The wider all-AI-tab row/fingerprint reconciliation remains open.

Q203.12 setup checkpoint: the corrected prereg hash `7a83bbf3c14634e67e6a52566761399c89c4f4a77bf5e1ef2281a61a3079f717` and linked Sheet statuses are read back PASS. Two runner invocations stopped before preflight because of a malformed local Sheet readback receipt and a missing root-level runner hash alias; both were corrected without loading a model or using GPU. The remaining next step is a fresh gated preflight; the broad audit across every AI-related sheet tab remains open.

Q203.12 latest setup checkpoint: prereg hash `56f3f3c1fbd5b62bf4a0a1eb0ee7954263ee134ab2ad2045a569204c6ef7cbdb`, Sheet readback PASS receipt `2c98f905cc7f985c7fb599aca866b0c8d4b2c2982afc900cd5b3ba137be8f734`. A third launcher validation mismatch was caught and fixed before preflight; no model/server/GPU used. Next: runner fresh live preflight. The cross-tab audit and all other justified AI tests remain open.


## Q203.12 result readback and audit continuation — 2026-11-03T09:51:57Z

The Q203.12 64K C/MTP-7 GPU block is invalid (server usage 65536/65536/65537; exact gate 2/3). The CPU fixture is a separate 12/12 local-text check. The Google Sheet’s stale pending/not-started fields were corrected, and readback confirmed the result status, 128/128/128 output tokens, N/D accepted P/D and Q172, and actual resource/cleanup state. Readback receipt `artifacts/evaluacion-modelos-llamacode/Q-20261103-VF-RESUME-202/profiles/qwen38-megakernel-v2026.11.01/receipts/sheet-sync-q20312-result-readback-20261103T095157Z.json` SHA-256 `a9d8313c072a9fdd27560623689dd44c72124b2e6fcadedbf6bfa98ae50fbd4c`. No profile averages or Q190 dual-GPU data changed.

The active test-level next step is CPU diagnosis of request suffix/chat-template tokenization; preregister a new test ID and synchronize before any GPU retry. The broader cross-tab audit remains incomplete: reconcile all AI rows from `IA local`, `Evaluaciones LlamaCode`, `Accionables`, `Resultados`, `Inventario de modelos`, `Modelos locales por peso`, `Sin evaluar`, `Enlaces revisados`, `Resources/Recursos`, `Perfiles de LlamaCode`, and any other AI-related tabs against exact IDs/fingerprints and local receipts. Include agent/tool/security/integration, RAG/retrieval, OCR, voice, and multimodal evaluations; don't treat every model inventory entry as an executable benchmark.


## Checkpoint vivo 2026-11-03T10:14:48Z — alcance completo y gates de ejecución

La metadata actual lista las pestañas IA indicadas en el objetivo: `IA local`, `Evaluaciones LlamaCode`, `Accionables`, `Resultados`, `Modelos locales por peso`, `Inventario de modelos`, `Sin evaluar`, `Enlaces revisados`, `Recursos`, `Perfiles de LlamaCode` y `Panel`; además se conserva `Vista agrupada por tipo` como derivada. Conteos de lectura en vivo: IA local 126 (48 Sin probar, 38 Por investigar), Evaluaciones LlamaCode 370, Accionables 76, Resultados 470 filas de datos (incluye Q204 en fila 471), Enlaces revisados 207 fuentes IA local y Sin evaluar 206. La diferencia de una fila entre esas dos pestañas queda como comprobación de fórmula/filtro, no como omisión confirmada. Perfiles de LlamaCode: 104 filas (75 activas y 29 deprecadas); perfil activo no implica prueba pendiente. Estas cifras son una foto del índice; el cierre exige conciliación por ID/fingerprint y evidencia local, no sólo conteos.

PeritoSoft está activo y ejecuta Qwen3.5-9B en 8033 y 8081, Gemma 4 12B en 8083, OCR y RAG. A las 10:13–10:14Z GPU0 mostraba 13821 MiB / 90% y GPU1 11514 MiB / 27%. No se libera GPU ni se inicia prueba mientras esos procesos sigan activos. `/` 1.8 GB libres; HDD extra 245 GB. Sin descargas ni inferencia en este ciclo.

Q204 sigue preregistrado, sin modelo local; antes de cualquier servidor falta fijar argv exacto y hash de runner. Q203.12 se invalidó por prompt usage variable; la inspección local muestra que `exact_prompt.py` ajusta tokens del texto antes del chat template, por lo que su PASS CPU anterior no cubre el conteo final del servidor. Continuar revisión documental y cruce del backlog AI mientras el gate de recursos persista.


## Matriz de aplicabilidad de Accionables 61–77 — 2026-11-03T10:16:02Z

| ID | Estado observado | Aplicabilidad de prueba / condición concreta |
|---|---|---|
| INGI-VOICE-SMARTTURN-V3 | Pendiente; no implementado | No hay prueba del feature local hasta implementar el detector. Luego CPU ONNX con fixture consentido es_AR de frases, pausas, balbuceo y barge-in; baseline sintético previo no lo sustituye. |
| INGI-HARK-PROACTIVO-OPTIN | Pendiente; diseño opcional | No existe implementación para medir. Definir permisos, opt-in, deduplicación y revocación antes de prueba E2E. |
| INGI-QENGINE-DUAL3090-INT4-TP2 | Pendiente; licencia/hardware | Aún sin test local. Confirmar términos PolyForm y fixture; exigir RTX 3090 ASUS/quarantine y ambas GPU libres antes de benchmark. |
| INGI-TTS-TONECOLOR-AB | Pendiente; sólo diseño | Requiere frases de voz con consentimiento y definir métrica de similitud/RTF/first-audio; no aplicar claim de 600 MB sin medir. |
| INGI-GHIDRA-MCP-READONLY | Pendiente; plugin no auditado | Prueba CPU/fixture abierta posible tras auditoría del código, lista de tools mutadoras y sandbox read-only; Q138 no cubre esta integración MCP. |
| INGI-CUA-AGENTDESKTOP-20261102 | Pendiente; adapter no implementado | No hay integración local que medir. Primero adapter semántico y gate AT-SPI/X11; no forzar acceso a apps ni sesiones ajenas. |
| INGI-DSH-DEVBOX-ROUTER-GATE-20261102 | Pendiente; sólo diseño | No existe implementación local. Autor benchmarks no son evidencia propia; tests sólo tras prototipo con sandbox, plan-review y audit log. |
| VF-REQUEST-COMPACTION-ANCHOR-20261102 | Pendiente; holdout no definido | Requiere fixture 6–12 tareas, hidden tests, semilla pareada, contexto 128K/262K y criterio de preservación antes del A/B. |
| VF-SPEEDY-SPARSEKV-3090-A-B-20261102 | Pendiente condicionado | Candidato depende SM86, memoria y seguridad. Primero verificar compatibilidad/runtime y política de KV; después preregistrar A/B en sandbox con mismos pesos. |
| VF-INDRA-OCR-PERITO-20261102 | Pendiente; licencia/fixture | Requiere verificar licencia de pesos y holdout consentido de documentos (idioma, tablas, sellos, rotación) antes de comparar CER/WER y orden. |
| INGI-LFM3-OMNI-VOICE-20261102 | Pendiente; compatibilidad/español | Requiere compatibilidad de Chromium/WebGPU en esta máquina y set es_AR; el claim de latencia M4 no permite decidir. |
| VF-MEGAKERNEL-3090-262K-Q172-20261102 | Q203.12 inválido a 64K | Server usage 65536/65536/65537; P/D y Q172 no aceptados. El generador cuenta texto antes del template; primero resolver tokenización server-side y preregistrar nuevo fixture. |
| VF-KVARK-SPARKLE-Q172-E2E-20261102 | Q204.00 preregistrado | No descargado ni probado. Falta argv completo/hash del runner; PeritoSoft ocupa ambas GPU. No detener procesos ni descargar en esta ventana. |
| VF-DS41-ISTA-CODER-VS-UD31-20261102 | Fila incompleta | No tiene estado/evidencia suficiente en Accionables. Resolver exactos hashes, runtime compatible y holdout Q172 antes de decidir si hay prueba nueva y viable. |
| VF-Q172-PARED-BENCH-QUANT-20261102 | Propuesta metodológica; campos incompletos | No es ejecución runnable todavía. Definir cohorte comparable, pares, semillas, métricas y umbrales antes de registrar una campaña. |
| VF-PMO-ODYSSEY-GITLAB-20261102 | Port nativo; sin claim de IA en la fila | Fuera de la campaña IA hasta que se identifique una evaluación concreta de IA. |
| VF-GOTHIC3VR-NEXUS-20261102 | Seguridad PCVR | Fuera del alcance IA especificado; no convertirlo en benchmark de IA. |

La lista anterior es sólo la sección de Accionables 61–77. El inventario de 126 fichas IA local, las fuentes de Enlaces revisados/Sin evaluar, las 370 evaluaciones históricas y las filas de Resultados siguen necesitando conciliación por ID/fingerprint.


Readback de bloqueo Q204 del 2026-11-03T10:16:02Z: `profiles/kvark-sparkle-1.0/receipts/sheet-sync-q204-live-blocker-readback-20261103T101602Z.json` SHA-256 `e854835e031645d2a0beacee34a0e2a8b1eb35dec0a138e12a6401093891f995`. Spreadsheet actualizado y leído de vuelta; no hay inferencia ni descarga.

## Checkpoint Q203.13 preregistrado — 2026-11-03T10:28:11Z

Q203.13 comprueba en CPU si 12 prompts no-cache distintos pueden calibrarse a 65.536 tokens **después** del template Jinja completo, en vez de contar solamente el texto del usuario como Q203.11/Q203.12. El fixture compara `tokenizer.chat_template` embebido en el GGUF con `tokenizer_config.json`, replica el entorno de template de `mk_server.py` y usa el tokenizer fast fijado. El lector GGUF mapea metadatos y no lee tensores; no se inicia servidor, inference, descarga, CUDA ni GPU. Incluso un PASS es solo un predictor CPU: el uso reportado por el servidor sigue siendo el gate definitivo de Q173.

Prereg local `profiles/qwen38-megakernel-v2026.11.01/receipts/q20313-full-template-exactness-cpu-prereg.json` SHA-256 `8373fb64009aed074ee6f6f8df7b337b69604600aa02c32cbe6094549456bb4e`; script `scripts/validate_q20313_full_template_exactness_cpu.py` SHA-256 `8cccc3e8c5c7ed2dc69353b3aa81dd4789a83480193fcd2a10172f045d5d1140`. Preregistro sincronizado y verificado en `Resultados!A472:AH472`, con referencias en `Accionables!D72:K72` e `IA local!I121:L121`; Q203.12 fila470 y Q204 fila471 se conservaron. Receipt de prereg/readback `receipts/sheet-sync-q20313-prereg-readback-20261103T1028Z.json`.

Q203.13 ejecutado el 10:30Z y falló de forma segura antes de calibrar prompts: el template de `tokenizer.chat_template` embebido en el GGUF difiere de `tokenizer_config.json`; 0/12 prompts, P/D/Q172 N/D. No se usó servidor ni GPU. Execution receipt `receipts/q20313-full-template-exactness-cpu-execution.json` SHA-256 `6bc8083061dfb17c9c5d8d9c52a11bffd7c434c450f8e7dacffc427d91b68a45`. El resultado se sincronizó/readback PASS en Resultados fila472, Accionables fila72 e IA local fila121; receipt `receipts/sheet-sync-q20313-result-readback-20261103T103145Z.json` SHA-256 `a43bc291260777fec8cc178ec70128ca75a2c1058109cd539bec915ca2491e95`. Q203.12 sigue inválido y sin métricas válidas.

Siguiente paso exacto: preregistrar Q203.14 CPU para verificar que los IDs del vocabulario GGUF coincidan exactamente con `tokenizer.json` y medir el delta entre templates; si coinciden, calibrar prompts solo con el template embebido que lee `mk_server.py`. Si el vocabulario no coincide, no confiar en conteos HF ni reintentar GPU. La reconciliación transversal de pestañas IA sigue abierta.

## Corrección de notas de Q203.14 — 2026-11-03T10:45:41Z

Se corrigió una escritura anterior que había reemplazado el texto histórico de `Modelos locales por peso!X33` e `Inventario de modelos!R41` al sincronizar el prereg Q203.14. La copia literal del texto anterior no está disponible en las revisiones recuperables. Se reconstruyó el resumen desde la historia aún presente en `Inventario de modelos!C41` y los recibos/resultados locales Q203.05–Q203.13; ambas notas identifican explícitamente que la restauración no es byte por byte. Se verificó de nuevo el prereg y su hash, y se corrigió una transcripción inicial equivocada del hash en esas notas. Los valores métricos, `Resultados!A473:AH473`, Q190 dual-GPU, ASTRA, SOL y los datos de PeritoSoft permanecen intactos. Readback: `profiles/qwen38-megakernel-v2026.11.01/receipts/sheet-sync-q20314-note-recovery-readback-20261103T104541Z.json`.

Q203.14 continúa `PREREGISTERED_NOT_STARTED`; no se ejecutó el diagnóstico en este checkpoint. Siguiente: revisar el preflight de CPU/IO y ejecutar solo el diagnóstico preregistrado de baja prioridad si la carga y el espacio de salida lo permiten. Después, registrar y leer el resultado de vuelta. La auditoría de todas las pestañas de IA —incluidas OCR, RAG, voz, herramientas, agentes, seguridad e integración— continúa abierta.


## Corte transversal de pestañas IA — 2026-11-03T10:55Z

Lectura de metadatos y valores de las 11 pestañas de trabajo relacionadas con IA, más `Panel`. El libro tiene 21 pestañas; Anime, PCVR, Quest3 Standalone VR, FlatScreen, Catálogo PC 2026, Recomp r36s, Maker y electrónica, VIDAA y la pestaña VR de respaldo quedan fuera cuando la fila no describe una evaluación de IA. `Recursos` es mixta y requiere filtro manual. Este corte es una triage transversal, no una conciliación final. Snapshot local: `profiles/qwen38-megakernel-v2026.11.01/receipts/ai-tabs-scope-snapshot-20261103T1055Z.json` SHA-256 `cfaeaa985165f0ca88f7b15f221cb9b26e69b06756c41d4a0786c563054d64ea`.

| Pestaña | Cobertura observada | Cómo interpretarla |
|---|---:|---|
| IA local | 126 filas; 48 “Sin probar”, 38 “Por investigar” | Pistas/fuentes; muchas no son ejecutables en RTX 3090 o son análisis documentales.
| Evaluaciones LlamaCode | 370 filas; 102 coincidencias léxicas de bloqueo/incompleto | El conteo incluye históricos cerrados; resolver por Q-ID, recibo y fingerprint antes de repetir.
| Accionables | 76 filas; 25 coincidencias léxicas de abierto/parcial | Mezcla tareas de implementación, bloqueos, cierres y propuestas; una fila R36S se excluye por no ser IA.
| Resultados | 472 filas; 64 coincidencias léxicas de pendiente/incompleto | Ledger, no cola automática; contiene no-go históricos y resultados parciales con gates cerrados.
| Inventario de modelos | 70 filas | Inventario de artefactos; distinguir modelo, perfil, auxiliar y fingerprint.
| Sin evaluar | 1.499 filas; 338 AI-keyword rows | Recibido/no recibido no equivale a benchmark pendiente. Estados de esas filas: 167 recibidas, 72 falta material, 97 vacías y 2 con Q204 pendiente.
| Enlaces revisados | 755 filas; 338 AI-keyword rows | Estados de acceso en esa cohorte: 228 verificados, 51 pendientes, 59 no verificables.
| Recursos | 139 filas; 50 matches de palabras clave | Incluye proyectos de juegos/hardware; no tratar cada match como prueba de IA.
| Perfiles de LlamaCode | 104 filas; 75 activos/experimentales | Los stable IDs no son fingerprint; falta unión automática exacta perfil→artefacto→resultado.
| Modelos locales por peso | 105 filas; 100 matches AI-keyword; 66 sin prefill, 65 sin decode, 75 sin Q172 | No es una cola homogénea: OCR/ASR/TTS/embeddings, drafters y componentes tienen métricas N/A, no Q173/Q172 pendientes.
| Vista agrupada por tipo | 104 filas | Vista derivada; no contarla como pruebas separadas.

### Cruce de fuentes y filas L733/L734

El cruce por ID entre las 338 filas AI-keyword de `Sin evaluar` y `Enlaces revisados` encontró 338 IDs emparejados. El registro L734 tenía los metadatos completos únicamente en `Enlaces revisados`; se copió a su fila de intake y se vinculó al Q204.00 existente, sin crear un test duplicado. La primera escritura apuntó una fila arriba; la lectura de vuelta detectó que había caído sobre L733. L733 se restauró desde su registro original y se leyó de vuelta comparándolo con `Enlaces revisados`. L734 conserva la casilla “no recibido por usuario” y su nota de siguiente paso es más específica para el fingerprint de Q204.00. No se cambiaron métricas ni filas de resultados. La secuencia de escritura y reparación está registrada en `profiles/qwen38-megakernel-v2026.11.01/receipts/sheet-sync-q20314-attempt01-amended-prereg-readback-20261103T1055Z.json` SHA-256 `2e34742302a7338cd858c4a3f96c3718245c71f75956df7a267c248fb3bdd62b`.

### Próximos gates

- Q193 Q172 terminó en semillas 42/43/44: 66/77/73, media 72/100; falló seguridad en las tres. Cerrado/no adoptar; no queda seed44 pendiente.
- Q203.14 continúa sin ejecución real. Intento 1 falló antes de iniciar el validador por una ruta relativa incorrecta; el prereg se corrigió y sincronizó. El retry CPU depende de una ventana CPU/IO segura: PeritoSoft mantiene servidores y trabajos RAG/OCR activos y la raíz tiene aproximadamente 1,8 GiB libres.
- Q204.00 sigue condicionado a completar el argv/hash del runner, verificar espacio y esperar la liberación natural de PeritoSoft; no detener servicios.
- El siguiente tramo de auditoría es reconciliar fila por fila los estados abiertos de `Resultados` y `Accionables` con los recibos locales; luego cruzar los candidatos de `IA local`, `Sin evaluar` y `Enlaces revisados`. Las coincidencias léxicas anteriores no son el número de pruebas accionables.


## 2026-11-03T11:01:52Z — reparación del estado obsoleto Q203.14

La lectura en vivo encontró `Resultados!E473` todavía indicando que el prereg corregido esperaba sync/readback, aunque el prereg Q203.14 ya estaba sincronizado. Se corrigió únicamente esa celda: intento 1 sigue `SETUP_FAILED_BEFORE_TEST` (ruta relativa incorrecta, validador no iniciado, sin entradas/servidor/CUDA/GPU); prereg sincronizado y leído de vuelta PASS; retry CPU/IO sigue pendiente de una ventana segura. El valor se leyó de vuelta exacto; Arial 10, WRAP/TOP y ausencia de validación se conservaron. No se ejecutó prueba en este paso. Recibo `artifacts/evaluacion-modelos-llamacode/Q-20261103-VF-RESUME-202/profiles/qwen38-megakernel-v2026.11.01/receipts/sheet-sync-q20314-status-cell-correction-20261103T1101Z.json`, SHA-256 `f6e62cafee1dcda289801fd98fb809d3736a89193a81530d6731be27b4b33b2b`.


## 2026-11-03T12:11:52Z — Q203.14 y lectura de vuelta del ledger

Q203.14 attempt 2 confirmó el bloqueo CPU-only por metadatos del tokenizer: GGUF 248,320 IDs frente a tokenizer.json 248,077; merges ordenados coincidentes, IDs `[PAD...]` sin mapa y `<|im_sep|>` representado como seis IDs. La calibración fue 0/12; no hay mediciones de inferencia, Q172, prefill/decode ni init. La lectura de vuelta encontró `Resultados!U473`, `V473` y `AD473` obsoletas frente a `E473` y `AF473`; se corrigieron y verificaron. No se modificaron métricas Q190, ASTRA, SOL ni registros de PeritoSoft. Recibo: `artifacts/evaluacion-modelos-llamacode/Q-20261103-VF-RESUME-202/profiles/qwen38-megakernel-v2026.11.01/receipts/sheet-sync-q20314-result-readback-2026-11-03T121152Z.json`.

La siguiente acción de este perfil es investigar fuentes/mapeos exactos de tokenizer o una vía de conteo probada del server; no repetir el mismo validador. La reconciliación global sigue abierta: mantener el cruce de IDs/fingerprints entre Resultados, Accionables, IA local, Inventario, Sin evaluar, Enlaces revisados, Recursos, Perfiles y demás pestañas IA; no inferir pendientes de benchmark por coincidencias léxicas ni por celdas vacías.


## 2026-11-03T12:24:35Z — Q203.15: matriz local de tokenizers y estado del ledger

Q203.15 comparó dos fuentes locales distintas contra el GGUF pinned, tras deduplicar por SHA la copia idéntica de AutoRound. El candidato AutoRound tuvo 243 IDs discrepantes (IDs [PAD...] anexados por el GGUF), merges ordenados 247,587/247,587 exactos y <|im_sep|> en seis IDs. El snapshot HF Qwen3.6 tuvo 250 discrepancias (siete tokens de audio ausentes además de pads), merges exactos y el mismo split de <|im_sep|>. Resultado FAIL_NO_EXACT_LOCAL_TOKENIZER; calibración exacta y Q173 siguen bloqueados. Dos fallos iniciales de preflight por intérprete/paquetes se corrigieron sin abrir modelo ni usar GPU; el preflight combinado pasó antes de ejecutar.

Se corrigieron y leyeron de vuelta las celdas de Resultados fila474, Accionables fila72, IA local fila121, Modelos locales por peso X35 e Inventario de modelos R41. El recibo verifica formato WRAP/TOP, presencia de hashes y que los campos numéricos Q190 quedaron intactos. Ejecución SHA-256 9eedb4039a4da6cd78c2092cbad764cdc5b24dc331328fb72cbe795d22a05de0; readback SHA-256 dea12f9b4e54c676877b19352918fa075f5dda8301a1cdb214d26894734426f3. La auditoría completa de pestañas IA continúa abierta; el siguiente paso de esta rama es leer el tokenizer path del runtime y no repetir candidatos ya descartados.


## 2026-11-03T12:51:58Z — Smart Turn v3.2 y avance de reconciliación IA

Se relevaron en vivo las pestañas IA del workbook y el estado de Accionables 61–77.
La fila `Accionables!B61` identifica `INGI-VOICE-SMARTTURN-V3`; no había modelo local
ni evaluación local de este artefacto. La fuente primaria de Pipecat declara español entre
23 idiomas, licencia BSD-2-Clause y una variante CPU int8 ONNX de 8 MB. Se fijó la
revisión HF `f766f81`; `smart-turn-v3.2-cpu.onnx` descargado a Disco local, 8,679,182 B,
SHA-256 verificado `2bb026316b14a660486a75b1733cd3fbab8c2fd0314dc9af7be49f8cca967e4f`. No se descargó el dataset de prueba de 4.84 GB.

Q191 aporta diez clips locales Piper sintéticos; no tienen etiquetas de fin de turno y no
permiten puntuar calidad. Quedó preregistrado un smoke técnico CPU con 3 pasadas por clip,
que reportará init/latencia/RSS y solo comprobará salidas válidas/repetibles. El resultado
no será Q172 ni calidad de voz rioplatense. Una evaluación de calidad requiere audio natural
etiquetado y cobertura es_AR. Prereg SHA-256 `df3884a25b231a626be148e901cc1c24f67a104286d5f63a3175e5889df85e3b`; runner SHA-256
`96c776fd8443c27299305d5c94d3319204b7c002dd0a85fe8b5826da3e10e107`.

Sheets: Accionables fila61 actualizada con estado y límites; Resultados fila475 contiene el
preregistro; Inventario de modelos fila73 y Modelos locales por peso fila109 agregan el
artefacto eval-only con Q172/P/D=`N/A`. Los pesos en la tabla por tamaño se almacenaron como
números (8,679,182 B y 0.008679182 GB; formato visible a seis decimales) y se leyeron de
vuelta. Recibos: `profiles/smart-turn-v3.2-cpu/receipts/sheet-prereg-readback.json` y
`profiles/smart-turn-v3.2-cpu/receipts/sheet-inventory-readback.json`. Attempt01 abortó antes de inicializar el modelo por un bug de clave en el runner; no hubo inferencia ni resultado. AMEND-01 corrige la lectura de `data.manifest_sha256`; attempt02 pendiente de preflight CPU.

En paralelo, la revisión de código del Megakernel localizó el método `prompt_tokens(body)`
y las rutas `POST /v1/chat/completions/input_tokens` y `/v1/responses/input_tokens`; el
servidor renderiza el mismo cuerpo y cuenta con su tokenizer sin generar tokens. Esto ofrece
una ruta distinta a los tokenizers locales ya descartados para un futuro Q203.16 de calibración
exacta, pero no se ha llamado a un servidor. El `llama-server` activo de PeritoSoft sigue
ocupando ambas 3090 y no se detuvo. Próximos pasos secuenciales: completar el smoke Smart
Turn en CPU con venv en Disco local; después, cuando GPUs/servicios estén naturalmente
libres, preregistrar Q203.16 usando el endpoint de conteo y reintentar solo los puntos Q173
habilitados. La auditoría fila por fila de todas las pestañas IA sigue abierta.


## Intento Smart Turn 1 sincronizado/readback — 2026-11-03T13:02:38Z

El intento 1 terminó con un error de setup antes de crear la sesión ONNX: el runner consultó una clave raíz de manifiesto que no existe. La clave correcta es `data.manifest_sha256`, cuyo hash coincide con el manifiesto local. No se procesaron clips, no se generó resultado y no se usó GPU. AMEND-01 modifica solo ese lookup; el artefacto, los diez inputs, runtime, criterios y política CPU-only permanecen fijados.

Se corrigieron y leyeron de vuelta `Resultados!E475`, `G475`, `AD475`, `AF475`, `AG475`; `Accionables!D61`, `I61`, `M61:N61`; `Inventario de modelos!C73`, `R73`; y `Modelos locales por peso!X109`. Readback exacto y formatos anteriores conservados. Recibo `profiles/smart-turn-v3.2-cpu/receipts/sheet-attempt01-sync-readback.json` SHA-256 `4b429b7399bd19379b6fec97196346e22ca3be2d106c1a649f3b4832aa13cee9.

Siguiente: ejecutar únicamente el smoke técnico CPU preregistrado tras preflight fresco. Los clips sintéticos no permiten una conclusión de calidad; el Q172, prefill y decode siguen siendo N/A. La auditoría integral de pestañas IA continúa abierta.


## Smart Turn attempt02 — 2026-11-03T13:04:25Z

El smoke técnico CPU pasó con el runner AMEND-01. ONNX Runtime `CPUExecutionProvider` procesó los diez clips sintéticos tres veces cada uno (30 predicciones); todas las salidas fueron finitas en [0,1] y la diferencia máxima entre repeticiones fue 0.0. Init de sesión+extractor 21.705 ms; ONNX mediana/p95 20.552/23.583 ms; pipeline completo mediana/p95 30.430/57.261 ms; RSS pico 667,406,336 B. No hubo GPU ni servidor.

Esto no mide calidad ni detección correcta de fin de turno: los audios son sintéticos y no tienen etiquetas. Q172, prefill/decode y adopción permanecen N/A. Resultado local `profiles/smart-turn-v3.2-cpu/receipts/attempt02-technical-pass.json` SHA-256 `7f735f676719ec69e2c06de37635a1a0fe12adc801503881c98cdadf7ba46f5b`; salida bruta en Disco local con SHA-256 `0ef149b047fdfa901ae3cdb5eb293ea5afc8afa7c0ced7b611c79d93eb820f7b`. Las pestañas vinculadas se actualizaron y leyeron de vuelta (15/15 valores exactos, formatos conservados). Receipt `profiles/smart-turn-v3.2-cpu/receipts/sheet-attempt02-sync-readback.json` SHA-256 `e9939107863dcab61e28353e90c9b10937c96be420da50e7179d7e28ffd82a01`. La conciliación completa de las demás pestañas IA sigue abierta.


## Checkpoint Q202.83 — Smart Turn quality preregistered and synced (2026-11-03T13:20:36Z)

The public Smart Turn v3.2 Spanish-subset quality screen is preregistered and read back from `Accionables!D61/I61/J61/K61/M61/N61`. Dataset revision, license, hashes, CPU-only runtime, threshold, metrics, bootstrap and decision gate are recorded. No dataset download or quality inference has started. This is one AI action item; it does not close the cross-tab audit. Next: fresh resource preflight, serial HDD download only if thresholds pass, then inspect schema and preregister/hash/sync the exact inference harness before CPU inference. Keep reconciling all named AI tabs against local receipts and fingerprints.


## Checkpoint Q202.84 — Smart Turn dataset downloaded and verified (2026-11-03T13:25:26Z)

The ten pinned official Parquet shards (4,837,751,629 bytes) downloaded serially to HDD extra; each passed the preregistered byte-size and LFS SHA-256 checks. Manifest SHA-256 `b637f2bf9b5b9ed20ac762bd799df5b60b505202704cb432507369354026ef18`; receipt `profiles/smart-turn-v3.2-cpu/receipts/quality-dataset-download-20261103.json` SHA-256 `ee5a3bc533b7668de66128d85f54fabb749fd33ab65e9d6129814b5683bd0d9f`. No inference, GPU or service interaction occurred. Next: install the pinned PyArrow dependency in the isolated venv with cache/temp on HDD; inspect schema and exact Spanish subgroup counts, then preregister/hash/sync the quality runner before CPU inference. This does not close the broad AI-tab audit.

## Checkpoint Q202.85 — Smart Turn Spanish sample gate passed (2026-11-03T13:27Z)

A metadata-only scan of all 31,527 pinned rows (no audio decoding or inference) found Spanish N=1,783, including 496 natural and 1,287 synthetic. The registered natural sample-size gate of 100 is met; all natural rows have `midfiller`/`endfiller` null. PyArrow 21.0.0 is isolated in the test venv. Sheet Accionables row61 reflects the counts and pending quality status with readback. Before inference, implement the exact CPU runner, register its hash, and sync/read it back; then run only if fresh preflight passes. Other AI tabs still require the full row/fingerprint reconciliation.

## Checkpoint Q202.86 — Smart Turn quality runner registered/readback (2026-11-03T13:31:59Z)

Exact CPU-only runner is pinned in amendment A01 (runner SHA `baecfce9fb240e44179fd87b9a6acbbf4d098ad53167317a7e5362176570d56f`; amendment SHA `514b61fb90690d713126678904ff26a96f748c781781bd93f0038d46b59354a4`) and synced/read back in Accionables row61. The test covers all 1,783 Spanish rows (496 natural, 1,287 synthetic) and uses threshold 0.5, endpoint_bool, natural/synthetic and available filler strata, confusion/accuracy/precision/recall/F1/FPR/FNR plus 1,000 row-wise bootstrap 95% intervals. Screen gate is unchanged and only advances to a consented es_AR holdout. Sheet readback receipt `profiles/smart-turn-v3.2-cpu/receipts/sheet-quality-runner-readback-20261103.json` SHA `b1fb90b699de95d06f1e35904bdbdad514ae926dacfac58180cdc30149f800d5`. No inference has started. Next: validate hash/syntax/readback and fresh CPU/RAM/HDD gates; execute only if all pass. Broad AI-tab row/fingerprint reconciliation remains open.

## Checkpoint Q202.87 — Smart Turn runner amended and resynced (2026-11-03T13:33:35Z)

Before inference, A01 was extended with a metadata-only gate verifying all Spanish IDs are present/unique, labels non-null, and exact counts match the prereg scan; this prevents opening an ONNX session if input integrity changed. Revised runner SHA `8651fbc0c921042ba9fb5e7cb57c6da0680ff0e32d43e9c8958f8bac53e451ab`, amendment SHA `264823718636f805a1ac09b946e9d7553c0e884d8ca48e877b83c93a459722c0`; Sheet Accionables row61 readback PASS, receipt SHA `07567efd6e42c6ece248ab6b51cc9c61639fc24e4f5162f67f967e1a0393d375`. Previous readback is preserved as superseded v1. No model inference has started. Next: run static hash/syntax guard, fresh CPU/RAM/HDD preflight, then execute the single preregistered CPU quality screen if all gates pass. Global AI-tab reconciliation remains open.

## Checkpoint Q202.88 — Smart Turn Spanish quality screen complete (2026-11-03T13:35:51Z)

All 1,783 pinned Spanish rows completed on CPU with unique IDs and no errors. Natural n=496: F1=0.8625, FPR=0.2240, row-wise bootstrap 95% FPR CI=0.1727–0.2762; preregistered FPR upper-bound gate≤0.05 failed. Synthetic n=1,287: F1=0.9192, FPR=0.0967. Do not advance to es_AR holdout from this screen; dataset is not es_AR and no integration/adoption claim. Raw JSON SHA `f7d957a58c586a3a1ba7f48464ffe592596b522fb433d1fadf733c397267addd`; local receipt SHA `32ee485379f47dd87f52059678d9dfe091b09c61d1688a3dcd353978fdd6d2f3`. Google Sheet results sync/readback is next. This closes only Smart Turn’s public Spanish screen; all-AI-tab reconciliation remains open.


## Checkpoint Q202.89 — Smart Turn quality result synced and read back (2026-11-03T13:40:55Z)

The quality screen is now recorded separately from the earlier CPU feasibility smoke. `Resultados!A476:AH476` contains the 34-field result; `Accionables!D61/I61/N61`, `Inventario de modelos!C73/J73:K73/N73:O73/R73`, and `Modelos locales por peso!J109/T109:U109/X109/Z109` were read back. Format check confirms the new Results row matches row 475 (Arial 10, WRAP, TOP); row 475 remains intact. Natural Spanish n=496 F1=.8625, FPR=.2240 and upper row-wise bootstrap 95% CI=.2762, failing the preregistered ≤.05 FPR gate. Do not advance to es_AR holdout or adoption from this screen; Spanish subset is not verified Argentine Spanish. Q172/P/D are not applicable. Readback receipt: `profiles/smart-turn-v3.2-cpu/receipts/sheet-quality-result-readback-20261103T1340Z.json`.

Global cross-tab IA reconciliation remains open; this closes only the Smart Turn screen. Next audit the candidate ledger across `IA local`, `Evaluaciones LlamaCode`, `Accionables`, `Resultados`, `Inventario de modelos`, `Modelos locales por peso`, `Sin evaluar`, `Enlaces revisados`, `Recursos`, and `Perfiles de LlamaCode`; classify each AI item against local receipts/fingerprints before selecting another runnable test. Do not infer a benchmark from inventory-only rows. Preserve ASTRA, SOL, PeritoSoft assets, and historical cohorts.


## Q204.01 — argv amendment Sheet readback PASS (2026-11-03T13:48:46Z)

The connector read back all 14 intended cells exactly: `Resultados!E471`, `R471`, `S471`, `AF471`; `Accionables!D73`, `I73`, `N73`; `IA local!I122`, `L122`; `Enlaces revisados!G734`, `J734`; and `Sin evaluar!H734`, `K734`, `Q734`. Complete server/client argv and pinned hashes are present; status remains preregistered/not started. No formats, formulas, weights, or neighboring rows were changed. No download, inference, or GPU use occurred. Readback receipt: `profiles/kvark-sparkle-1.0/receipts/sheet-sync-q20401-argv-readback-20261103T1348Z.json`, SHA-256 `7f4d8283d071462e0047ee42708dfcf746856a232bd066cc5a286a050082a393`.

Next: continue the cross-tab AI reconciliation against local IDs/fingerprints; a fresh server/GPU1/RAM/PSI/HDD/helper preflight is still required before the Q204 download.


## Q204.02 — fresh preflight PASS to download only (2026-11-03T13:54:11Z)

Read-only preflight found no inference servers, candidate test workers, checked-port listeners, or CUDA compute apps. PNY GPU1 (UUID `GPU-5b9f385f-6a8e-b802-f69c-e62a71c91049`, PCI `0000:03:00.0`) had 108 MiB used, 29–30 °C, and no compute process; utilization 16–17% is retained as a covariate. ASUS GPU0 remains excluded from Q204; its quarantine service is active and boot log records 1636/1636 frames held with zero failures. P2P read/write both return OK; `gpu_unlock` loaded and kernel logs report both cards unlocked. The enabled helper oneshot has current-boot `Result=success` and its latest boot record is green. Available RAM was 102.4 GiB, memory PSI avg10 0%, and sustained swap-in/out was zero in the last two vmstat samples; swap remains 7.46 GiB used. HDD extra has 257,960,407,040 bytes free; `/` has 1,921,355,776 bytes free, so download temp/cache must remain on HDD. Control, runtime and runner hashes match preregistration; candidate path is absent. No download, inference, server or GPU allocation was started.

Preflight receipt: `profiles/kvark-sparkle-1.0/receipts/q20402-fresh-preflight.json`, SHA-256 `5d020e2d9abdccd1915c56335973226293e10a9c2d3ab2ca38f5009a15d2a97a`. Next: sync/read back this state, reread repo instructions/lock immediately before the authorized download, then fetch only the pinned text GGUF to HDD and verify size/hash.


## Q204.03 — preflight Sheet readback PASS (2026-11-03T13:59:09Z)

The connector read back all 15 intended cells exactly across Results, Accionables, IA local, Enlaces revisados, and Sin evaluar. Receipt `artifacts/evaluacion-modelos-llamacode/Q-20261103-VF-RESUME-202/profiles/kvark-sparkle-1.0/receipts/sheet-sync-q20402-preflight-readback-20261103T135909Z.json`, SHA-256 `18c0739c5f36112bf5b03395bfc2182998924fb6e5f2faf8814e4a39034db232`. No formulas or formats were changed and no inference/download/GPU action occurred. The broad reconciliation across AI tabs remains open. Next is a fresh live resource gate immediately before the pinned Q204 GGUF download.


## Q204.05 — fresh preflight synced/readback PASS (2026-11-03T14:02:14Z)

The connector read back all 15 intended Q204.04 cells exactly across Results, Accionables, IA local, Enlaces revisados, and Sin evaluar. Receipt `artifacts/evaluacion-modelos-llamacode/Q-20261103-VF-RESUME-202/profiles/kvark-sparkle-1.0/receipts/sheet-sync-q20404-preflight-readback-20261103T140214Z.json`, SHA-256 `d025dffc0f687c9653d57deafeb41545c113bb9db53b37705112761fa81640fd`; source preflight receipt SHA-256 `f0aa3657757488720d425c9895439704116a238f69b43c8a143a08863bf1e4a0`. No formulas or formats changed. No download, inference, server launch, GPU allocation, or process stop occurred.

Next: immediately reread `AGENTS.md`, `README.md`, `WORK_QUEUE.md`, and `WORK_QUEUE.lock`; verify lock ownership and repeat the resource gate before downloading only the pinned text GGUF directly to HDD extra. Global AI-tab reconciliation remains open.


## Q204.06 — pinned Hub file dry-run (2026-11-03T14:04:42Z)

The initial CLI dry-run failed before transfer because this `hf download` version disallows `--local-dir` together with `--cache-dir`; no model bytes were downloaded. The corrected dry-run uses only `--local-dir`, with `TMPDIR`, `HF_HOME`, `HF_HUB_CACHE`, and `HF_XET_CACHE` redirected to HDD extra. It resolved the exact pinned file at revision `1305d0de60384957d526f8954e06fefb6dad9aa6`, returning size 16.8G. The output warns that the public request is unauthenticated; no token was used. Expected exact size is 16,810,715,744 bytes and SHA-256 `a6b6a6dfe52531a1dc6b224b788d5b4599e601ee82873fdb16893b4abba98c89`. Receipt `artifacts/evaluacion-modelos-llamacode/Q-20261103-VF-RESUME-202/profiles/kvark-sparkle-1.0/receipts/q20406-hf-dry-run.json`, SHA-256 `ba420bbd253963effb461740b0745088fe01c9eea2d96ea79d2e4d13021b47d4`. No inference server, model load, benchmark, or GPU allocation has started.

Next: reread root instructions and lock, repeat the live resource gate, then download only this GGUF to HDD extra and verify exact bytes/SHA before any inference.

## Q204.07 — descarga verificada; test pendiente (registrada 2026-11-03T14:28:01Z)

El GGUF fijado `Kvark-Sparkle-1.0-27B-Q4_K_M.gguf` ahora está presente en HDD extra: 16.810.715.744 bytes, SHA-256 esperado y observado `a6b6a6dfe52531a1dc6b224b788d5b4599e601ee82873fdb16893b4abba98c89`. Recibo `profiles/kvark-sparkle-1.0/receipts/q20407-download-complete.json`. Esto solo verifica el artefacto; no hay Q173, Q172, inferencia, benchmark ni métrica local. Falta sincronizar/readback la ficha del modelo en Inventario de modelos y Modelos locales por peso, actualizar el estado de las pestañas de Q204 y hacer preflight vivo antes de GPU1. La conciliación transversal sigue abierta.


## Checkpoint Q204.09 — preflight y gate de salida (2026-11-03T15:28Z)

Se verificó en vivo el lock del objetivo, las pestañas Q204 y el host. No hay inference server ni proceso CUDA de prueba; PNY GPU1 está sin compute (PMon sólo Xorg gráfico). RAM disponible 102.8 GiB, PSI memoria/CPU 0%, I/O 0.01%, helper/quarantine/P2P/gpu_unlock PASS. El gate actual de Q204 falla porque los paths de raw output están bajo C (1.89 GB libres, mínimo 10 GiB); D tiene 80.59 GB libres. Recibo `profiles/kvark-sparkle-1.0/receipts/q20409-fresh-preflight.json` SHA `7679d175a8f2017143af45a3f115bd00342a3c3ef8d1926178a7b3f23dbb80b2`. No hubo inferencia, benchmark ni parada de proceso. Próximo: enmendar y sincronizar rutas raw/temp a D, repetir preflight fresco y ejecutar Q173 sólo si pasa.


## Q204.10 — ruta de salida previa a benchmark

Se registró una enmienda que redirige resultados/progreso/logs temporales de Q204 a D NVMe porque C no pasa el gate de 10 GiB. No cambian las métricas ni el plan comparativo; Q173 aún no comenzó. Enmienda `artifacts/evaluacion-modelos-llamacode/Q-20261103-VF-RESUME-202/profiles/kvark-sparkle-1.0/receipts/q20410-raw-output-path-amendment.json` SHA-256 `af03d59082ce9a796af4104cec6c22253bd1574e0ecca1c24ecdfafdb3d5171c`. Sigue pendiente sync/readback, preflight fresco y luego Q173 si libre. El resto del backlog de pestañas IA sigue abierto.


## Q204.10 — enmienda Sheet verificada (2026-11-03T15:33:23Z)

Readback PASS en las pestañas enlazadas para el raw-output amendment; las métricas de modelo siguen N/D. Recibo `artifacts/evaluacion-modelos-llamacode/Q-20261103-VF-RESUME-202/profiles/kvark-sparkle-1.0/receipts/sheet-sync-q20410-amendment-readback.json` SHA-256 `3a0082176ba469482f80584f6fbb146feb56d4c3007fab9e5dcb6e0d02a6a5c0`. Sigue pendiente Q204.11 fresh preflight y después Q173 si los gates pasan.


## Q204.12 — primer punto Q173 del control (2026-11-03T19:42:14Z)

Se completó el A-control exact 8K n=3 de Q204, con P=1142.353±1.750 y D=32.051±0.274 tok/s, TTFR=7.171±0.011 s; usage del servidor 8192 en las tres y salida128×3. No es Q172 ni score general. Advertencia: el proceso fue configurado con PNY GPU1, pero no se capturó telemetría durante ejecución; el log indica un warning de placement antes de cargar el modelo. Por tanto la velocidad es un punto descriptivo y la atribución GPU queda por confirmar en los bloques B/A-repeat instrumentados. Receipt `artifacts/evaluacion-modelos-llamacode/Q-20261103-VF-RESUME-202/profiles/kvark-sparkle-1.0/receipts/q20412-a-control-8k-execution.json` SHA 9aeb7077a37826e67628e51496c8464ceb263b720928f540319b0b7ade8c19d2. El ladder Q204 sigue abierto y no se mezclan estos datos con el perfil Q190 ni con q8_0.


## Q204.12 — resultado sincronizado (2026-11-03T19:44:57Z)

Q204.12 A-control exact8K n3: P=1142.353±1.750, D=32.051±0.274, TTFR=7.171±0.011s, usage exacto y output128. El Sheet quedó actualizado y leído de vuelta en los rangos enlazados; no se mezclaron cohortes. Q172 y KVARK B siguen pendientes; falta telemetría de GPU durante los requests y el server emitió warning de placement. Readback receipt `artifacts/evaluacion-modelos-llamacode/Q-20261103-VF-RESUME-202/profiles/kvark-sparkle-1.0/receipts/sheet-sync-q20412-result-readback.json` SHA `cc7ea4bdd1437fc1d288736760a51208edddde26813f45236e8739b76f26a37a`. Reconciliación de todas las pestañas AI sigue abierta.


## Q204.13 — verificación de placement para el siguiente bloque

Se preregistró monitor pmon+dmon en B 8K porque Q204.12 carecía de telemetría bajo requests. Solo GPU1 queda visible al servidor; ASUS sigue excluida. La comparación requiere ver el PID propio como compute con FB>0; si no, los TPS no se usarán para decisión de GPU. Receipt `artifacts/evaluacion-modelos-llamacode/Q-20261103-VF-RESUME-202/profiles/kvark-sparkle-1.0/receipts/q20413-telemetry-amendment.json` SHA `c22c2bcdeedd1b461c0c11ae52e0121917b802576d45a8f279e22f57d18527a7`. El resultado parcial Q204.12 ya fue readback; el cruce de otras filas/pestañas AI sigue pendiente.



Q204.17 prereg amendment ready for synchronization: runner SHA-256 `77f8dc4404c7e9e874fdfabeaa7e8c9b94a323ae7509d038ae88ce8cb66b1405`; receipt `profiles/kvark-sparkle-1.0/receipts/q20417-runner-amendment.json`. The updated supervisor streams artifact hashes, validates exact 8192/128 usage for all three requests, captures line-buffered PMon/DMon for 1800 seconds and gates attribution on the owned PID at GPU1 plus ≥512 MiB framebuffer delta. CPU-only fixtures passed; no inference/GPU. Sync/readback and a fresh launch preflight remain necessary before B.



Q204.18 final preflight is PASS and was synchronized/read back across linked AI tabs. No model inference occurred. Receipt `profiles/kvark-sparkle-1.0/receipts/q20418-fresh-launch-preflight.json` SHA-256 `0ffa9406f2346b5c0a01a6c5adfc985d2aa50de06858a359dc1ea092a9840dd1`; Sheet readback `profiles/kvark-sparkle-1.0/receipts/sheet-sync-q20418-preflight-readback.json` SHA-256 `be454a9ddd76d3aaf1e496e9d995ee8d369c637832c5b03219688c9d8973cdba`. Runner may now start candidate B only after its own inline process/resource/hash gates pass; the three output requests remain pending.

## Checkpoint 2026-11-17 — objetivo vivo y corrección Q190

- Se adopta el objetivo actualizado del usuario: revisión semántica completa de las pestañas IA al inicio si falta checkpoint confiable, cuando se agregue material, aparezca una pestaña, cada cinco pruebas y aproximadamente cada día; entre esos hitos, sólo cambios/filas pertinentes. Mantener worker aislado para pruebas riesgosas, actualizar Sheet y recibos después de cada prueba y respetar el lock de campaña.
- Lock vigente de esta campaña: token `d9029f6b-c649-4291-b0be-f14d77dc737e`, tarea `Q-20261103-VF-RESUME-202`.
- Refresco de metadatos del Sheet `Listado` el 2026-11-17: 22 pestañas totales. Bounds IA actuales: Panel 1000×26; Sin evaluar 1500×19; Recursos 350×18; IA local 350×15; Evaluaciones LlamaCode 1000×26; Enlaces revisados 1200×18; Inventario de modelos 78×18; Accionables 138×14; Resultados 547×34; Modelos locales por peso 129×29; Vista agrupada por tipo 1000×37; Perfiles de LlamaCode 110×18; Agentes largo plazo 94×16. No apareció una pestaña nueva respecto del metadato previo. Esto es un snapshot estructural, no una auditoría semántica completa.
- La conciliación semántica transversal sigue **ABIERTA**; el último estado local aún la declara abierta desde Q204 y no hay un checkpoint reciente que demuestre una revisión completa diaria. Próximo paso exacto: reconciliar filas/IDs nuevos o modificados en todas las pestañas IA contra el último checkpoint, registrar fingerprints y sólo entonces escoger el siguiente experimento; no repetir filas ya conciliadas.
- Corrección de evidencia Q190: el registro decía que `medium` vs `effort=High` hacía incompatibles las comparaciones. Las fuentes primarias confirman que DSX acepta `medium` como alias `high`, y Maya asigna `medium` y `high` al presupuesto 75. Se corrigieron `RESULTS.md` y `Resultados!U14/W14`, `Modelos locales por peso!M81/X81/Y81/AA81`; readback exacto guardado en `profiles/deepseek-maya-xs-vs-dsx-q190/receipts/q190-reasoning-level-reconciliation.json` (SHA-256 `d220cf0e24b8375d01f3b6e96f503d5b3e7d7d1e18c3aa45fc5d12afab98f7ae`). Los scores/semillas no cambiaron; DSX 86,33 vs Maya 84,67, diferencia 1,67 con n=3, sin ganador general. TC-92 sigue fallando en ambos 3/3. No hubo nueva inferencia ni GPU.
- Revisión solicitada de los cuatro niveles, basada en filas vivas 2, 9, 29, 70, 76, 81 y 83 y recibos locales. Se asignaron provisionalmente las etiquetas de filtro `ASTRA` a DSX T16/Maya DS4, `SOL` a Flash-Next NInfer-all fc12, `TERRA` a Ternary Bonsai NInfer v3; la fila LUNA conserva la restricción sin tools. Se añadió `Accionables!139` y se leyó de vuelta junto con Modelos locales por peso B70/B76/B81/B83; recibo `profiles/four-role-specialization-review/receipts/sheet-readback.json` SHA-256 `c40febd25353714c21ba59b55550b039b38f384511653b123cf1abfd5a36f7de`. No se ejecutó prueba ni se usó GPU. El empate funcional ASTRA permanece abierto: Maya tiene mayor Q172 reciente (89,33 n=3), DSX mayor LHA (79,2 vs76); los perfiles/cohortes difieren. SOL/TERRA/LUNA también conservan sus gates de seguridad Q172 fallidos. La conciliación semántica de todas las pestañas IA sigue ABIERTA.

## Revisión incremental — nuevas filas de IA local, 2026-11-17

Se procesaron secuencialmente las primeras dos entradas nuevas visibles en `IA local` (filas 147–148); las filas siguientes siguen pendientes. No hubo descarga, compilación, inferencia ni uso de GPU.

### Fila 147 — Delta Inference Engine v0.94

- **Estado: BLOQUEADO para la sesión Linux actual.** El [README del proyecto](https://github.com/musicurgy/delta-inference-engine) describe un port nativo de Windows de Xolotl/Strata. La versión 0.94 publica 41,7 tok/s en una RTX 3090 con 192 GB RAM; 34 tok/s a 128 GB corresponde a la versión 0.93. La segunda GPU trabaja como helper de expertos y el mismo README aclara que no divide el modelo; para dos GPUs grandes remite a Project Maya. Los resultados son del autor y no incluyen Q172/LHA comparables con la ficha ASTRA local.
- El modelo indicado requiere entre 233 y 395 GB según la cuantización. No se halló artefacto ni recibo local de Delta. No se descargó porque el entorno actual es Linux, no hay distribución Linux validada del proyecto v0.94, y el perfil no usa las dos 3090 como TP.
- Condición de reanudación: release/build Linux reproducible (o sesión nativa Windows disponible) y plan de comparación verificable contra Maya con Q172 y prueba agentiva; confirmar espacio antes de cualquier descarga grande. No marcar como SUPERADO: faltan datos compatibles.
- Sheet: `IA local!I147/L147` y `Accionables!D114:N114`, actualización con readback exacto; recibo local en `profiles/delta-inference-engine-v094/receipts/decision.json`.

### Fila 148 — Qwen3.8-27B Unsloth Dynamic v3.1 GGUF

- La [ficha primaria de Unsloth en Hugging Face](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF) publica una mejora de 5–10% en sus suites frente a otras cuantizaciones. Es una afirmación del proveedor y no reemplaza la suite local.
- La evaluación local corresponde al mismo GGUF SHA-256 `2a5f3565f39cf885103da591182c1266da64745737b42b452fd3e675369f1211`: Q208 completó Q173 a 8K–261888, P/D medio 721,57/22,01 tok/s. Q208 seed42 quedó incompleto y falló TC-92; Q223 con reasoning-on volvió a fallar TC-92; Q224 reprodujo el fallo en seed43 (0/2 en el caso focal). No existe puntaje global Q172 válido y no se debe iniciar LHA ni recomendar herramientas multi-tenant.
- **Estado: BLOQUEADO por fallo de aislamiento en TC-92**, no por falta de potencia ni por falta de métricas de velocidad. No repetir Q172/Q189 mientras no exista una corrección concreta del filtrado/autorización por tenant; después, preregistrar una suite completa con seeds y fingerprint fijados.
- Sheets: el resultado detallado ya consta en `Resultados` Q208/Q223/Q224; la fila nueva `IA local!I148/L148` quedó conciliada con las repeticiones y la condición de reanudación. Recibos locales Q223 `RESULTS.md` SHA-256 `8d03b05f0e7508dcc7bfdf37756b470fa2e41a71ea2eb0c57134de12e8d29420`, Q224 `RESULTS.md` SHA-256 `fc4fd1bb9fdb94e644737f0853805ab1e6995215634669c81456886c24161d29`.

### Fila 149 — KQuant/MLX y Nace GGUF relacionado

- La página original [Qwen3.8-27B-MLX](https://huggingface.co/nace-ai/Qwen3.8-27B-MLX) confirma un pack MLX y Kapitsa para Apple Silicon; Kapitsa declara Apple Silicon only, no Linux/Windows.
- Hallazgo nuevo: el GGUF hermano [nace-ai/Qwen3.8-27B-GGUF](https://huggingface.co/nace-ai/Qwen3.8-27B-GGUF) ya está publicado y documenta llama.cpp en Linux, tamaño 17,65 GB más `mmproj` opcional 0,93 GB. Su propio benchmark pareado con Unsloth UD-Q4_K_XL de tamaño similar describe MMLU/ARC/Winogrande como “about the same” (intervalos 95% incluyen cero); la ligera diferencia de KL contra BF16 no demuestra superioridad en tareas ni velocidad.
- **Estado: SIN PRUEBA APLICABLE para la decisión actual ASTRA/SOL/TERRA/LUNA.** No hay una afirmación local de TPS mejor ni un cambio estadísticamente claro en tareas que justifique descargarlo; además, las pruebas Q172/LHA con tools para Qwen3.8-27B siguen condicionadas por TC-92 en el perfil Unsloth actual. No se descargó ni usó GPU. Reconsiderar sólo si aparece una ventaja en una tarea local concreta o se prioriza comparar cuantizaciones.
- Sheet `IA local!C149:E149,H149:L149` actualizado con el nuevo GGUF y readback exacto; `profiles/nace-qwen38-27b-gguf-review/DECISION.md` y `receipts/sheet-readback.json` conservan la evaluación.

**Checkpoint incremental:** filas 147–149 conciliadas; siguiente material: fila 150, anécdota comparando ISTA GSQ-RCO IQ3_S y Unsloth IQ4_XS. La auditoría semántica transversal continúa abierta. Último inventario estructural completo: 2026-11-17, 22 pestañas; no se repitió la lectura total.


### Fila 150 — ISTA GSQ-RCO IQ3_S vs Unsloth IQ4_XS

- **Estado de la afirmación: REVISADO · SIN PRUEBA REPRODUCIBLE.** El autor original declara que no hizo benchmark; su hardware es distinto y los comentarios contradicen la conclusión.
- Evidencia local IQ3_S: Q20/S23 aprobó 3/24 tareas de coding; Q216 Q173 8K×3 registró P17,548/D3,765 con gran variación de caché; Q247 Speedy v0.4.10 screen P2491,15/D34,37 falló el gate decode ≥90 y no habilitó ladder/Q172. Q243 fue smoke solamente. No mezclar runtimes ni presentar estos resultados como comparación directa.
- No se hallaron los pesos exactos UD-IQ4_XS en la ruta histórica, sólo marcadores `.gguf.done`; no existe A/B local comparable. Se deja el origen y la condición de reapertura en `profiles/ista-gsqrco-iq3s-vs-unsloth-iq4xs-review/DECISION.md`.
- Sheet `IA local!E150:I150` y `L150` fue actualizado y leído de vuelta exactamente; recibo `profiles/ista-gsqrco-iq3s-vs-unsloth-iq4xs-review/receipts/sheet-row150-readback.json`. No se ejecutó prueba, descarga, build ni GPU.

**Checkpoint incremental:** filas 147–150 conciliadas; siguiente material: `IA local!151`, tandem.cpp (ewhacc). La revisión semántica transversal sigue abierta.


### Fila 151 — tandem.cpp v0.3.0

- **Estado: ACCIONABLE.** Fuente primaria actual publica v0.3.0 (2026-11-16), patch sobre llama.cpp f5222f25c; sus cifras Qwen3.8 IQ3_S+MTP (34,3 tok/s en 5070 Ti 16GB/32GB; 97,3/96,1 en RTX 4090/64GB frente a Strata 103,6/98,1) son del autor y no transferibles al host 2×3090. Declara objetivo single-user; falta validar placement real en 1×/2× 3090.
- Q210 local compiló commit previo 0ba3b04 (sin inferencia de rendimiento); Q212 smoke respondió PASS con Qwen3.8-27B UD-Q4_K_XL atribuido a ambas GPUs, pero no midió P/D/Q172; Q211 IQ3_S+MTP exacto está descargado y SHA-verified.
- Se identificó una prueba que puede cambiar SOL/runtime: build aislado v0.3.0 y Q173 8K×3 matched frente al control llama.cpp, con GPU attribution; continuar ladder hasta 261888 y calidad sólo si pasa el screen. No iniciar benchmark hasta preregistrar commit/args, fijar comparabilidad y verificar recursos.
- Sheet `IA local!E151:I151,L151` actualizado y leído de vuelta; receipt `profiles/tandem-cpp-v030-review/receipts/sheet-row151-readback.json`. No hubo descarga/build/inferencia/GPU en esta revisión.

**Checkpoint incremental:** filas 147–151 conciliadas; siguiente material: `IA local!152`. La revisión semántica transversal sigue abierta.

### Fila 152 — Kuru, beta privada sin artefacto público

- **Estado: BLOQUEADO.** La fila atribuye a `@rifaldyelninoru` un anuncio de Threads del 2026-11-14 con 332 tok/s en RX 7900 XTX y 64 GB de RAM, pero no aporta permalink. Las búsquedas públicas del 2026-11-17 (`site:threads.net "rifaldyelninoru" Kuru inference 332 tok/s` y `"Kuru" "332 tok/s" Qwen3.6-35B-A3B`) no localizaron fuente primaria, repositorio ni release. El alcance de hardware del claim tampoco valida CUDA/SM86 o las RTX 3090 locales.
- No se encontró modelo, runtime, benchmark ni recibo Kuru en el árbol local de evaluaciones. No hay prueba reproducible que ejecutar; no se instaló ni aceptó binario por DM, no se descargó, compiló ni usó GPU.
- **Reapertura:** permalink primario verificable, release público con licencia y hash, soporte confirmado para SM86/CUDA y protocolo completo que permita A/B reproducible del mismo Qwen3.6-35B-A3B (quant, GPU/RAM, contexto, batch, MTP, tokens y métrica de calidad).
- Sheet `IA local!I152/L152` actualizado y leído de vuelta; `IA local!A153:O153` está vacía. Decisión local `profiles/kuru-private-beta-review/DECISION.md` SHA-256 `ec769b8879dc49782127d31d2b422916e9ee115cd52ed200c10b0f31cba6b79f`; readback `profiles/kuru-private-beta-review/receipts/sheet-row152-readback.json` SHA-256 `a8408ddeaa542661aff37838a6374c462d5a7386f280b9f617f3537600fcc6da`.

**Checkpoint incremental:** IA local filas 147–152 revisadas; fila 153 vacía. La conciliación semántica de las demás pestañas IA sigue abierta; revisar filas/IDs modificados desde el último checkpoint y no repetir resultados ya cerrados.


## Revisión incremental 2026-11-17 (cierre Q253 y adopción del objetivo vivo)

- Metadatos del Sheet verificados 2026-11-17T17:13:45Z: 22 pestañas, las mismas 13 pestañas IA y los mismos sheet IDs; no apareció una pestaña nueva.
- Persistida la lectura de grids acotados observada a las 16:50:30Z en `artifacts/evaluacion-modelos-llamacode/Q-20261103-VF-RESUME-202/receipts/live-sheet-inventory-reconciliation-20261117T1650Z.json`. Las filas 147–152 de `IA local` están conciliadas; 153 sigue vacía. Resultados alcanza 547, Accionables 139 y Agentes largo plazo 94.
- Los tails nuevos de `Enlaces revisados` (970–998) y `Recursos` (166–171) corresponden a gaming/firmware, sin prueba aplicable a esta campaña de IA.
- No se generó un nuevo fingerprint completo: el baseline FNV anterior no coincide con la comprobación de fila1 y no debe usarse como delta fiable. Para continuar, usar IDs estables y filas posteriores a los límites registrados; reconstruir fingerprints sólo en la próxima revisión completa programada o ante material nuevo.
- Sin build, descarga, benchmark, inferencia ni GPU en esta activación. Próximo candidato: evaluar Qwen3.8 IQ3_S+MTP con tandem.cpp v0.3.0 sólo tras diseñar un control Q173 compatible; Q216 no es compatible (MTP-off/cap24).

## Corrección de roles ASTRA / SOL / TERRA / LUNA — 2026-11-17T17:36:43Z

La reconciliación de filas vivas y recibos Q190/Q206/Q222/Q253 cambió sólo la asignación LUNA: `Modelos locales por peso!B14` ahora apunta a Qwen3.6-35B-A3B NInfer-all v3 MTP3 Q190; `B2:C2` deja MTP4 en evaluación sin rol. MTP3 Q173 promedia P5155.87/D230.02; Q172=74/100 n=3; LHA-1=100/100 n=5. Q172 TC-91 falla, así que no habilita tools. MTP4 Q253 promedia P4600.61/D214.04 y queda 6.95% debajo de MTP3 en decode; su Q172=79 es n=1 y falla TC-82/91. Lectura de vuelta exacta en `profiles/four-role-specialization-review/receipts/sheet-readback-20261117T1736Z.json`. ASTRA Maya/DSX, SOL Flash-Next y TERRA Ternary Bonsai permanecen como candidatos provisionales con los gates indicados en `Accionables!139`; no se ejecutó inferencia ni GPU. Próximo test de desempate ASTRA: Q172 DSX T16, seeds42–44, configuración emparejada con Maya DS4.
- Addendum 2026-11-17T17:36:43Z: `Inventario de modelos!R76` actualizado y verificado; MTP4 se marca explícitamente sin rol LUNA, y el inventario enlaza al mismo target `.ninfer` usado por MTP3 Q190. Receipt actualizado `profiles/four-role-specialization-review/receipts/sheet-readback-20261117T1736Z.json`.


## Addendum comparativo ASTRA — 2026-11-17T17:55:40Z

La nota de 17:36 decía que faltaba emparejar Q172 de DSX con Maya DS4; Q206 ya contiene el perfil Maya DS4 `DS4_SPLIT=39,1` completo. Reconciliación: DSX Q190 89/84/86 (86,33) vs Maya DS4 Q206 88/89/91 (89,33), Tool-Eval 2.8.0, contexto 131072, seeds 42–44, reasoning medium/budget 75; deltas Maya−DSX −1/+5/+5, media +3, una diferencia descriptiva con n=3; los 5 puntos sólo pertenecen al gate de borrado junto con menor velocidad, no a una prueba estadística. La Maya original Q190 (84,67) es otro perfil. Ambos perfiles fallan TC-92 en 3/3 semillas. Se corrigió `Accionables!H139:I139/K139/N139` y `Modelos locales por peso!AA81/AA83`; readback íntegro en `profiles/four-role-specialization-review/receipts/sheet-readback-20261117T1755Z.json`. No hace falta repetir Q172 ni se declara dominancia. Roles provisionales: ASTRA Maya DS4 para priorizar Q172, DSX como alternativa decode/LHA; SOL Flash-Next IQ2_XS NInfer-all v3; TERRA Ternary Bonsai NInfer v3 para output-heavy; LUNA Qwen3.6-35B-A3B MTP3 restringido sin tools. Los perfiles Qwen IQ3_S, KVARK y DFlash incompletos siguen sin asignación. Sin prueba, build, descarga ni GPU. Lock `d9029f6b-c649-4291-b0be-f14d77dc737e`.


## Corrección de alineación de filas de la hoja viva — 2026-11-17T18:09:51Z

Una lectura por rangos de celdas y un cambio posterior de orden de la hoja no coincidían en los índices de fila. Se verificaron los modelos por nombre con búsqueda de filas y se corrigió la asociación: `B80` DSX=`ASTRA · ALTERNATIVA`, `B114` Maya DS4=`ASTRA · PRINCIPAL`; `AA80/AA114` contienen la comparación ASTRA; `AA81` volvió a una nota de Qwen Flash-Next sin Q172/LHA atribuibles y `AA83` a Qwen3.8-27B GGUF+mmproj/QWEN38-VISION, Q17279/100 y su propio Q173. `B8` LUNA MTP3, `B12` MTP4 sin rol, `B16` TERRA y `B69` SOL Q206. La lectura exacta quedó en `profiles/four-role-specialization-review/receipts/sheet-readback-20261117T1809Z.json`; los recibos 17:55 y 17:58 quedan marcados superseded por tener alineación de filas antigua. Se corrigió RESULTS.md para usar los índices actuales con fecha y advertencia de hoja viva. No se ejecutó benchmark/inferencia/GPU. Lock `d9029f6b-c649-4291-b0be-f14d77dc737e` conservado.
