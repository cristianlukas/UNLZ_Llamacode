# Presupuestos de razonamiento Qwen

Fecha: 2026-09-08

La recomendación evaluada propone mantener `reasoning_effort=medium` y limitar el presupuesto de thinking según la dificultad. Esto evita que Qwen3.8 convierta tareas simples o ciclos repetitivos del agente en deliberaciones muy largas. El presupuesto sólo se aplica cuando el interruptor global de thinking de LlamaCode está activado; no fuerza razonamiento en consultas simples.

## Política aplicada

| Perfil | Presupuesto | Motivo |
|---|---:|---|
| ASTRA | 8192 tokens | Qwen Next para problemas largos y planificación compleja |
| SOL | 4096 tokens | Coding difícil, revisión y refactorización |
| TERRA | 2048 tokens | Default diario; suficiente para coding normal sin overthinking |
| LUNA | ilimitado | Mantiene su comportamiento histórico de razonamiento |
| METEOR | ilimitado | Perfil de throughput; no se cambia sin una medición específica |

La política se envía por request desde el harness mediante `reasoning_budget`; no se limita sólo la salida del servidor. En los tres perfiles Qwen principales de Ubuntu también se agregó `--reasoning-budget-message "ok now"`, que permite al template retomar la respuesta cuando alcanza el límite. El esfuerzo permanece en `medium`. Si thinking está apagado, el harness sigue enviando presupuesto cero, como corresponde.

Windows no fue modificado: los presupuestos y el mensaje quedaron en la sección `platformArgs.linux` o en la política de lanzamiento común que ya usa el harness, por lo que el ejecutable y los argumentos Windows existentes se conservan.

## Criterio de uso

- Para tareas triviales o automatizaciones muy repetitivas, 512–1024 tokens puede ser una variante futura de benchmark, no el default.
- Para el uso diario de LlamaCode, TERRA queda en 2048.
- SOL y ASTRA conservan margen para tareas que requieren verificación; el presupuesto no garantiza calidad si el contexto o el harness son incorrectos.

La implementación usa las capacidades ya existentes de LlamaCode (`reasoningBudget`, `reasoningEffort` y `reasoning_budget` en el request), sin introducir un flag nuevo en C++.
