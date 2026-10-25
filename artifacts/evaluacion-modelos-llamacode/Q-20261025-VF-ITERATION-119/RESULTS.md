# Q119 · auditoría del detector y smoke OCR sidecar · 2026-10-25

## Detector de presión de memoria

La evidencia coincide con lo que señaló el usuario: las ejecuciones exitosas de ASTRA DEFAULT 1M y SOL consumieron mucha memoria y terminaron sin que el RSS alto, por sí solo, provocara una parada.

- ASTRA DEFAULT 1M terminó con HTTP 200 en 442,45 s sobre ambas RTX 3090; el replay Q118 de sus 707 muestras pasó 12/12. RSS máximo: 51,306 GiB; `MemAvailable` mínimo: 58,698 GiB; PSI global máxima: 53,61%; sin stop, OOM ni swap del worker.
- SOL Q34 TP=2 terminó en las dos RTX 3090 sin OOM. No guardó PSI continua, así que confirma la terminación exitosa pero no calibra un umbral temporal.
- AMD05 es candidato del supervisor, no está integrado en Q97/Q100 ni en producción. La traza exitosa no alcanzó la condición de stop severo con bajo headroom.

**Matiz que cambia la evaluación:** Q116 ya encontró un falso negativo en el helper activo Q97/Q100 cuando la política escrita se interpreta como `full>=60% OR some>=80%` sostenido 15 muestras. El helper real mantiene contadores por métrica; si las señales alternan y el OR es cierto en todas las muestras, ninguna racha individual llega a 15 y no se detiene. El candidato de Q116 con racha OR compuesta pasó 5/5, pero no se integró. Así que la parte “no cortar por RSS alto con headroom” está respaldada por ASTRA; el detector no está validado en todos los patrones PSI severos y no debe declararse completamente correcto. Esta brecha no demuestra que haya causado cierres de Codex.

No se modificaron umbrales, supervisor, RAM, swap, modelos, perfiles ni comportamiento de producción. No se repitió ASTRA/SOL ni se hizo asignación artificial de memoria.

## Smoke OCR de Data Lab

`LC_JOBS=1 ./scripts/tests-linux.sh Release` compiló y pasó **95/95**. En esa corrida el test nuevo usó el texto inline de fallback porque no se exportó `LLAMACODE_OCR_SIDECAR_FIXTURE`; por eso la suite no acredita procedencia del archivo Q49.

La enmienda 03 ejecutó después `test_datalab` con la variable apuntando al sidecar Markdown exacto de Q49 P4. El test pasó **1/1** en 0,34 s. El camino comprobado fue: leer un `.md` temporal, conservar `FORM-8821-Z` y `LAB-CEDAR-07` en el prompt, recibir JSON de un fake HTTP loopback, validar el registro y borrar el job.

Esto demuestra ingestión y validación de texto de sidecar por Data Lab. No prueba extracción OCR automática desde un PDF escaneado, documentación real/legal, calidad comparativa nueva ni preparación para integrar el OCR en producción. Sigue siendo necesario el opt-in y un holdout real autorizado para continuar con esa decisión.

## Recursos, incidencias y limpieza

La prueba fue CPU/QtTest: no inició inferencia, servidor externo ni trabajo GPU; ArtCraft se dejó intacto (207 MiB reportados). No se aplicó límite artificial de RAM. Al cierre quedaban aproximadamente 110 GiB disponibles y 3,6 GiB de swap usado; no quedaban procesos de build/test/inferencia ni listeners del harness.

Se conservaron las incidencias: el primer intento de compilación falló antes de tests por un identificador duplicado en la fixture, corregido sólo en el test; una invocación accidental de `tests-linux.sh --help` inició un árbol de 32 jobs y se detuvo antes de ejecutar pruebas. No se midió el pico RSS de esa invocación. El gate válido se ejecutó con `LC_JOBS=1`.

## Decisión y seguimiento

- Mantener ASTRA DEFAULT 1M y SOL, sin reducir contexto ni memoria por causa del RSS histórico.
- No atribuir a este guard el cierre de Codex. Q97/Q100 son protecciones del harness de evaluaciones, no una vigilancia general de Codex, el escritorio, el driver o el OOM killer.
- Antes de depender del hard-stop PSI severo, integrar y validar un streak compuesto versionado (o corregir explícitamente la especificación para persistencia por métrica). No activar un stop más agresivo basado en RSS.
- Mantener el OCR aislado; reabrir con autorización para un holdout de documentos reales y evaluación de extracción automática.

Se registró el seguimiento del guard como `q119-memory-pressure-composite-streak` en los accionables locales y en `Accionables!A18:N18`. Antes del próximo benchmark debe validarse un supervisor versionado que combine el OR severo y el headroom, manteniendo el caso de ASTRA con headroom como control. El helper candidate-only existente no sustituye esa integración/prueba combinada.

## Evidencia

- Prerregistro y alcance: `PLAN.md`, `receipts/q119-preregistration.json`, enmiendas 01–03.
- Resultado de prueba y postflight: `receipts/q119-test-run.json`.
- Revisión del guard: `receipts/q119-memory-detector-review.json`.
- Q116 que documenta la condición PSI alternada: `../Q-20261025-VF-ITERATION-116/RESULTS.md` y `receipts/q116-composite-candidate.json`.
- Q118 replay de la traza real ASTRA: `../Q-20261025-VF-ITERATION-118/RESULTS.md` y `receipts/q118-amd05-live-trace-replay.json`.
- Sidecar P4 exacto, SHA-256 `e5b6b53eb0a14d67df5e954c1428df77c143d469ba100fd54e4accdabaafc3ae`.
