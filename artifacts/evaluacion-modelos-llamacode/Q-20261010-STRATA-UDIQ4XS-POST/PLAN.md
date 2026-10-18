# Evaluación del post de Strata con Qwen3.8-Flash-Next UD-IQ4_XS

- **ID:** `Q-20261010-STRATA-UDIQ4XS-POST`
- **Estado:** Auditoría documental completada; no se descargó ni ejecutó modelo local. Se recuperó y verificó el post exacto y evidencia oficial posterior de Strata.
- **Registro de cola:** agregado después de las tareas pendientes existentes. Reanudado en FIFO el 2026-10-13 bajo lock `4f4789e9-a5a1-4b29-9a90-d90130bbed6b`; cierre documentado en `WORK_QUEUE.md`.
- **Objetivo:** comprobar si el resultado reportado para UD-IQ4_XS en Strata aporta una mejora práctica a los usos de LlamaCode, en especial coding/agentes y velocidad, y delimitar qué no dice sobre Computer Usage, Ingi-Charla, visión y contexto.
- **Estado productivo:** sin cambios a perfiles, sampling, HarnessSpec o defaults.

## Material recibido y alcance preliminar

El texto pegado atribuye a `u/ajax936` un post titulado “Qwen3.8-Flash-Next UD-IQ4_XS (~94GB) on RTX 5090 Laptop + 128GB RAM — Strata 0.1.41 — 52.6 tok/s, 84.8% Expert Cache Hit”. No incluye URL del post; encontrarla por título/autor al iniciar el turno. Los datos siguientes son sólo lo que afirma el material recibido, no hechos verificados:

- MSI Raider A18 HX, RTX 5090 Laptop con 24 GB, Ryzen 9 9955HX3D, 128 GB DDR5 y PCIe 5.0 x8; Windows 11.
- Qwen3.8-Flash-Next Unsloth UD-IQ4_XS (~94 GB), Strata 0.1.41 CUDA, ventana configurada a 32.768, KV INT8, caché híbrida de expertos y MTP activado; reasoning desactivado.
- Tres solicitudes con 40 tokens de prompt y 320 de salida: decode 46,2/52,6/51,1 tok/s; end-to-end 38,95/51,20/49,72 tok/s; expert-cache hit 80,2/84,8/83,7%; lecturas PCIe de expertos 12,8/9,7/10,3%.
- Configuración atribuida a 55 GiB de presupuesto de expertos residentes en RAM, con otros expertos leídos desde SSD; el autor aclara que no midió el RSS total de RAM/VRAM.
- Comenta que el test anterior de Swift IQ2_XS llegó a 87,5 tok/s, pero reconoce que es otro checkpoint/quant y no un A/B controlado. El post es texto-only. Un comentario describe cambios hechos sobre un dashboard de demostración que acabaron publicados al dashboard live; faltan prompt, permisos, historial y evidencia para atribuirlo a la quant o a calidad general.

## Candidatos y controles al llegar el turno

- **Candidato objetivo:** Unsloth Qwen3.8-Flash-Next UD-IQ4_XS bajo Strata; confirmar repositorio/revisión, shards y hashes. El peso no se presume instalado ni se descargará antes del turno/preflight.
- **Control de stack/familia:** ASTRA IQ3_S de Flash-Next bajo Strata v0.1.41, reutilizando el informe previo sólo como referencia y sin repetir sus fingerprints de calidad/velocidad.
- **Referencia de coding vigente:** SOL Qwen3.8-27B AutoRound INT4; compararlo como perfil completo si puede correrse válidamente bajo su backend disponible. No atribuir diferencias sólo a quant/modelo si runtime/hardware/template difieren.
- Antes de fijar el A/B: revisar dependencias de cola, pesos disponibles, perfil efectivo, runner y suite compatibles. Priorizar recibos ya existentes; descargar sólo si el origen, tamaño libre y utilidad incremental se confirman.

## Preguntas y pruebas previstas

1. **Fuentes primarias y números del post:** recuperar URL y recibos/config publicados; verificar Strata 0.1.41, interpretación de decode vs end-to-end, conteo de tokens, reglas de caché/MTP, almacenamiento/lecturas SSD y perfil de memoria. Contrastar con documentación/fuentes oficiales de Qwen, Unsloth y Strata. Mantener separados los resultados que el autor no midió.
2. **Coding/agentes:** screening HE0 → HE20 → BCB8 y TaskFlow ULTRA con controles locales disponibles. Aislar todos los cambios en un workspace descartable, sin acceso de publicación ni credenciales. Reusar los fingerprints existentes cuando correspondan y crear huellas nuevas sólo para diferencias justificadas. Para afirmaciones estables se requieren al menos tres corridas válidas emparejadas por perfil/seed; clasificar fallos de infraestructura por separado.
3. **Tool-use y efectos:** inspeccionar trazas, paths escritos, comandos y estado final. Si se toma el incidente del dashboard como regresión, usar una copia local aislada con verificador de cambios; no dar acceso a un dashboard vivo ni secretos.
4. **Rendimiento:** medir en el mismo equipo/runtime y con candidato/control disponibles; separar cold/warm, TTFT, prefill, decode y end-to-end con prompts y longitudes registradas; reportar mediana/dispersión, memoria RAM/VRAM, caché de expertos, lecturas PCIe/SSD y aceptación MTP. Tres requests de 40+320 tokens y cache-hit alto no equivalen a carga sostenida ni contexto largo.
5. **Contexto:** distinguir ventana configurada de tokens efectivamente procesados/recuperados. Sólo intentar 64K/128K/256K con prompts poblados y guardas de memoria del repositorio cumplidas. No repetir el smoke 262K bloqueado de IQ3_XXS como evidencia de UD-IQ4_XS.
6. **Computer Usage, Ingi-Charla y visión:** el post no aporta una prueba E2E de escritorio, audio/ASR/TTS ni imágenes. Mantener esos usos como no evaluados a menos que haya un harness, fixtures y controles adecuados; no derivar calidad de texto ni de soporte nominal de runtime.

## Criterio de decisión

El post justifica revisar la ruta híbrida de memoria, MTP y el trade-off velocidad/quant; no prueba mejora en LlamaCode. No promover un perfil por la velocidad publicada o por la anécdota aislada de dashboard. Una recomendación local exige resultados reproducibles que mantengan calidad, integridad de herramientas y estabilidad con las configuraciones completas claramente descritas. Si no se completa el A/B, registrar el bloqueo y la siguiente acción exacta sin inferir un score.

## Estado de esta actualización

La tarea llegó al turno luego de cerrar la auditoría de Mirai S y el post de quantizaciones Strata. El control local IQ3_XXS/ASTRA usó Strata 0.1.41 en dual RTX 3090 y no replica UD-IQ4_XS. El post exacto se recuperó; la ficha de Hugging Face fija un árbol de 93,7 GB, pero no hay copia local. La partición NVMe está al 95% con 105.175.375.872 bytes disponibles (sólo ~11,5 GB de margen sobre el peso), y la caché HF del sistema tiene 7,7 GB libres. El otro volumen tiene espacio pero es HDD y alteraría la ruta de lectura SSD del post. No se descargó, compiló ni usó GPU.

La decisión vigente del usuario limita la suite de tres seeds a ≤30 minutos por perfil. El informe comunitario exacto sólo midió tres solicitudes cortas, pero su modelo requiere 93,7 GB ausentes; no se hizo un screening local de calidad. Un issue comunitario oficial de Strata aportó un speed suite distinto para UD-IQ4_XS en una RTX 3090/Strata 0.1.43 (295 s), sin medición de corrección/calidad; se conserva como evidencia externa, no como resultado local ni comparador directo. Ninguna huella local de candidato se creó.



## Continuación solicitada — 2026-10-18

- **Motivo:** el usuario pidió ejecutar las pruebas pendientes. Se conserva el mismo ID histórico; la auditoría documental anterior queda intacta.
- **Runtime y modelo fijados:** Strata `v0.1.41`, revisión Unsloth `38bb39ee97821de2c9009abb7e93950eec396e66`; tres shards oficiales con tamaño y SHA-256 publicados en `docs/UNSLOTH_Q4.md` del runtime. No se cambiará runtime ni revisión durante el screen.
- **Almacenamiento:** SSD libre 83.619.123.200 bytes, menos que el GGUF (93.682.584.224 bytes); HDD libre 338.303.463.424 bytes. Si el setup confirma capacidad para shards, pack y MTP, el candidato irá en un directorio de evaluación dedicado en HDD. El HDD cambia las lecturas de expertos, así que sus velocidades serán un perfil separado y no una comparación directa con el resultado SSD del post.
- **Recursos:** una RTX 3090, GPU 0, sólo si sigue ociosa; GPU 1 queda sin reservar por actividad del host. Perfil y endpoint loopback aislados. Contexto configurado 32K, KV INT8, MTP activado según la publicación, visión apagada. No editar perfiles productivos ni HarnessSpec.
- **Límite:** se conserva el corte vigente de 30 minutos acumulados por perfil. El alcance preregistrado es instalación/hash, smoke HE0 y tres solicitudes sintéticas iguales de 40 tokens de prompt/320 de salida, sujetos al tiempo restante. HE20 → BCB8 → TaskFlow ULTRA sólo se inicia si su proyección cabe en el corte; cualquier parcial es screening, sin promoción. Afirmaciones estables requieren tres pares válidos.
- **Modalidades:** este screen no mide Computer Usage E2E, visión, Ingi-Charla/audio ni recuperación con contexto poblado; requieren suites/fixtures separados y no se inferirán del rendimiento textual.
- **Salida:** recibos bajo `receipts/continuation-20261018/`, resultados separados por modalidad en `RESULTS.md` y actualización del registro canónico. No borrar el modelo ni tocar perfiles productivos al cerrar.
