# Q157 · Recheck de PeritoSoft y barreras para reanudar evaluaciones

Fecha local: 2026-10-26. Lock umbrella: Q146 (`2242863e-c78e-4fa9-9649-c1d1541f3919`).

## Objetivo

Con la autorización explícita del usuario, comprobar si PeritoSoft o sus LlamaServers están activos y detener sólo esos procesos. Después, identificar el próximo test de IA justificable según WORK_QUEUE/actionables y su condición de ejecución.

## Reglas

- No terminar aplicaciones ajenas ni perfiles productivos ASTRA/SOL.
- No repetir pruebas cerradas sin cambio de artefacto, protocolo o gate.
- Mantener los gates que el usuario dejó pendientes para Windows nativo.
- No iniciar inferencia si los candidatos están retirados o la prueba no puede cambiar una decisión.

## Preflight y cierre

Leer `AGENTS.md`, `README.md`, `WORK_QUEUE.md` y `WORK_QUEUE.lock` antes de cualquier edición o uso de GPU. El lock vigente pertenece a Q146.
