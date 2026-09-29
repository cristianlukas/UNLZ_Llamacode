# Registro LC-H1 Genesis — 2026-09-29

Corrida realizada con el harness real de agentes de LlamaCode, `agent-maximo`, 1 pasada, timeout de 1800 s, modo `agent`, build de daemon de pruebas aislado y dos RTX 3090 despejadas.

## Resultados

| Suite | Puntaje | Tiempo | Resultado |
|---|---:|---:|---|
| HumanEval 1 | 1/1 | 27.074 s | Aprobado |
| HumanEval 20 | 20/20 | 758.772 s | Aprobado; sin reparación |
| BigCodeBench-Hard 8 | 2/8 | 417.406 s | Gate fallido por calidad |
| Intelligence Adversarial v1 corregida | parcial, cancelada en prompt 3/10 | — | Sin puntuación; no comparable |

Huella de configuración: `1959e22a888a4a2c8979bbacf92c43b0c11505b2f4ad00299572dd43d636c594`.
Huella LC-H1: `sha256:cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef`.

## Contenido

- `benchmark-runs/`: carpetas completas de cada corrida, metadatos, resultados por tarea y workspaces del agente. ADV contiene el estado parcial guardado al cancelar.
- `lch1-inputs/`: definiciones exactas de HE0, HE20, BCB8 y ADV10 utilizadas.
- `runtime/benchmark-results-all.json`: resultados almacenados por el daemon de LlamaCode.
- `runtime/server-log.json` y `runtime/agent-log.json`: logs preservados al detener la corrida.

ASTRA y SOL se comparan en `docs/swift-genesis-qwen38-evaluation-20260929.md`; sus resultados son históricos y tienen las limitaciones de huella allí indicadas.
