# Q170 — Auditoría de pruebas pendientes en inbox, accionables y Sheet

Fecha: 2026-10-27. Se reutilizó el lock paraguas Q146. Se leyeron AGENTS.md, README.md, WORK_QUEUE.md y WORK_QUEUE.lock antes de esta auditoría. No se hizo build, benchmark, descarga ni uso de GPU.

## Estado reconciliado

El inbox contiene 58 entradas: 57 URLs (las 56 fuentes originales más la planilla añadida después) y un pedido de texto sobre ampliar el contexto. La app tiene 35 accionables locales; los 35 IDs existen en la pestaña Accionables. La planilla contiene 9 filas adicionales: ocho registros históricos/modelo y un seguimiento público de R36S que no es una prueba de modelos. No quedó un accionable de modelo oculto sólo en la pestaña.

## Gates que mantienen pruebas pendientes

- NInfer Flash-Next C39-02 y Job Objects/entrypoints Windows requieren una sesión Codex nativa de Windows; este executor es Ubuntu.
- La prueba cross-tenant requiere que el host transmita un principal autenticado no falsificable y que exista una policy real por recurso.
- Harness² no tiene aún un workflow de LlamaCode ni un holdout fijo que responda una pregunta de calidad local.
- El fixture de validación de pedidos espera una caption/transcripción primaria atribuible de la fuente #36.
- El A/B híbrido #20/#21 requiere proveedor y modelo fijados, keyRef autorizada, tope de gasto y frontera de datos.
- Q119 requiere una traza real de presión crítica o un cambio explícito de política; no se genera presión artificial.
- La comparación Qwen/Ghidra específica de R36S requiere un target real o abierto con SHA, inputs, oracle/tests/CRC y revisión humana.

Swift Q72/Q97 y PLE Q20/Q22 ya cerraron sus gates de calidad; la declaración del usuario sobre uso no comercial no cambia esos resultados. HyperQwen sigue sin defecto local reproducible según Q104. El inventario del Sheet marca UD-IQ4_XS como retirado Q151 y con 0 bytes, por lo que no se restaura ni descarga contra la decisión de retención.

## Resultado

No se ejecutó un modelo porque no hay un benchmark justificado que esté habilitado en esta sesión bajo los gates actuales. ASTRA Flash-Next RCO IQ2_XS, SOL y los datos/configuración de PeritoSoft permanecen intactos. La revalidación de la fuente #14 y su fila del Sheet están en Q169.

La evidencia completa, incluidos IDs reconciliados y gates por actionable, está en receipts/pending-gates-audit.json.
