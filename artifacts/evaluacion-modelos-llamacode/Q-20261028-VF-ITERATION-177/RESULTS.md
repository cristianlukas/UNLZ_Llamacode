# Q177 — Revalidación de gates IA y reconciliación de estado

**Estado:** auditoría completada; no se inició una prueba de inferencia ni se usó GPU. Los gates abiertos siguen sin habilitar una comparación de calidad/velocidad en Linux.

## Hallazgos

1. **Strata · Qwen3.6-35B-A3B:** el issue oficial #3294 continúa `Open` al 2026-10-28. El caso descrito mantiene el modelo en GPU0 y deja GPU1 ociosa; el issue solicita implementar layer split en la ruta `src/qwen35/q36_engine.cu`. Un ensayo single-GPU no responde al caso dual de las dos RTX 3090. No se inició descarga, build ni benchmark.
2. **P2.1 · autorización MCP:** el código actual sí crea `localPrincipal(home,cwd)` en `LlamaAgentBackend`, lo propaga al worker/`AgentToolRunner`/`McpClient` y lo envía como `io.llamacode/principal` en `_meta`. Esa identidad local no es una identidad tenant autenticada ni prueba que el servidor MCP la valide. `ToolExecutionSafety` permite únicamente workspace con coincidencia exacta, deniega `scope=tenant` y bloquea selectores tenant/org en argumentos. Las pruebas existentes validan el helper; no prueban autorización del servidor ni side effects cross-tenant. P2.1 permanece fail-closed y bloqueado hasta que exista proveedor confiable y policy real del servidor.
3. **Cola:** el inbox conserva 69 entradas con resultado registrado; el ledger contiene 36 accionables. Las entradas que siguen abiertas requieren condiciones externas documentadas (Windows nativo, identidad/policy tenant, workflow/holdout, transcripción primaria, cambio reproducible de parser/runtime, target real con oráculo o evento de presión real). No apareció una prueba IA local nueva que pueda cambiar una decisión sin esas condiciones.
4. **Preflight:** no se detectó proceso/listener de inferencia de modelos. Hay procesos/puertos de PeritoSoft/Electron que no corresponden a un endpoint de inferencia; no se enviaron señales ni se inició carga. La utilización instantánea de GPU no se usó como proxy de servidor.

## Decisión y reanudación

No se repitieron benchmarks cerrados ni se inventaron pruebas para superar gates externos. El registro MCP se corrigió para distinguir principal local de principal tenant y la fuente Strata se revalidó. Reabrir solo cuando cambie el estado upstream/runtime, aparezca la policy real del servidor, llegue la fuente primaria/fixture, o se disponga del host/target requerido.

**Sin cambios** en perfiles, pesos, modelos, parámetros productivos ni datos de PeritoSoft.

## Evidencia

- `receipts/strata-issue-3294-revalidation.json`
- `receipts/p2.1-current-code-audit.json`
- `receipts/inference-server-preflight.json`
- `receipts/google-sheet-q177-reconciliation.json`
- `receipts/prewrite-snapshot/`
