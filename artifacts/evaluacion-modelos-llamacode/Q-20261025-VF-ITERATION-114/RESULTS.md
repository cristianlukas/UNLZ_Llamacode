# Q114 · PSI del cgroup alta frente a PSI global moderada · 2026-10-25

## Resultado final

**Q114-A1, replay enmendado: 2/2 PASS.** Se invocó el `check_gates`/`record_sample` activo de Q97 con fixtures, en CPU. `gpu_snapshot` se mockeó con dos RTX 3090 para reflejar el host sin consultar NVML. No se inició modelo/servidor, no hubo inferencia, GPU, build, red ni asignación artificial de memoria.

1. Con MemAvailable=71,864 GiB, OOM=0, PSI global=0% y PSI cgroup some/full=81,53%, 30 muestras consecutivas continúan sin warning ni stop. El registro conserva la señal cgroup, pero ésta no activa un gate por sí sola.
2. Con PSI global some/full=34,72% y la misma cgroup=81,53%, el guard no avisa en las muestras 1–29; avisa en la 30 y no hace hard-stop. El aviso deriva de PSI **global** moderada; el cgroup permanece diagnóstico.
3. El recibo histórico Q97 confirma picos separados: cgroup full=81,53%, PSI global full=34,72%, MemAvailable mínima=71,864 GiB, OOM=0. No se afirma que los picos hayan ocurrido al mismo tiempo.

## Calidad del experimento

El primer intento pasó 2/2, pero el caso cgroup-only usó una sola muestra y no cubría la ventana de 30 muestras. No se usó como evidencia final. La enmienda 01 se leyó de vuelta en Sheets y amplió el caso a 30 muestras con PSI global=0; la segunda corrida pasó 2/2 con esa cobertura. Ver `receipts/q114-attempt01-short-diagnostic-window.json` y el recibo final `receipts/q114-cgroup-psi-replay.json`.

## Interpretación

Junto con Q113 (7/7), la prueba respalda la calibración que señaló el usuario: ASTRA DEFAULT 1M con ~51,14 GiB RSS y más de 55 GiB disponibles no debe detenerse por RSS; tampoco debe tratarse la PSI alta del cgroup como si fuera presión global. El guard avisa por PSI global moderada sostenida y reserva el stop para MemAvailable<32 GiB, OOM nuevo o PSI global severa sostenida según los límites Q97. SOL TP=2 terminó sin OOM en ambas RTX 3090, pero su campaña no guardó PSI continua.

Esto verifica sólo la decisión del guard de campañas mediante fixture replay; no genera una carga real de modelo ni atribuye el cierre de Codex. La causa de ese cierre sigue abierta. No se cambian umbrales, RAM, swap, contexto, ASTRA, SOL ni Flash-Next.

## Siguiente condición

Los benchmarks de modelo pendientes siguen condicionados a sus requisitos externos (Windows nativo/Job Objects, principal+policy tenant u otro fixture/workload habilitado). No se los sustituye por un benchmark incompatible de una GPU; cuando se habilite un A/B de modelos, se conservará tu configuración de 2×RTX 3090 y 128 GiB.

Artefactos: `PLAN.md`; `runner/test_q114_cgroup_psi_diagnostic.py`; `receipts/preregistration.json`; `receipts/q114-cgroup-psi-replay.json`; `receipts/q114-attempt01-short-diagnostic-window.json`; `receipts/sheet-preregistration-readback.json`.
