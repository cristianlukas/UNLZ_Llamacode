# Resultados — Q-20261018-LLAMACPP-MTP-REMAINING

**Estado:** completada el 2026-10-18 a las 14:14 UTC. El usuario liberó las dos
GPU y se ejecutaron en serie las dos pruebas pendientes, sin modificar perfiles,
modelos, HarnessSpec ni código de producción. Ninguna dio un resultado que
permita promover MTP.

## Verificaciones para reanudar

- MemAvailable 117,1 GiB, swap libre 8 GiB, PSI `some/full avg10=0`,
  `oom_kill=0`.
- Las dos RTX 3090 informan cero procesos de cómputo CUDA. `nvidia-smi pmon`
  muestra sólo Xorg, Compiz y Codex gráfico. Los puertos 8033, 8081, 8350, 8877,
  8898, 18111, 18112 y 18119 estaban libres antes del daemon.
- Se verificó presencia de los cuatro shards base; el recibo anterior conserva
  sus SHA-256 completos. El sidecar sigue disponible y su SHA-256 coincide
  (`58a47d6a…951da8d1`). `llama-server` y LlamaCode coinciden con sus hashes
  fijados.
- Perfiles y suites listos. Tras seleccionar `agent-maximo` y thinking activo,
  la API devolvió los fingerprints esperados: BCB8 MTP-off
  `7f84727070a2fb93d008a42c90391f3904d800f7d7c2e67f173813ab0435ff89`, TaskFlow
  MTP-off `e9c5c527e30744049cff955f0489c36cd08a8777b9bf87422f0f768c3d42cf23`.
  HE0/HE20 están válidos y BCB pendiente para BCB8. Estado de servidor/agent
  detenido y benchmark ocioso al pasar el gate.
- Una consulta inicial de cobertura, antes de setear el agente y thinking del
  benchmark, mostró huellas diferentes y gates pendientes. No se cargó ningún
  modelo en esa consulta; se corrigió el orden de setup y el preflight posterior
  pasó con las huellas fijadas. El setup efectivo queda registrado en
  [preflight de API](receipts/api-preflight-resumed.json).

## Pruebas previas que conservan su clasificación

- Q-20261010: HE0/HE20 válidos en ambos brazos, BCB8 MTP-on 3/8 final; BCB8
  MTP-off 2/8 cancelado; TaskFlow no ejecutado. Hard Mode y speed probe están
  resumidos en el documento canónico.
- Q-20261017 FOLLOWUP: BCB8 MTP-off cancelado por una guarda de swap antes de
  puntuar; TaskFlow no iniciado.
- Q-20261017 RESUME: BCB8 MTP-off incompleto en 4/8; TaskFlow MTP-off
  interrumpido en 3/10 sin resultado final; TaskFlow MTP-on completado 0/13
  tras tres reparaciones, fallo válido de calidad. Detalles y recibos en
  [Q-20261017 RESUME](../Q-20261017-LLAMACPP-MTP-CODING-RESUME/RESULTS.md).

TaskFlow MTP-on 0/13 no se repite porque ya es una medición válida y no hubo
cambio de fingerprint que motive una nueva prueba. Se reintentaron una sola vez
BCB8 MTP-off y TaskFlow MTP-off, con las huellas y suites exactas, sólo para
obtener un resultado final donde faltaba. No se cuentan como muestras de
variabilidad.

## Resultado tras liberar las GPU

- **BCB8 MTP-off:** corrida iniciada a las 13:36:21 UTC y cancelada a las
  13:48:21 UTC dentro del límite preregistrado de tres reparaciones. El harness
  permaneció en el primer ítem: 1/8, progreso 0% antes de cancelar. Cuatro probes
  de aceptación (intento inicial + tres reparaciones) dieron 1/8 con fallo duro.
  El estado de cobertura mantiene BCB pendiente; no hay score final y no se
  cuenta como 0/8 ni como fallo de infraestructura. La cancelación dejó el
  servidor aislado detenido.
- **TaskFlow ULTRA MTP-off:** corrida iniciada a las 13:49:17 UTC y completada a
  las 14:13:47 UTC (1459,693 s reportados por el harness), perfil fingerprint
  `e9c5c527e30744049cff955f0489c36cd08a8777b9bf87422f0f768c3d42cf23`.
  Resultado final **0/13**, fallo de calidad, dos reparaciones; el intento inicial
  también fue 0/13. No se creó ninguno de los diez archivos solicitados ni se
  pasó ninguno de los tres comandos de aceptación. El turno inicial duró 510,945
  s sin llamadas de herramienta; después hubo 18 llamadas `run_shell` y ninguna
  llamada de escritura. El agente se desvió a investigar MTP/llama.cpp y dejó un
  clon temporal en `/tmp`; se retiró ese clon al terminar. No hubo timeout ni
  crash del servidor.
- **Recursos:** los recibos de monitorización no registran aumentos de OOM,
  presión sostenida ni procesos CUDA ajenos durante ninguna corrida. Antes de
  TaskFlow había 118,2 GiB disponibles y cero apps CUDA; al final quedaron
  `benchmarkRunning=false`, servidor/agente aislados detenidos, GPU sin procesos
  de cómputo y `oom_kill=0`.

TaskFlow MTP-on 0/13 permanece como resultado histórico válido y no se repitió.
La campaña sigue incompleta para una comparación BCB8 entre brazos y no demuestra
mejora de MTP. El síntoma de mayor prioridad es la deriva del agente fuera del
prompt/workspace de TaskFlow; no repetir estos fingerprints hasta corregir y
validar ese flujo.

## Por qué las tareas no arrancan solas

`WORK_QUEUE.md` es una cola de coordinación manual, no un despachador. El runner
de benchmarks de LlamaCode usa un único slot (`parallel=1`) y avanza al siguiente
prompt después de que termina el turno y el cooldown. Una corrida activa o una
generación sin terminar ocupa ese slot. Esta continuación tuvo el lock propio y,
cuando el usuario liberó las GPU, ejecutó los dos parciales secuencialmente. La
tarea ya cerró y no quedan pruebas encoladas por esta continuación.

No se corren tests C++/QML: no hay cambios de producción. La evidencia previa
queda preservada; se registran los resultados finales y postflight de esta
continuación.

## Recibos

- [Preflight del sistema y hashes fijados](receipts/preflight-resumed.json)
- [Preflight de perfiles/suites y cobertura](receipts/api-preflight-resumed.json)
- [Perfiles efectivos](receipts/effective-profiles-resumed.json)
- [Resultado BCB8 MTP-off](receipts/bcb8-mtp-off-completion-20261018.json) y
  [eventos del runner](receipts/bcb8-mtp-off-completion-20261018.events.jsonl),
  [eventos del agente](receipts/bcb8-agent-events-20261018.jsonl),
  [monitor de recursos](receipts/resource-monitor-bcb8.jsonl) y
  [progreso del slot](receipts/bcb8-slot-progress.jsonl)
- [Resultado TaskFlow MTP-off](receipts/taskflow-mtp-off-completion-20261018.json) y
  [eventos del runner](receipts/taskflow-mtp-off-completion-20261018.events.jsonl),
  [eventos del agente](receipts/taskflow-agent-events-20261018.jsonl)
- [Preflight antes de TaskFlow](receipts/preflight-before-taskflow.json),
  [monitor de recursos](receipts/resource-monitor-taskflow.jsonl),
  [progreso del slot](receipts/taskflow-slot-progress.jsonl) y
  [postflight](receipts/postflight-taskflow.json)
- [Plan preregistrado](PLAN.md)
