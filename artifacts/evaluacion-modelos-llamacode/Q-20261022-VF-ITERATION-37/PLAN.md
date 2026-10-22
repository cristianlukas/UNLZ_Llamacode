# Q37 — Evitar que el sistema cierre Codex y las pruebas · 2026-10-22

**Lock:** `89bea058-cced-43f6-a5e8-2ee41da2394e`
**Estado:** la mitigación de systemd-oomd y el aislamiento del runner Q35 quedaron aplicados y verificados; la matriz Q35 terminó sus 12 celdas en serie. El regrade semántico corrige el parser JSON no solicitado por el prompt: las siete respuestas completas (`stop`) pasan 8/8 y las cinco respuestas limitadas por `length` al cap de 768 son parciales. Mantener 131K como default; 1M sólo para tareas que requieran más de 131K, aceptando ~10,6× latencia media de request. No quedan inferencias priorizadas habilitadas con los artefactos actuales. Detalle en `RESULTS.md` y `receipts/q35-matrix-final-decision.json`.

## Hallazgo

El cierre observado de Codex fue una decisión de `systemd-oomd`, no un segfault: el 2026-10-22 a las 13:17:27 UTC, OOMD terminó el scope `app-org.chromium.Chromium-833601.scope` al superar la presión del user-manager 63,31% durante más de 20 s frente al límite 50%. PSI del scope: 90,01%; el cgroup tenía 103,5 GiB actuales y pico 112,9 GiB. No se encontró un minidump reciente. El evento no identifica qué proceso del scope produjo el pico.

En Q35-05, en otro intento, el guard detuvo el worker antes del request con RSS de árbol 5,68 GB, `MemAvailable` mínimo 117,2 GB y cero swap-out. El guard cancelaba sólo por PSI del user-manager ≥35% durante cinco muestras. Ese chequeo confundía presión de un cgroup padre con memoria agotada por la prueba.

La configuración de Q35 que se describía como “aislada” sólo estaba en `background.slice` **dentro de** `user@1000.service`. OOMD puede terminar el servicio padre completo; por eso ese aislamiento no garantiza que la prueba sobreviva al cierre de la sesión de usuario.

## Mitigación preregistrada y aplicada

1. Ejecutar supervisor y worker de Q35 como unidades transitorias del gestor systemd del sistema, bajo `background.slice`, con `User=1000`/`Group=1000`, en un cgroup fuera de `user.slice/user-1000.slice/user@1000.service`. El supervisor no depende de que Codex siga abierto. El worker conserva límites dinámicos de `MemoryHigh`, `MemoryMax` y swap, más `OOMPolicy=kill`, `KillMode=control-group` y `OOMScoreAdjust=900`.
2. Retirar PSI del user-manager como razón autónoma para abortar Q35. PSI intermedio queda registrado; siguen abortando `MemAvailable <20 GiB`, delta >4 MiB de swap del cgroup de inferencia, PSI global ≥80%/60% sostenido durante 15 muestras y PSI del cgroup del worker en el mismo nivel. El preflight mantiene `MemAvailable ≥80 GiB`, `SwapFree ≥1 GiB`, PSI global no severo, hashes, disco, procesos/puertos y GPU requeridos.
3. Ajustar OOMD de la unidad worker a 80%, alineado con el guard severo, conservando `ManagedOOMMemoryPressure=kill`, límite dinámico del cgroup y OOMD global activo.
4. Cambiar **sólo** el límite de `user@1000.service` de 50% a 70%. Aplicado con `systemctl set-property` persistente y verificado por readback. OOMD sigue habilitado y conserva autoridad para intervenir ante presión grave. No se alteró la configuración global de OOMD.

No se cambian pesos, cuantización, contexto, sampling, perfil productivo ni memoria lógica que solicita el modelo. Tampoco se mataron servidores o procesos ajenos.

## Diagnóstico de Q35 intento 06: contador global de swap

El recibo del intento 06 muestra que el guard abortó antes de health/request porque `/proc/vmstat:pswpout` aumentó 1.458 páginas (5,70 MiB). Durante ese intervalo `MemAvailable` nunca bajó de 119.390.248.960 bytes (~111,2 GiB); PSI avg10 máximo fue 8,62% global y 17,02% en el cgroup de inferencia, y 0% en user-manager, sin alcanzar el gate severo 80%/60%. El contador es del host completo y no atribuye el swap a la unidad de la prueba. Un primer extracto tomó solo la muestra inicial; los máximos están reconciliados en `receipts/q35-attempt-06-evidence-reconciliation.json`.

Corrección preregistrada en `receipts/q35-swap-guard-fix-preregistration.json`: conservar `pswpin/pswpout` como telemetría del host; añadir `memory.swap.current` y su delta al snapshot del cgroup propio, y usar ese delta >4 MiB como condición de aborto atribuible al worker. Se conservan el piso de MemAvailable y los gates de PSI sostenido. Antes de otro intento con modelo, la regresión CPU-only debe demostrar que swap global ajeno no aborta y swap cargado al cgroup sí lo hace. No se cambia el fixture, el modelo, el contexto, el sampler ni los perfiles protegidos.

## Validación

- Regresiones CPU-only de Q35: la revisión Q37 inicial pasó 17/17; tras corregir el contador global de swap, pasó 18/18; al añadir la validación de hash del fixture contra el manifiesto pasó **20/20**. Incluye 117 GiB disponibles con PSI de user-manager de 63,3% (continúa), `pswpout` global >4 MiB sin aborto, swap del cgroup >4 MiB con aborto, memoria disponible <20 GiB (aborta), PSI severo global y del worker (aborta), hashes exactos pasan y hashes alterados del prompt/answers bloquean antes de inferencia, rechazo de cgroups dentro de `user@1000` y ciclo start/stop del monitor.
- Un servicio systemd descartable de 512 MiB intentó asignar memoria bajo `MemoryMax=128 MiB`, `MemorySwapMax=0`, `OOMPolicy=kill`, `KillMode=control-group`. El resultado fue `oom-kill` sólo para su unidad; `oom.group=1`, cgroup `/background.slice/...`, controlador vivo y los PID de ChatGPT/Codex sin cambios. Q35 leyó correctamente desde ese servicio el cgroup worker y el PSI de `user@1000.service`. Sin GPU ni inference server.
- Prueba inicial del harness falló antes de asignar memoria porque el directorio `receipts/` aún no existía; unidad fallida limpiada y no dejó hijo activo. Se creó el directorio y el ensayo repetido pasó.
- `py_compile` de los scripts y `bash -n` del launcher pasan. No se ha iniciado el barrido Q35.

La lectura de `progress.json` reveló que el intento Q35-01 había fallado antes de request por ausencia de `Monitor.stop()`; se restauró el ciclo de vida del hilo y se añadió su regresión. También se detectó que la reanudación Q35 corre bajo el lock Q37: launcher, supervisor y worker ahora transportan el task id del lock sin confundirlo con el id de la campaña Q35. Ambas correcciones pasan en la suite antes del próximo preflight.

## Estado del sistema y rollback

- Propiedad efectiva: `ManagedOOMMemoryPressure=kill`, `ManagedOOMMemoryPressureLimit=70%` en `user@1000.service`.
- El override persistente está en `/etc/systemd/system.control/user@1000.service.d/50-ManagedOOMMemoryPressureLimit.conf`; existe también su copia runtime. Para volver al valor de distribución (50%), ejecutar `sudo systemctl revert user@1000.service` y comprobar `systemctl show user@1000.service -p ManagedOOMMemoryPressureLimit`.
- El umbral 70% evita el evento observado a 63,31%, no garantiza que nunca vuelva a cerrarse la GUI si la presión llega a nivel grave. Las pruebas ya no comparten el ciclo de vida de la GUI y cada worker conserva su límite de recursos.
- Antes de la siguiente inferencia: verificar lock Q37, ausencia de servidores/listeners, MemAvailable/SwapFree, ≥23.000 MiB libres en ambas RTX 3090, hash del perfil/weights/runtime y volumen de salida. Sólo entonces retomar `131072/2026101` dentro de una unidad system manager.

## Artefactos

- Código y regresiones: `../Q-20261022-VF-ITERATION-35/scripts/`.
- Prueba OOM aislada y recibo: `scripts/test_system_service_containment.py`, `scripts/oom_worker.py`, `receipts/system-service-oom-containment.json`.
- Política del sistema: `receipts/systemd-runtime-policy.json`.

## Continuación después del reinicio y resultado Q35-07

El intento 07 terminó correctamente como medición válida de calidad, no como infraestructura: 131.072 tokens de contexto, prompt efectivo de 125.135 tokens, 618 tokens de salida, `finish_reason=stop`, prefill 3.456 tok/s y decode 151,6 tok/s. El holdout exacto dio **0/8 (0%)**. Es una medición negativa de recuperación para esa corrida; no respalda que aumentar el contexto mejore calidad y no es una comparación de velocidad contra otro perfil. El cgroup reportó 0 bytes de swap y no tuvo OOM.

El supervisor avanzó al seed `131072:2026102`, pero el runner lo detuvo antes de lanzar un servidor o enviar request: el bind de preflight a 8350 recibió `EADDRINUSE`. El muestreo final del seed anterior registró grupo de procesos vacío, Strata informó `stopped`, y la inspección tras el evento no encuentra proceso de inferencia ni listener. La implementación Linux del servidor Strata permite reutilizar el puerto; el preflight del runner no configuraba `SO_REUSEADDR`. Un test CPU-only reproduce un TCP `TIME_WAIT` tras cerrar limpiamente una solicitud y demuestra el falso positivo; otro confirma que un listener real sigue bloqueando el puerto.

Se añadió `assert_port_bindable()` en el runner de Q35 con `SO_REUSEADDR` y las dos regresiones correspondientes. La suite CPU-only pasa **22/22** y `py_compile` pasa. No se tocó el producto, los pesos, los perfiles protegidos ni la configuración del modelo. La recuperación `131072:2026102`, intento 02, está prerregistrada y sólo se habilita tras un preflight fresco de procesos/listener, memoria, PSI, disco, hashes y ambas GPU. Ante otro fallo de infraestructura se detendrá el supervisor para diagnóstico; no hay reintento automático. Si el seed da una respuesta válida, el supervisor prosigue el barrido Q35 restante en serie como fue registrado originalmente.

Evidencia de la corrida y el preflight fallido preservada en `receipts/progress-after-attempt-07-before-recovery.json` y `receipts/attempt-07-seed2-preflight-failure/`; nuevo registro en `receipts/q35-port-timewait-fix-and-attempt-08-preregistration.json`.

### Enmienda preregistrada · continuar tras una salida truncada pero completa

Q35-08 procesó el seed 2 y el supervisor avanzó. Q35 seed 3 ahora tiene una respuesta HTTP 200 completa, modelo cargado, 125.113 tokens de prompt (≥95% de 131.072), sin error de transporte ni aborto del monitor, pero agotó el mismo máximo de 768 tokens (`finish_reason=length`, 0/8); por eso el runner lo clasificó `incomplete` y el supervisor pausó por el código de salida. El experimento no debe repetir ese seed.

En `receipts/q35-continue-after-quality-negative-preregistration.json` se registra tratar toda respuesta completa como resultado terminal del fixture, aunque sea negativa/incompleta, sólo si `request_sent=true`, modelo cargado, HTTP 200, prompt ≥95% del contexto, cuerpo presente, `finish_reason` `stop` o `length`, sin error de transporte ni aborto del monitor. El supervisor podrá continuar con el siguiente fixture en serie, manteniendo idénticos pesos, prompt, sampling y `max_tokens=768`. Un fallo de infraestructura, guard, hash/config, servidor/puerto o request ausente seguirá deteniendo la matriz. El próximo material es `262144:2026101`; 131072/2026103 no se repetirá.


## Cierre de campaña Q35 · 2026-10-22

Q35 terminó su matriz de 4 contextos × 3 seeds bajo el supervisor de system manager. La tercera corrida 1M/seed3 acabó sin error; se cerró el listener y el cgroup quedó sin worker. El regrade preregistrado corrige la métrica original de JSON no solicitado; los siete outputs completos son 8/8 semánticos, y los cinco outputs truncados siguen parciales. La recomendación final es conservar 131K como default y permitir más contexto sólo cuando el prompt lo requiera, dado el coste observado a 1M. El barrido no se repite. La lista priorizada no tiene otra inferencia habilitada hasta que cambie una condición externa o exista un artefacto/claim nuevo. Ver `RESULTS.md` y `receipts/q35-matrix-final-decision.json`.