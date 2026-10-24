# Q106 — Revisión del guard de memoria y regresiones CPU de tools

**Estado:** cerrado PASS; tres casos enfocados y gate Linux Release completos con entorno saneado.
**Lock:** `cb78d8ff-dcf8-460a-936f-62f50f0fb848`.

## Objetivo

Atender la duda del usuario sobre el detector de presión y continuar la prioridad P2.1 con una validación de la regla de replanificación de tandas mixtas de tools que ya está en el working tree. No modificar ese código preexistente.

## Revisión del detector (sólo evidencia local)

- ASTRA DEFAULT 1M real, Q14/Q35: 10/10 respuestas exactas; RSS del árbol ~51,14 GiB; `MemAvailable` mínimo 55,728 GiB; sin PSI de memoria, swap-out u OOM. La carga alta por sí sola no era un hard-stop.
- SOL Q34: ejecución dual TP=2 completada sin OOM; el registro histórico no tiene PSI continuo ni RSS del host, así que no se usa como calibración de presión.
- Guard Q102: observa `MemAvailable`, PSI global de memoria y delta de `oom_kill`; no decide por RSS ni porcentaje ocupado. Umbrales registrados: aviso moderado continúa; hard-stop por MemAvailable <32 GiB, OOM nuevo o PSI severa sostenida (full ≥60% / some ≥80% durante 15 muestras de 1 s).
- Q103: RSS anónimo CPU de 56,013 GiB por 12 s, MemAvailable mínima 53,386 GiB, PSI máxima avg10 0,36%, cero aviso/stop/OOM y recuperación inmediata. Junto con replay Q102 19/19 y Q100 bajo PSI moderada, esto comprueba tolerancia al RSS alto y los límites por replay; no representa inferencia CUDA ni supervisa VRAM.

Conclusión provisional: los recibos respaldan que el guard no trata el uso alto de RAM como presión crítica. No cambiar thresholds, perfiles, ASTRA, SOL, swap ni límites. La verificación de este turno no vuelve a cargar modelos.

## Experimento preregistrado

- Objetivo: comprobar en el `LlamaAgentBackend` actual que para `read_file → read_file` y `read_file → task` sólo se ejecuta la primera acción de la respuesta mixta antes de una nueva completion; la segunda aparece como omitida/replanificada después de que el primer resultado exista. Comprobar además que las tandas task-only pueden seguir fan-out.
- Fixture: dos archivos temporales sintéticos y un servidor HTTP falso ligado a loopback ephemeral; no se envía texto a un modelo.
- Comandos: `CUDA_VISIBLE_DEVICES= LLAMACODE_Q77_SERVER_URL= LLAMACODE_Q102_SERVER_URL= LC_JOBS=2 ./scripts/tests-linux.sh Release`; luego ejecutar de forma enfocada el binario `test_agent_wire` para `toolBatchRequiresReplan_onlyTaskBatchesFanOut`, `nativeToolBatchReplansAfterFirstResult` y `nativeMixedTaskBatchDoesNotDispatchLaterTaskEarly`.
- PASS: build y CTest completos terminan sin fallos, las tres pruebas enfocadas pasan, y el test Q77 queda opt-in/skipped al no definir endpoint. Si se produce un fallo, no iniciar inferencia/modelo; conservar logs y cerrar como bloqueado/fallido con repro.
- Límites: esta validación cubre orden/replanificación en LlamaCode con fixtures; no valida autorización multitenant server-side, la calidad de Qwen/OpenJet ni una integración real de reservas/notificaciones. No habilita adopción de Qwen.
- Recursos: CPU, Qt offscreen, loopback local; GPU no usada; sin servidor de inferencia ni PeritoSoft; no señalizar ni detener procesos ajenos; sin límites de RAM/swap nuevos.

## Salida esperada

Actualizar `RESULTS.md`, recibos, `WORK_QUEUE.md`, la fila de evaluación Q106 y la recomendación P2.1 en el Sheet; reconciliar los datos locales de la app. No commit de los cambios preexistentes.
