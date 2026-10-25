# Q113 · Replay completo del guard activo de memoria · 2026-10-25

## Resultado

**Q113-A1: 7/7 PASS** sobre el código activo de Q97 (`check_gates` → `record_sample` → `pressure_gate_transition`), que Q100 reutiliza. El replay usó señales fixture y CPU; la consulta de GPU fue mockeada. No arrancó modelo/servidor, no usó GPU, no construyó el proyecto y no reservó RAM artificial.

La prueba leyó recibos históricos antes de aplicar el guard: ASTRA DEFAULT 1M completó 10/10 con proceso de hasta 51,14 GiB RSS, MemAvailable mínima 55,728 GiB y OOM=0 en el resumen Q102; el recibo Q97-Q14 registra 51,14 GiB RSS, 55,64 GiB disponibles y OOM=0. Con la muestra fixture de MemAvailable=55,728 GiB, el guard activo continuó. El código de `record_sample`/`check_gates` no toma RSS como entrada ni como criterio de parada.

## Comprobaciones ejecutadas

- ASTRA 1M con la disponibilidad registrada, continúa aunque el RSS histórico sea ~51 GiB.
- PSI global full=46,52% sostenida: avisa a partir de la muestra 30; no detiene.
- MemAvailable exactamente 32,00 GiB continúa; 31,99 GiB detiene.
- Incremento de `oom_kill` global, `memory.events:oom` o `oom_kill` del cgroup detiene.
- PSI global full≥60% o some≥80% detiene en la muestra consecutiva 15, no en la 14.
- Una muestra normal reinicia la racha severa; luego some≥80% detiene en 15.
- SOL Q34 TP=2 en ambas RTX 3090 permanece como control histórico: terminó sin OOM; no tiene serie PSI continua y por eso no calibra esos límites.

## Incidencia del runner

La primera invocación de Q113 terminó en preflight con cero escenarios ejecutados: comparaba el mapa de dos hashes activos contra el manifiesto completo de ocho fuentes. La auditoría independiente confirmó que los ocho hashes preregistrados coincidían. En la enmienda 02 se corrigió el runner para comparar el mapa completo; el segundo intento pasó 7/7. La incidencia y la lectura de vuelta de Sheets están registradas en `receipts/q113-attempt01-runner-preflight.json` y `receipts/sheet-preregistration-readback.json`.

## Decisión y alcance

La evidencia apoya la observación del usuario: **ocupación/RSS alto por sí solos no activan la política vigente**. No se cambian umbrales, RAM, swap, contexto, ASTRA, SOL ni Flash-Next. El detector distingue advertencia de presión moderada y parada por poca memoria disponible, OOM nuevo o PSI global extrema sostenida.

El replay verifica las transiciones del código con fixtures; no es una nueva carga de 1M ni reproduce VRAM/KV/concurrencia. La corrida SOL demuestra finalización/no-OOM, pero su PSI no quedó muestreada por segundo. Tampoco determina por sí solo la causa del cierre de Codex: el monitor supervisa campañas, no el proceso de escritorio/driver en general. La causa de ese cierre continúa sin atribución concluyente.

## Preregistro y artefactos

- `PLAN.md`
- `runner/test_q113_active_guard.py`
- `receipts/preregistration.json` (enmiendas 01 y 02)
- `receipts/q113-active-guard-audit.json` (7/7)
- `receipts/q113-attempt01-runner-preflight.json` (preflight abortado, cero checks)
- `receipts/sheet-preregistration-readback.json`
