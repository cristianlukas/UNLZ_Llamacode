# Q109 · Integración live del guard estricto

**Estado:** cerrada PASS 8/8; preregistrada antes de ejecución y resultado leído de vuelta en `Evaluaciones LlamaCode!A329:J329`.
**Lock:** `Q-20261024-VF-ITERATION-109`, token `a58e3117-4c47-49a1-9110-5c189c287a25`.

## Pregunta

¿El core candidato de Q108 opera con telemetría real de `/proc` y protege sólo el PID candidato asignado, sin falsos cortes cuando el host reporta presión normal?

## Hipótesis y controles

- La lectura real de MemAvailable/PSI/OOM debe producir `continue` bajo el preflight actual.
- Tres muestras live de un proceso `sleep` propio deben dejarlo vivo y no crear stop reason.
- Si se simula telemetría ausente mediante una raíz procfs temporal vacía, `monitor_once` debe terminar sólo el hijo candidato designado; un hijo control debe seguir vivo.
- ASTRA DEFAULT 1M y SOL Q34 quedan como controles históricos exitosos. Q103 ya ejecutó 56 GiB CPU RSS (VmHWM 56.013 GiB, 12 s, MemAvailable mínima 53.386 GiB, sin OOM). No repetir esa carga: Q109 comprueba el camino de integración estricto y no añade una asignación de memoria.

## Alcance y gates

- Sólo CPU, un muestreo live de `/proc`, dos procesos hijos inocuos y señal al PID hijo creado por la prueba.
- Sin servidor, prompts, modelo, GPU, build, alteración de límites, escritura en rutas del usuario ni cambios a umbrales.
- Antes de correr: confirmar lock Q109, telemetría completa, decisión base sin stop, raíz de corrida inexistente y preregistro/readback exacto de la fila Q109 en Sheets.
- Criterios de PASS: live sample completo; 3/3 ciclos válidos continúan con el candidato normal vivo; telemetría ausente da razón explícita y termina al candidato asignado; proceso control permanece vivo; OOM sin delta; clean-up de los dos hijos propios.
- Si la presión de host ya exige stop antes del test, o falta/malforma telemetría real, registrar gate abortado y no crear el primer hijo.

## Artefactos

- Runner: `runner/q109_live_guard_integration.py`
- Preregistro y resultado: `receipts/`
- Resultado de corrida: `runs/live-guard-integration-01/`
