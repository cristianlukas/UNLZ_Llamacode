# Q118 · revalidación de pendientes del lote VF-20261019-01

**Estado:** Cerrada · 2026-10-25T02:04Z
**Lock:** `5e84ed99-0aad-4ddb-817d-597ca20af3c9`
**Objetivo:** comprobar con el estado actual si algún material bloqueado del inbox o accionable abierto ya permite una prueba que pueda cambiar una decisión, y reconciliar los registros locales y Sheets.

## Alcance preregistrado

1. Revalidar las fuentes #26, #28, #31 y #32, las cuatro entradas que siguen como `Bloqueada` en `VF-20261019-01`. Para claims técnicos usar sólo la publicación primaria/repositorio; no descargar medios, código ni modelos.
2. Revisar el estado actual de los accionables abiertos P0 (Job Objects/entrypoints Windows) y P2.1 (principal autenticado/policy tenant) contra el ejecutor y el código local. No modificar cambios ajenos ni implementar una feature durante esta auditoría.
3. Confirmar que el Q117 de memoria y el regrade semántico aparecen en `data/actionables.json`, porque la app local y el Sheet son depósitos explícitos del usuario.
4. Si no cambió una condición externa, actualizar sólo el registro de la fuente #32 y el accionable P0 que quedaron desfasados; dejar #26/#28/#31/P2.1 con su condición concreta vigente. Releer y verificar los cambios.
5. No ejecutar build, benchmark, modelo, descarga ni usar GPU. No se autoriza iniciar servidores, crear presión de memoria, llamar servicios frontier ni tocar perfiles, modelos, RAM/swap o pesos productivos. Una fuente nueva que sí justifique experimento se registrará para una tarea posterior con un preregistro separado.

## Revalidación de fuente preparada antes de reclamar el lock

El acceso público a `https://www.instagram.com/reel/DefpbUKlMxh/` se probó como lectura independiente, sin editar archivos ni usar recursos del repo. `web.open` fue throttled y la búsqueda exacta no recuperó el reel. Este resultado se considera evidencia de accesibilidad de fuente, no benchmark; se repetirá una apertura acotada bajo este scope para dejar el recibo asociado a Q118.

## Criterio de salida

- Cada fuente #26/#28/#31/#32 conserva resultado verificable y una condición concreta para reabrir, o habilita un test nuevo claramente identificable.
- Cada accionable abierto queda confirmado como ejecutable o bloqueado por la plataforma/contrato actual.
- `data/actionables.json`, `data/inbox.json`, `WORK_QUEUE.md`, `RESULTS.md`, recibos locales y los rangos Sheet pertinentes describen el mismo estado.
- El lock se libera sólo tras comprobar el token y la lectura de vuelta.

## Enmienda de alcance de registro

Las lecturas actuales encontraron una publicación relacionada nueva para #26 y una edición nueva en #28; ambas aportan contexto suficiente para actualizar la nota de revalidación aunque ninguna habilite un test local. Actualizar `currentRevalidation` de las cuatro entradas bloqueadas (#26/#28/#31/#32), manteniendo su `status` bloqueado y explicitando por qué el nuevo material no cambia la aplicabilidad. Para #26 separar el log físico de `709.py` en A100 (17/17 checks mecánicos y 11/11 trials, `PASS_PHYSICAL_UNSCORED_SEMANTICS`) de la demo `MAM_full_QWEN_72B.py`, cuyo encabezado dice que no fue ejecutada por el autor; Zenodo no resultó accesible y el target requiere una sola A100/Qwen2.5-72B, no el perfil local Flash-Next/Strata. Para #28 registrar la edición del autor (90% del trabajo y una race condition corregida con SOL) pero mantener la falta de fixture/diff/tests/control externo. Para #31 el README actual sigue declarando Linux ROCm/HIP, `gfx1100`, RX7900 y ~570 GB NVMe. Para #32 continúa throttled/no atribuible.

## Enmienda preregistrada · replay del detector sobre la corrida real ASTRA DEFAULT 1M

**Motivo:** el usuario recordó que ASTRA DEFAULT 1M y SOL completaron con uso alto de memoria y pidió verificar que el detector no confunda ocupación/RSS con presión. La evidencia previa ya indica que la política no usa RSS como condición de parada; esta enmienda agrega una comprobación contra el rastro real persistido, además de las pruebas sintéticas AMD05 ya aprobadas.

**Auditoría de identidad previa al replay:** el wrapper realmente usado, `run_context_holdout_attempt05.py`, importa explícitamente `q117_pressure_guard_attempt05.evaluate`; esa es la variante AMD05 con PSI severa + `MemAvailable <48 GiB`. Existe además `q117_pressure_guard.py`, helper genérico anterior que no implementa la conjunción; no debe usarse para atribuir el resultado AMD05. El replay usará exclusivamente el módulo attempt05 y verificará su hash contra el prerregistro.

**Prueba CPU/offline:** leer sin modificar `Q-20261025-VF-ITERATION-117/runs/astra-1m-seed-2026103-attempt05/memory-monitor.jsonl`; pasar cada muestra de `MemAvailable`, PSI global `some/full avg10` y `oomKill` por la función exacta `q117_pressure_guard_attempt05.evaluate`, conservando contadores entre muestras. Registrar cantidad de muestras, mínimo de MemAvailable, máximos PSI/RSS, paradas/avisos y comparación con el recibo de la corrida. No conectar a servidores, no cargar modelos, no reservar GPU, no asignar RAM artificial y no tocar la traza original.

**Éxito esperado:** 707 muestras procesadas, ningún hard-stop, ninguna muestra con OOM nuevo, MemAvailable mínima igual al recibo (~58,70 GiB) y RSS máximo igual al recibo (~51,31 GiB); los campos de RSS se tratan como diagnóstico y no alteran la decisión. Si el replay diverge del resultado guardado o los hashes/valores fuente no coinciden, detener y documentar la discrepancia antes de abrir otros gates.

**Control histórico SOL:** validar sólo el recibo Q34 ya existente: TP=2 en las dos RTX 3090, ejecución completa y cero OOM. Como Q34 no guarda PSI continua, no inferir que pasó los umbrales del detector ni repetirlo.

**Separación de decisión:** ASTRA DEFAULT 1M es evidencia de aceptación real ante RSS alto; SOL es evidencia de finalización sin OOM; ninguna es una prueba de que toda causa de cierre de Codex esté detectada. No cambiar umbrales, integración de Q97/Q100, memoria, swap, contextos, perfiles ni modelos. Después de este replay, continuar la revalidación Q118 de fuentes/actionables; sólo abrir otra prueba si un gate local verificable queda habilitado.

**Corrección preregistrada del runner de replay (intento 01):** la primera invocación se detuvo antes de evaluar una muestra porque el script esperaba el resumen bajo `q117["run"]`; el recibo histórico guarda esos datos en `q117["memory"]`. No se procesó la traza, no se escribió resultado ni hubo efectos externos. Corregir únicamente la ruta de lectura, fijar el nuevo hash del script en el recibo preregistrado y repetir la misma comprobación; el resultado fallido se conserva en el historial de Q118.

## Cierre y reconciliación

- El replay corregido pasó 12/12 checks sobre las 707 muestras; ver `receipts/q118-amd05-live-trace-replay.json`.
- Las cuatro entradas #26/#28/#31/#32 mantienen un resultado y condición de reapertura; no habilitaron otra prueba local.
- Reconciliación local: `data/inbox.json` contiene 58 materiales con resultado; el accionable P0 conserva su estado parcial e incorpora el resultado Q118. Los respaldos anteriores a la escritura están en `data/backups/inbox.q118-prechange.20261025T020301Z.json` y `data/backups/actionables.q118-prechange.20261025T020301Z.json`.
- Google Sheets verificado por lectura posterior: `Evaluaciones LlamaCode!A339:J339` y `Accionables!A2:N2`; ambos rangos tienen `WRAP`. Q118 elevó la fila 339 a 160 px. Recibo: `receipts/google-sheet-sync-q118-final.json`.
- No se abre otra prueba de modelo en esta sesión Linux: C39-01/Qwen Flash-Next NInfer y los Job Objects requieren Windows nativo; el test P2.1 necesita un contrato de principal y policy tenant reales; HyperQwen sigue condicionado a un defecto parser/runtime reproducible. Las pantallas de Qwen3.8-27B, RCO y Swift ya están cerradas sin superar calidad/seguridad o sin habilitar follow-up.
- Sin GPU, servidor, descarga, build ni asignación artificial de memoria en Q118. ASTRA, SOL, perfiles, límites, swap y guard productivo quedan intactos. No hay evidencia nueva que atribuya los cierres de Codex.
