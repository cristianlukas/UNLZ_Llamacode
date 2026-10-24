# Q108 · Auditoría independiente del guard de memoria y conciliación de pruebas

**Estado:** activa; revisión CPU/read-only, sin inferencia ni cambios de umbral.
**Lock exclusivo:** `Q-20261024-VF-ITERATION-108` (token en `WORK_QUEUE.lock`).
**Fecha:** 2026-10-24.

## Pregunta

¿Los recibos muestran que el guard confundió RSS/uso alto con presión y detuvo o habría detenido ASTRA DEFAULT 1M o SOL? ¿Los umbrales reflejan los monitores registrados? ¿La acción de integración E2E de Strata sigue pendiente después de Q100/Q105?

## Prerregistro

Auditoría independiente de artefactos ya existentes, antes de cualquier nueva carga de modelo: releer y validar aritméticamente los recibos originales de ASTRA 1M (10/10; árbol RSS ~51.14 GiB; MemAvailable mínima ~55.728 GiB), SOL Q34 (TP=2 exitoso; sin serie PSI, límite explícito de evidencia), Q97/Q98/Q99/Q100 (avisos PSI moderados, MemAvailable por encima del piso, OOM=0 y tareas terminadas), Q102 replay de guard (19/19), Q103 smoke CPU (RSS 56.013 GiB, MemAvailable mínima >53 GiB, sin stop/OOM), y las implementaciones Q102/Q103. No ejecutar modelo, servidor, GPU ni presión artificial.

Verificar en cada registro la condición de decisión: `MemAvailable <32 GiB`, incremento de `oom_kill`, o PSI global severa sostenida por 15 muestras; el RSS por sí mismo no es entrada del guard. Confirmar que PSI moderada sólo avisa. Recalcular los casos conservados y marcar cualquier discrepancia como fallo. Separar evidencia de SOL sin PSI continua de la calibración PSI; no inferir telemetría ausente.

Inspeccionar la acción `f318d34d-eefc-4d16-b77d-98b1977d0698`: comparar su estado con Q100 (integración real de `LlamaAgentBackend`, tres semillas, 3/3 serial vs 1/3 parallel2) y Q105 (forensics CPU). Si confirma ejecución, reconciliar estado local/Sheet como completado sin adopción; no repetir inferencia.

## Criterio de salida

PASS si todos los recibos son consistentes y ningún control exitoso histórico recibe `stop`; SOL queda señalado como prueba de éxito/no-OOM pero sin calibración PSI continua; el estado de la acción Strata coincide con Q100/Q105; se conservan ASTRA, SOL, Flash-Next y PeritoSoft. Si aparece discrepancia, abrir una enmienda/retest CPU preregistrado antes de recomendar cambios.

## Siguiente prueba elegible

No iniciar otro A/B de modelo hasta que cambie una condición material. La cola vigente deja pendientes con dependencias externas: NInfer/Job Objects requiere Windows nativo; HyperQwen requiere defecto reproducible y cambio del parser/runtime; autorización tenant requiere backend/fixture concreto; orden de validación requiere caption/transcripción primaria. Estos bloqueos se revisarán después de la auditoría y se anotarán con condición verificable.


## Enmienda 01 · datos PSI/OOM ausentes o inválidos

La revisión de código localizó un borde no cubierto por los casos históricos: el parser PSI puede devolver `{}` y el evaluador interpreta métricas ausentes como cero; `read_oom()` también devolvía 0 si faltaba el contador. Esto no ocurrió en ASTRA 1M, SOL ni los monitores Q97–Q103, cuyos recibos tienen métricas, y no explica ningún crash previo. Antes de ejecutar el test, se amplía el prerregistro: reproducir el comportamiento anterior con entradas ausentes/malformadas y probar un core de monitor Q108 que rechace esas lecturas con una razón explícita y detenga sólo el PID candidato. No cambiar los thresholds de presión ni reconstruir el guard de históricos; no inferencia, GPU ni reserva artificial de RAM. Casos válidos ASTRA/Q100/límites deben seguir dando el mismo resultado.


## Enmienda 02 · una muestra de telemetría real /proc

Antes del cierre, ampliar la auditoría a una lectura de solo lectura de `/proc/meminfo`, `/proc/pressure/memory` y `/proc/vmstat` del host actual para verificar la integración del parser con sus formatos reales. Inyectar fixtures temporales para los mismos parsers y asegurar fallo explícito si desaparece un archivo. La muestra real no enviará señales ni empezará un proceso candidato; no se reserva RAM, no se inicia un modelo/servidor, no se usa GPU y no se cambian umbrales.
