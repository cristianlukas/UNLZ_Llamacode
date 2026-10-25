# Q119 · integración OCR sidecar en Data Lab · 2026-10-25

**Estado:** Cerrada · lock `46289c40-dc45-4f14-aa9d-6680f21d7684`

## Motivo y decisión objetivo

El actionable `vf-ocr-unlimited-20261019` quedó pausado después del screen P1–P4. P4 superó seis casos sintéticos con el parser fijado y mostró una ventaja en tablas/orden espacial frente a Tesseract, pero aún falta comprobar si una salida Markdown parseada se puede consumir por la ruta existente de Data Lab.

Q119 ejecutará un smoke de integración **sólo con sidecar Markdown sintético**. No añadirá una ruta automática de OCR para PDFs, no cambia `DocumentExtractor` ni la extracción productiva, y no se presenta como validación de documentos reales. La decisión resultante será si el sidecar merece una prueba opt-in posterior; no promueve el modelo.

## Prerregistro

- Fuente exacta: texto parseado del caso sintético `form` de Q49 P4, obtenido de `unlimitedocr-p4-parser-attempt01.json`; verificar SHA-256 contra el recibo Q49 antes de usarlo.
- Fixture de entrada: Markdown de OCR temporal, derivado exclusivamente del PDF sintético P4. Contiene `Reference: FORM-8821-Z` y `Customer: LAB-CEDAR-07`; no se leen documentos del usuario.
- Recorrido: `DataLabStore::createJob` → `processJob` → `extractionPrompt` → `runExtraction` contra el servidor fake de loopback existente en `tests/test_datalab.cpp` → validación/escritura del resultado → borrado del job.
- Gate: un documento se extrae; el prompt contiene ambos identificadores y el esquema; el fake local devuelve un registro JSON exacto; Data Lab lo marca `valid`, conserva evidencia de coincidencia y el job temporal se elimina.
- Control: ruta normal existente de documentos Markdown/TXT; no fingir que se probó el PDF rasterizado dentro de `DocumentExtractor`.
- Alcance de recursos: CPU/QtTest, sin cargar pesos, inferencia real, GPU, servidor externo, red, build de la aplicación ni modificación del extractor/modelos/perfiles. El fake HTTP de prueba será loopback y sólo vivirá durante el caso QtTest.
- Luego de agregar el test, fijar el hash del fuente en `receipts/q119-preregistration.json` y leer el prerregistro de vuelta en Google Sheets antes de compilar.
- Gate de repo por cambio en test C++: `./scripts/tests-linux.sh Release`; no omitir el resultado aunque el cambio no toque código de producción.

## Preflight inicial (read-only)

- Lock Q119 reclamado por creación exclusiva. No había lock previo.
- Linux `7.0.0-38-generic`; scan de procesos y puertos de evaluación: cero servidores de inferencia, cero listeners en 8350/8000/8001/8080/1234/30000.
- `MemAvailable`≈111 GiB; swap libre≈4,4 GiB; ArtCraft presente (207 MiB reportados en GPU), se deja intacto. No se inicia una inferencia.
- Q49 conserva su venv/checkpoint aislados en Disco local; Q119 no abrirá esos pesos.

## Resultado y límites

El gate Linux Release compiló y pasó **95/95 tests**. Esa corrida no fijó `LLAMACODE_OCR_SIDECAR_FIXTURE`, así que el nuevo test tomó el fallback inline y no se usa como evidencia de procedencia Q49. Después, el `test_datalab` aislado pasó **1/1** con esa variable apuntando al sidecar P4 exacto, SHA-256 `e5b6b53eb0a14d67df5e954c1428df77c143d469ba100fd54e4accdabaafc3ae`.

El smoke demuestra que Data Lab puede ingerir texto Markdown ya producido por el sidecar Q49, enviarlo en el prompt a un fake HTTP loopback, validar la respuesta sintética y borrar el job. No demuestra OCR automático de PDF, calidad con documentos reales ni que convenga integrar el candidato en la aplicación. No se cambió código productivo ni se cargó modelo/GPU.

El pedido de revisar el detector queda respondido con alcance limitado: ASTRA DEFAULT 1M completó y el replay Q118 del rastro real no produjo falso stop pese a 51,306 GiB RSS; SOL Q34 terminó TP=2 dual-3090 sin OOM. Por tanto, el guard no detiene por RSS alto aislado en las trazas exitosas citadas. A la vez, Q116 detectó un hueco de semántica en el guard Q97/Q100: la condición PSI severa `full OR some` alternada no acumula una racha común porque los contadores son independientes. El helper compuesto de Q116 pasó 5/5, pero es candidate-only y no está integrado. Esta prueba no certifica cada presión extrema ni detecta la causa del cierre de Codex.

## Enmienda de alcance · revisión del detector de presión

El usuario recordó que ASTRA DEFAULT 1M y SOL finalizaron cargas de memoria altas sin crashes y pidió comprobar que el guard no las trate como presión fatal. Revisión read-only antes del smoke Q119:

- Q118 ya reprodujo en orden las 707 muestras reales de ASTRA 1M contra el módulo que importó AMD05. Resultado 12/12: RSS máximo 51,306 GiB, `MemAvailable` mínimo 58,698 GiB, PSI global máxima 53,61%, sin stop, OOM ni swap. El RSS alto no es por sí mismo un criterio de detención.
- AMD05 sólo permite el stop compuesto de PSI global severa y `MemAvailable <48 GiB` durante 15 muestras; conserva el corte inmediato de `MemAvailable <32 GiB` y OOM. La PSI severa del cgroup del worker es diagnóstica y no detiene sola. Los umbrales de frontera fueron cubiertos previamente por Q117 AMD05 CPU 21/21.
- SOL Q34 TP=2 dual RTX 3090 concluyó sin OOM; no tiene PSI continua, así que no permite validar el umbral temporal.
- AMD05 es una variante candidata del harness, no está integrada en el guard Q97/Q100 ni en producción. Por eso esta evidencia descarta “RSS alto de ASTRA” como falso stop de AMD05, pero no demuestra comportamiento bajo presión host severa real ni explica el cierre de Codex.

No se repetirá el replay Q118 porque no agregaría evidencia; su recibo, hashes y resultado se conservan. El smoke actual sigue siendo CPU/QtTest, secuencial y sin inferencia/GPU.

## Enmienda de build 01

El gate inicial configuró bien el build pero falló al compilar `tests/test_datalab.cpp`, antes de iniciar cualquier test: `response` estaba declarado como `QJsonObject` y luego como buffer `QByteArray`. Se renombró el objeto JSON a `responseObject`; no cambia la respuesta ni el comportamiento evaluado. Registrar el hash corregido y hacer readback de Sheets antes de repetir el gate.

## Enmienda de ejecución 02

Al intentar crear el recibo del readback se invocó accidentalmente `scripts/tests-linux.sh --help`; el script no tiene modo help y trató ese argumento como configuración, arrancando el build con los 32 jobs predeterminados. Se detuvo sólo el árbol de procesos de esa invocación; verificación posterior: cero procesos hijos restantes, cero tests iniciados, sin servidor de inferencia/GPU. No se aplicaron límites de memoria y no se midió el pico RSS del intento. Antes del único retry válido, registrar el incidente y su alcance en el Sheet; ejecutar exactamente `LC_JOBS=1 ./scripts/tests-linux.sh Release`.

## Enmienda de fixture 03

La suite Linux Release pasó 95/95, pero la nueva prueba usó el texto inline porque el primer comando no exportó `LLAMACODE_OCR_SIDECAR_FIXTURE`. Esa corrida prueba el flujo con texto sintético, pero no valida la procedencia Q49 P4 fijada en este plan. La enmienda 03 registró el smoke `test_datalab` contra `inputs/p4-form-sidecar.md` (hash completo arriba) mediante esa variable, sin recompilar ni cambiar el test; el resultado final se documenta en “Cierre de enmienda 03”.

## Cierre de enmienda 03

El smoke exacto con `LLAMACODE_OCR_SIDECAR_FIXTURE` pasó 1/1 (`test_datalab`, 0,34 s). El preflight/postflight no encontró inference server, listeners de inferencia ni proceso de build/test remanente; ArtCraft quedó intacto (207 MiB en GPU). La máquina reportó 110 GiB disponibles y 3,6 GiB de swap usado al terminar. No se impuso límite de RAM ni se hizo otra asignación grande.

Incidencias conservadas: el primer build falló antes de test por una variable duplicada del fixture y se corrigió en test-only; la invocación accidental `--help` arrancó un árbol de build con 32 jobs, que se detuvo antes de tests. El gate válido se hizo con `LC_JOBS=1`; no hubo inferencia/GPU ni medición de pico RSS durante ese incidente.
