# Q61 — Resultado: evidencia de cierres de Codex

**Estado:** auditoría local completada; causa probable identificada, causalidad de los cierres repetidos aún no demostrada.
**Lock:** `57f4b70c-b33f-4c99-8c9f-2784a8d8ef9e`
**Observado:** 2026-10-23T15:00:12Z

## Hallazgos

- Crashpad de `~/.config/Codex/Crash Reports` tiene un registro `capture_kind=crash`, `ptype=gpu-process` del 2026-10-22 22:20:53 (-03:00). Hay dos registros posteriores `dump_without_crashing` del subproceso GPU (22:39:46 y 2026-10-23 08:47:17 -03:00); esos dos no prueban que el proceso se haya caído.
- En el directorio sólo aparecen sidecars `.json` y metadatos `.meta`; no hay minidump para inspeccionar el stack. `coredumpctl` no está instalado, así que no se pudo corroborar un core del proceso principal.
- El proceso principal `ChatGPT` seguía vivo en el recheck y figura iniciado el 2026-10-22 22:28 (-03:00). Esto no descarta cierres anteriores, pero el registro disponible apunta a un proceso GPU hijo, no a un crash probado del proceso principal.
- `systemd-oomd` sólo registra su arranque. La búsqueda del journal de este boot no encontró OOM kill, `segfault` ni `general protection` que identifique Codex.
- El kernel registró un NVIDIA Xid 31/MMU fault de un proceso `python3` el 2026-10-22 22:36 (-03:00); no hay evidencia suficiente para identificar qué trabajo lo originó ni asociarlo a Codex.
- Después de instalar NVIDIA 615.71.09, el kernel registró repetidos `API mismatch`: procesos `qml`/`nvidia-smi` usan librerías 615.71.09 mientras el módulo activo sigue en 610.57.04. `nvidia-smi` continúa fallando. El arranque es anterior a la actualización.

## Decisión

La explicación mejor apoyada para investigar primero es una falla de la ruta gráfica/GPU, agravada actualmente por el desajuste entre módulo y librerías. **No** hay evidencia de presión de memoria ni de que `systemd-oomd` esté cerrando Codex; no corresponde bajar memoria ni contexto. El registro de Crashpad es de un hijo GPU y no demuestra que ese evento explique todos los cierres.

La mitigación siguiente es reiniciar Ubuntu después del update y verificar que módulo y NVML coincidan antes de volver a usar GPU. Si Codex vuelve a cerrarse con el driver alineado, capturar el minidump/stack del evento nuevo y correlacionar su hora; no aplicar flags de aceleración ni cambiar políticas del sistema sin esa evidencia.

## Límites

No hubo cambios de configuración, reinicio, servidor de inferencia, request, benchmark, build ni uso de GPU. La ausencia de coredumps no demuestra que nunca hayan ocurrido: esta instalación no tiene `coredumpctl`, y los registros Crashpad hallados no incluyen minidumps.
