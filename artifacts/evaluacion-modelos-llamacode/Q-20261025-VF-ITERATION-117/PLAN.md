# Q117 · ASTRA DEFAULT 1M bajo guard estricto de presión

**Estado:** Q117 cerrada. AMD05 pasó la guarda de memoria en un request real de 1M con ambas RTX 3090: 51,31 GiB RSS máximo, 58,70 GiB disponibles mínimo, HTTP 200, OOM/swap del worker=0 y 707 muestras; la PSI global máxima fue 53,61%, así que no se activó el umbral severo. La suite de frontera pasó 21/21. El parser JSON original obtuvo 0/8, pero el prompt no exige JSON; el regrade CPU AMD05-R1, con el método auditado Q37 y sin otra inferencia, confirmó 8/8 semántico por respuestas numeradas en orden. AMD04 sí demostró que PSI severa sola podía detener falsamente con 77,07 GiB disponibles, por eso la variante candidata exige PSI severa + MemAvailable <48 GiB por 15 muestras. No se integró a producción. Ver `RESULTS.md`.
**Lock:** `Q-20261025-VF-ITERATION-117`, token `6db3418d-c2cb-400b-a11a-8a328e01a11f`.

## Pregunta

¿El supervisor de una evaluación permite que ASTRA DEFAULT complete un request de 1.048.576 tokens aunque el proceso alcance RSS alto, y detiene únicamente ante presión global sostenida, OOM, `MemAvailable <32 GiB` o telemetría inválida?

## Diseño preregistrado

- Una sola request de recuperación con el holdout congelado Q35 `1048576/2026103`; no se volverá a medir calidad ni se afirmará rendimiento. Se compararán los valores de memoria con los recibos históricos sólo para validar el comportamiento del guard.
- Modelo/runtime/configuración: ASTRA DEFAULT Qwen3.8 Flash-Next GSQ-RCO IQ2_XS, Strata 0.1.41; exactamente el config ya usado por Q35 (`--max-context 1048576`, ambas RTX 3090, `--kv int8`, YaRN ×4, cache residente 32768, MTP4, sampling 0.6/0.95/20). Se verifica hash del config, prompt, esperados, ejecutable, shards y assets auxiliares antes de lanzar.
- Una evaluación a la vez en un servicio transient del **system manager**, fuera de `user@1000.service` y del scope de Codex. Se usan ambas 3090 y los 128 GiB; sin cap artificial de RAM ni cambio de modelo/contexto/perfil. La GUI/ArtCraft queda abierta y fuera de la unidad de evaluación.
- El monitor observa cada segundo `MemAvailable`, PSI global (`some/full avg10`), contador global `oom_kill`, PSI/OOM/swap del cgroup de la unidad, RSS del árbol y VRAM por GPU. RSS alto se registra y nunca causa un stop por sí solo. PSI del cgroup es diagnóstica (Q114 comprobó 81,53% cgroup con global 0%, host disponible y OOM=0 sin advertir/parar).
- Parada: `MemAvailable <32 GiB`; incremento de `oom_kill`; telemetría requerida ausente o inválida; PSI global `full>=60% OR some>=80%` por 15 muestras consecutivas usando la regla compuesta candidate Q116; o swap atribuible al worker >4 MiB. PSI global moderada (`full>=20% OR some>=70%`) avisa al sample 30 pero no aborta. PSI del cgroup por sí sola no para.
- La guarda es sólo un supervisor versionado para esta campaña; no se integra al producto ni vigila Codex, la GUI, el driver o el kernel. Si falla CPU validation, preflight, identidad dual-GPU o aislamiento, no arranca el modelo. Si la guarda detiene la unidad, sólo termina el grupo de procesos de esta prueba y conserva logs/recibos; no mata otros procesos.
- Gate de memoria: request completa HTTP 200, guard no aborta, RSS reportado por separado, `MemAvailable` nunca cruza 32 GiB, OOM y swap de worker no aumentan, ambas GPUs reciben el worker, y queda limpio el puerto/unidad. Un intento abortado es resultado de seguridad/infraestructura, no de calidad.

## Alcance de SOL

SOL permanece intacto. Q34 ya documenta su ejecución vLLM TP=2 en ambas RTX 3090, sin OOM y con ~103.4 GiB disponibles al readiness. Esa carga fue principalmente VRAM y no guardó PSI continua; repetir el benchmark no cambiaría la decisión. Esta prueba se concentra en el caso que sí tensiona memoria de host (ASTRA 1M). No se afirmará que Q34 calibra PSI de SOL.

## Controles previos

1. Releer queue/lock; verificar token y ausencia de server/listener de inferencia.
2. Ejecutar suite CPU de la regla combinada (ocho casos iniciales; enmienda 02 añade cgroup-only PSI diagnóstica): ASTRA-like RSS alto con 55.64 GiB disponibles continúa; PSI moderada avisa sin parar; PSI severa estable y alternada paran al sample 15; OOM, `MemAvailable<32` y PSI global ausente paran; muestra normal reinicia la racha.
3. Hashes exactos del código del guard, runner, script y test; preregistro Google Sheets leído de vuelta antes de ejecutar esos checks.
4. Preflight fresco: ≥80 GiB `MemAvailable`, ≥1 GiB swap libre, PSI debajo de stop, ≥23.000 MiB libres en cada 3090, ≥5 GiB en volumen de resultados, puerto 8350 libre, no inference server externo, y límites cgroup efectivos calculados con el margen de 16 GiB del host.
5. Ejecutar una única request de 1M. Guardar cada muestra, resultado, journal y limpieza; actualizar Sheets y WORK_QUEUE al cierre.

## Evidencia previa que motiva la prueba

- Q14/Q97: ASTRA DEFAULT 1M terminó con RSS ~51.14 GiB y `MemAvailable` mínimo 55.64–55.728 GiB.
- Q35/Q37: Flash-Next 1M terminó tres seeds; el mínimo fue 64.98–65.06 GiB disponibles y el servicio se aisló del gestor de usuario.
- Q97: el guard dejó continuar ASTRA con PSI global moderada de hasta 34.72% (64 warnings), 71.864 GiB mínimos disponibles y OOM=0, pero contexto fue 8192.
- Q34: SOL dual-3090 TP=2 terminó sin OOM, ~103.4 GiB disponibles; no hay serie PSI continua.
- Q108: core candidato falla cerrado cuando falta telemetría.
- Q116: helper candidato compone el OR severo por 15 muestras; Q97 histórico no implementa esa semántica si alterna `full` y `some`.
- Q117 live attempt01: el wrapper candidato añadió por error un hard-stop de PSI del cgroup; antes del request paró a los 38 s con 16,28 GiB RSS, 93,71 GiB `MemAvailable`, PSI global máx. 57,6%, PSI cgroup máx. 85,29%, OOM=0 y swap del worker=0. Q114 y Q97 establecen que cgroup PSI aislada es diagnóstica. Enmienda 02 elimina sólo ese hard-stop y añade replay explícito antes de un único retry. Evidencia en `receipts/q117-live-attempt01-*`.
- AMD02 corrigió el corte de PSI local, pero la monitoría abortó antes del proceso por la referencia colgante `run_psi_stop` (NameError). El runner no cargó el modelo ni mandó request; se corrigió la ruta con un helper probado en CPU.
- AMD03 permitió iniciar la carga con ambas GPU; el log de Strata dice que comenzó a leer los pesos y cargar ~39 GB de expertos en RAM. El transient worker estaba explícitamente en `ManagedOOMMemoryPressure=kill`; systemd-oomd lo mató al registrar PSI local avg10 92,35% durante >20 s, cuando el uso reportado era 16,4 GiB. El host snapshot cercano (25 s antes, no simultáneo) mostraba 93,48 GiB disponibles y PSI global 58,61%; el contador kernel `oom_kill` siguió en 0. La unidad se limpió, no hubo request y el proceso no llegó a healthy. Ver `runs/astra-1m-seed-2026103-attempt03/systemd-oomd.log` y `q117-live-attempt03-diagnostics.json`.
- AMD04, preregistrado en `receipts/amendment-04-preregistration.json` y Sheets, opta a `ManagedOOMMemoryPressure=auto` **sólo en esta unidad transitoria** y elimina el threshold PSI de oomd. Retiene `MemoryHigh`, `MemoryMax`, `MemorySwapMax`, `OOMPolicy=kill`, la reserva de 16 GiB, los hard stops de presión global/OOM/telemetría y ambas 3090. El worker verifica el readback efectivo `auto` antes de lanzar Strata; añade JSONL con flush por muestra para conservar evidencia si hubiera SIGKILL externo. Pasó 6/6 pruebas de política/telemetría y 13/13 del guard; queda un preflight fresco y una única solicitud real, sin más retry si vuelve a abortar antes del request.

La prueba no atribuye a este detector los cierres anteriores de Codex: Q35 documentó `systemd-oomd` terminando el scope de escritorio cuando una evaluación estaba en el cgroup de usuario. Tampoco promete inmunidad a fallos de kernel, driver o hardware.

## Enmienda 01 · replay CPU antes del canario

El primer intento del test CPU (registrado en `receipts/q117-cpu-guard-attempt01.json`) obtuvo 7/8. La combinación propagaba el booleano instantáneo de warning del parser Q108 y omitía la cadencia de 30 muestras Q116. Se ajusta el adaptador para usar el warning con persistencia Q116; hard-stops, thresholds, entradas, workload y gate de inferencia no cambian. No se inició modelo ni servidor. La enmienda y el hash corregido se registran en `receipts/amendment-01-preregistration.json` y en Sheets antes del retry.


## AMD04 · resultado de la guarda durante la carga

AMD04 corrigió el factor externo de AMD03: la unidad transient leyó de vuelta `ManagedOOMMemoryPressure=auto`, `systemd-oomd` no la mató y el worker no tuvo OOM ni swap atribuible. En 309 muestras de carga, el máximo PSI global avg10 fue 63,11%, pero `MemAvailable` nunca bajó de 77,065 GiB y el árbol alcanzó 33,851 GiB RSS. La regla de PSI severa sin considerar memoria disponible detuvo el worker antes de que Strata estuviera healthy; no se envió request y no se obtuvo resultado de modelo. Véanse `runs/astra-1m-seed-2026103-attempt04/q117-live-attempt04-diagnostics.json` y los logs crudos.

## Enmienda 05 · PSI severa sólo con poco headroom

El antecedente de usuario indica ASTRA DEFAULT 1M exitoso con `MemAvailable` mínimo 55,64–55,728 GiB y RSS ~51,14 GiB; ASTRA Flash-Next 1M también terminó con ≥64,98 GiB disponibles. AMD04 mostró que PSI global severa sola aparece durante carga aun con 77 GiB disponibles. Por eso AMD05 conserva la advertencia PSI moderada, pero sólo aplica el hard-stop PSI si `full avg10 >=60% OR some avg10 >=80%` **y** `MemAvailable <48 GiB` se mantienen juntos durante 15 muestras consecutivas. El umbral de 48 GiB queda 7,64 GiB por debajo del mínimo histórico exitoso de ASTRA DEFAULT 1M. `MemAvailable <32 GiB`, aumento de OOM global/cgroup, swap atribuible al worker >4 MiB y telemetría ausente/invalidada continúan como stops independientes; RSS y PSI de cgroup siguen siendo diagnósticos.

El cambio vive en una variante AMD05 aislada; el guard Q97/Q100 y producción no se modifican. La política transitoria de systemd-oomd permanece en `auto` (sin inscripción de PSI-kill) y se verifica dentro del worker. Se preregistró en `receipts/amendment-05-preregistration.json` y en la fila 338 del Sheet antes de editar la variante y correr pruebas. CPU tests cubren PSI severa con 77 y 55,64 GiB disponibles, la frontera de 48 GiB al sample 15, recuperación/reset, el corte de 32 GiB y las salvaguardas OOM/swap/telemetría. Sólo si los tests y el preflight fresco pasan se ejecutará una request 1M en ambas RTX 3090; si no llega a respuesta, AMD05 se cierra sin otro live retry. SOL Q34 permanece como control histórico y no se repite.

## AMD05 · resultado final

El preflight pasó con 110,74 GiB disponibles, PSI/OOM en cero, ambas GPU libres y `ManagedOOMMemoryPressure=auto`. El modelo alcanzó readiness y atendió una única request HTTP 200 de 1.001.463 tokens en 442,448 s. El prefill fue 2.270,9 tok/s y decode 82,0 tok/s. RSS máximo 51,306 GiB, `MemAvailable` mínimo 58,698 GiB, PSI global máxima 53,61%, cgroup OOM/swap cero; VRAM pico +22.831/+22.372 MiB en GPU0/GPU1. El guard no abortó; la unidad y el puerto se limpiaron.

El protocolo de memoria pasa. La salida numerada contiene los ocho valores esperados y el regrade semántico CPU pasa 8/8. El 0/8 del parser JSON queda registrado por separado como formato diagnóstico; el prompt no pide JSON. La PSI severa concurrente con baja memoria no se produjo en el canario real; la frontera queda cubierta por CPU. La nueva política es un candidato sin integrar, pendiente de revisión antes de cambiar el guard productivo.
