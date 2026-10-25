# Q120 · reconciliar el candidato AMD05 con la preocupación de presión · 2026-10-25

**Estado:** Cerrada · lock `e84d0d6d-b773-4416-89e2-1c223d8d3c91`

## Pregunta

¿Queda pendiente volver a probar en CPU un guard que acumule PSI severa compuesta y headroom bajo, usando ASTRA 1M exitosa como control, o esa combinación ya fue verificada?

## Alcance

Auditoría read-only de artefactos existentes. No iniciar otra carga de memoria, modelo, servidor, build, GPU o red; no cambiar Q97/Q100 históricos, AMD05, umbrales, RAM, swap, ASTRA, SOL ni producción. Antes de repetir pruebas, comparar helper, runner, fixtures y traza por hashes.

## Evidencia preexistente a reconciliar

- Q97 es el guard histórico con contadores severos independientes `full` y `some`; Q116 demostró el falso negativo al alternar dimensiones cuando se interpreta como persistencia del OR por muestra.
- AMD05 (`q117_pressure_guard_attempt05.py`) ya usa `severe_any = full>=60 OR some>=80`, lo combina con `MemAvailable <48 GiB` por 15 muestras, y mantiene el piso inmediato de 32 GiB/OOM.
- La suite CPU AMD05 ya cubre la alternancia, headroom alto/bajo, ASTRA con RSS alto, piso de memoria, OOM y fallos de telemetría; 21/21 PASS.
- Q118 ya procesó de nuevo la traza real de ASTRA DEFAULT 1M con ese módulo exacto: 707 muestras y 12/12 PASS; RSS 51,306 GiB, MemAvailable mínimo 58,698 GiB, sin stop/OOM/swap.

## Regla para no duplicar

No volver a ejecutar el mismo helper, fixtures o traza si los hashes y resultados existentes coinciden. Cerrar como auditoría de reconciliación; dejar pendiente sólo comprobar que una futura corrida nueva importe/use AMD05 o un sucesor equivalente **antes** de iniciar inferencia/GPU. Mantener explícito que Q97/Q100 históricos no se reescriben.
