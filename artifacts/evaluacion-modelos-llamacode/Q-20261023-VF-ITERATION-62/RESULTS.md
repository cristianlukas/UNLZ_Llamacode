# Q62 — Resultado de factibilidad P2.1

**Estado:** auditoría estática completada; P2.1 se mantiene condicionado a una integración de tools concreta.
**Lock:** `1b64d03d-e61f-46b7-9a04-3a955d3c98a9`
**Cierre:** 2026-10-23T15:06:48Z

## Hallazgos

- Q29 y Q32 evaluaron el comportamiento del modelo con `tool-eval-bench` contra `llama-server`/NInfer por HTTP directo. El runtime LlamaCode no participó; sus errores TC-74/84/92 son fallos del candidato en el harness, no regresiones probadas del ejecutor de herramientas de la app.
- LlamaCode sí contiene `ToolExecutionSafety` para contratos MCP conservadores, aprobación de escrituras externas y verificación posterior; además, `AgentContext` declara un presupuesto de concurrencia cuyo valor inicial es 1. Los módulos revisados no definen una identidad tenant ni un servidor de negocio donde aplicar el filtrado server-side recomendado. La autorización efectiva de una herramienta externa debe implementarse en su servicio/MCP propietario.
- La recomendación P2.1 sigue siendo válida **para un piloto que use una API multitenant real**: autorizar cada operación según la identidad autenticada en el servidor, imponer prerrequisitos/orden en los efectos y verificar el commit antes de notificar. Sin ese contrato no hay una implementación genérica de LlamaCode que esta evidencia justifique.
- No se ejecutó un test CPU de producto ni se editó código: el objetivo de esta auditoría era distinguir si existía una prueba de modelo/bug de app ejecutable ahora. La conclusión es que no; reabrir Qwen requiere cambio material y un holdout de integración concreto. El driver NVIDIA desalineado mantiene bloqueadas las pruebas GPU actuales.

## Reconciliación

El accionable local `vf-qwen-tool-safety-gates-20261022` se precisó y guardó con backup. En Google Sheets se completó la fila 7 de **Accionables** (antes sólo tenía tipo e ID), con estado, diseño, decisión, artefactos y evidencia. El API devolvió los valores escritos, `WRAP`/alineación superior y altura de fila 160 px. Sin render visual porque no se abrió una pestaña de Sheets.

## Evidencia

- Q29 `PLAN.md` y `RESULTS.md`; Q32 `scripts/run_ninfer_quality.py` y `RESULTS.md`.
- `src/core/agent/ToolExecutionSafety.h`, `src/core/agent/AgentTypes.h` y `tests/test_tool_execution_safety.cpp`.
- Receipt estático: `receipts/p2-safety-feasibility-audit.json`.
- Recepción Sheet: `receipts/google-sheet-p2-safety-row.json`.

## Siguiente paso

1. Para volver a probar calidad de Qwen con tools, cambiar materialmente el protocolo o conectar una integración real con tenant y permisos verificables; preregistrar sus regresiones antes de reabrir el modelo.
2. Para la cola prioritaria de inferencia, reiniciar Ubuntu después de instalar NVIDIA 615 y pasar el preflight de NVML/módulo; el A/B Flash-Next Windows queda en Windows nativo y Swift espera elegibilidad comercial.
