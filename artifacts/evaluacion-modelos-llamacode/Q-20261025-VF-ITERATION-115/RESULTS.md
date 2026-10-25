# Q115 · Límites exactos del warning de PSI moderada · 2026-10-25

## Resultado

**Q115-A1: 2/2 PASS** sobre el `check_gates`/`record_sample` activo de Q97, con fixtures CPU y sin consultar GPU. En cada check se probaron 30 muestras consecutivas, sin sleeps ni asignación de memoria; `gpu_snapshot` representa dos RTX 3090 sólo como fixture.

- PSI global `full=20,00%`: no avisa en muestras 1–29 y avisa en la 30. `full=19,99%`: no avisa tras 30.
- PSI global `some=70,00%`: no avisa en muestras 1–29 y avisa en la 30. `some=69,99%`: no avisa tras 30.
- Ninguna condición alcanzó los hard-stops severos.

El recibo histórico Q97 se cotejó: define warning inclusivo `full avg10 >=20%` o `some avg10 >=70%` durante 30 muestras. Q113 ya probó la ruta full moderada al 46,52%; Q115 cierra las dos fronteras exactas y la rama some. Q114 cerró el caso de PSI cgroup diagnóstica.

## Decisión y límites

La lógica de aviso moderado del detector activo se comporta según la política: el aviso aparece sólo cuando la PSI **global** alcanza el límite durante 30 muestras; valores inmediatamente por debajo no avisan. Esto no detiene la inferencia. Junto con Q113/Q114, los gates de memoria activos quedan cubiertos por fixture replay. No se cambian threshold, RAM, swap, contexto, ASTRA, SOL o Flash-Next.

Esto no es una prueba de inferencia ni una carga real con VRAM/KV/concurrencia, y no determina la causa del cierre de Codex. No hay nuevo A/B de modelo habilitado bajo Linux mientras los gates externos de la cola sigan pendientes; cuando se habilite, la comparación respetará la configuración del usuario de 2×RTX 3090 y 128 GiB.

Artefactos: `PLAN.md`, `runner/test_q115_warning_thresholds.py`, `receipts/preregistration.json`, `receipts/q115-warning-boundaries.json`, `receipts/q115-final-summary.json`, `receipts/sheet-preregistration-readback.json`.
