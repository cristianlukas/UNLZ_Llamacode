# Q109 · Integración live del guard estricto

**Estado:** PASS 8/8 CPU-only.
**Lock:** Q-20261024-VF-ITERATION-109 (`a58e3117-4c47-49a1-9110-5c189c287a25`).
**Prueba:** 2026-10-24 23:57:44 UTC.

## Resultado

El core candidato Q108 leyó telemetría real de `/proc` durante tres ciclos. MemAvailable pasó de 109.843 a 109.691 GiB; PSI some/full se mantuvo en 0%, OOM=0. En los tres ciclos devolvió `continue`, sin aviso ni stop, y el hijo candidato normal siguió vivo.

En la segunda fase, el lector apuntó a una raíz procfs deliberadamente inexistente. El core fail-closed escribió la razón `memory telemetry unavailable` y envió SIGTERM sólo al PID candidato asignado (`exit=-15`). Un segundo hijo sleep de control siguió vivo hasta la limpieza del runner. No hubo incremento del contador global OOM ni archivos de stop para la fase normal. Los dos hijos propios quedaron recolectados.

## Cómo responde a la duda del detector

ASTRA DEFAULT/Flash-Next 1M y SOL Q34 TP=2 son controles reales exitosos: no fueron interrumpidos por el guard recalibrado. Q103 ya sometió el guard anterior a 56 GiB de RSS durante 12 s, alcanzando VmHWM 56.013 GiB con MemAvailable mínimo 53.386 GiB, sin stop ni OOM. Q109 valida que el core estricto corregido se conecta a `/proc` real, continúa en estado sano y falla cerrado ante telemetría faltante. No repetí la asignación de 56 GiB: la evidencia ya existe y el margen de commit en este host era menor a 30 GiB.

Los umbrales no cambiaron: RSS alto por sí solo no detiene; MemAvailable <32 GiB, OOM nuevo o PSI global severa sostenida pueden detener el candidato; PSI moderada sólo avisa. Esta comprobación no prueba resistencia de un modelo ni predice cierres de Codex/GUI/driver. No hubo inferencia, servidor, GPU, carga artificial, cambio de cgroup/sysctl, límite RAM ni modificación de ASTRA/SOL/Flash-Next/PeritoSoft.

## Próximo paso

Integrar `read_host_sample/monitor_once` en el launcher de la próxima evaluación que cumpla sus dependencias y conservar el guard del PID de esa evaluación. Las pruebas de modelos pendientes siguen condicionadas por Windows nativo, un backend/fixture tenant, un cambio parser/runtime reproducible o una fuente primaria verificable.
