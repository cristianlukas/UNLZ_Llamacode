# Reejecución BCB8 directa — 2026-09-15

Se reejecutó el pack de 8 tareas `bigcodebench-hard-ubuntu-8.json` contra los
perfiles solicitados. Esta campaña es un control **directo de modelo**: cada
modelo recibe el enunciado y devuelve código, y luego se ejecutan los tests
originales. No usa el ciclo LC-H1 de LlamaCode (herramientas, reparación,
reintentos y memoria de agente), por lo que no reemplaza ni invalida los BCB
agentivos históricos de la tabla principal.

## Corpus y protocolo

- Fecha: 2026-09-15, Ubuntu, 2× RTX 3090, P2P disponible.
- Corpus: `artifacts/bigcodebench-hard-ubuntu-8.json`.
- SHA-256 del corpus: `11279cde14113fc8527f141c53e14cb5ccf0dba65749081a4f914408e391c268`.
- Prompt directo: sólo código Python ejecutable, sin herramientas ni reparación.
- Sampling: `temperature=0.2`, `top_p=0.95`, `top_k=20`, `min_p=0.0`.
- KV: `q8_0` en las rutas GGUF; no se usó ninguna quantización superior a Q8.
- Resultados por tarea y código generado: [`artifacts/bcb-rerun-20260915`](../artifacts/bcb-rerun-20260915/).

## Resultado de la corrida

| Perfil | Configuración probada | Servidor | BCB8 directo | Tiempo de generación de 8 casos | Lectura |
|---|---|---:|---:|---:|---|
| **QWEN35-A3B vLLM** | AutoRound INT4 · TP2/P2P · KV FP8 · vLLM 0.27.1 · control 32K · sin MTP | OK | **1/8** | 156,849 s | Válido como control directo; no comparable 1:1 con el BCB LC-H1 histórico 4/8 |
| **METEOR / BigBang** | Q4_K_M · MTP5 · KV Q8 · dual layer split · 8K | OK | **2/8** | 13,187 s | Mejor resultado directo de los GGUF grandes, pero no supera su BCB LC-H1 histórico 3/8 |
| **QWEN35-A3B GGUF MTP** | UD-Q4_K_XL · MTP3 · KV Q8 · dual layer split · 8K | OK | **1/8** | 17,583 s | Funcional; no eleva el resultado de calidad frente al control vLLM |
| **CyberTiel** | 35B-A3B Q4 · MTP3 · KV Q8 · dual layer split · 8K | OK | **1/8** | 15,288 s | Velocidad alta, calidad directa todavía no demostrada |
| **Qwen3.5-9B** | Q4_K_M · MTP3 · KV Q8 · 8K | OK | **1/8** | 20,882 s | Auxiliar funcional; no alcanza evidencia para uso agentivo principal |
| **Qwen3.5-4B** | Q4_K_M · MTP3 · KV Q8 · 8K | OK | **1/8** | 12,445 s | Auxiliar rápido; BCB directo bajo esta muestra |
| **Qwen3.5-2B** | Q4_K_M · MTP3 · KV Q8 · 8K | OK | **0/8** | 9,865 s | No apto para sustituir un perfil de coding por calidad |
| **Qwen3.5-4B CPU** | Q4_K_M · sin MTP · CPU · 8K | OK | **2/8** | 418,982 s | Control de calidad CPU; la receta MTP CPU no es compatible con el runtime disponible |

El tiempo es la suma del tiempo de generación de las ocho respuestas; no es
TPS de decode. El grader de cada caso ejecutó los tests en un entorno temporal
aislado y no aceptó respuestas que sólo compilaran.

## Comparación con la evidencia anterior

| Perfil | BCB agentivo/histórico registrado | BCB directo de esta campaña | Decisión |
|---|---:|---:|---|
| QWEN35-A3B vLLM | **4/8** | 1/8 | Mantener 4/8 como evidencia agentiva; el 1/8 queda como diagnóstico directo |
| METEOR / BigBang | **3/8 histórico** | 2/8 | No promover; la diferencia está dentro de protocolos distintos |
| QWEN35-A3B GGUF MTP | Pendiente | 1/8 | Sigue experimental |
| CyberTiel | Pendiente | 1/8 | Sigue experimental |
| Qwen3.5-9B | Pendiente | 1/8 | Sigue auxiliar |
| Qwen3.5-4B | Pendiente | 1/8 | Sigue auxiliar |
| Qwen3.5-2B | Pendiente | 0/8 | Mantener sólo para tareas rápidas, no coding complejo |
| Qwen3.5-4B CPU | Pendiente | 2/8 | No usar como backend por defecto por latencia |

No se cambió el perfil **SOL** ni se promovió ninguno de estos modelos. Para
actualizar un BCB oficial habría que repetir la cadena documentada
`HE0 → HE20 → BCB` mediante el harness LC-H1, incluyendo herramientas,
reparación y el mismo agente. La catalogación Linux actual no tenía un binario
asignado para ejecutar esa campaña oficial sobre estas filas, por eso se dejó
este control directo separado.

## Limitación del control CPU

El runtime CPU empaquetado anterior rechazó el layout de tensores de Qwen3.5
(`expected 441, got 437`). Se usó el lector CUDA actual con `-ngl 0` y sin MTP
para obtener un control reproducible. Esto valida el modelo en CPU, pero no
valida una configuración CPU+MTP.

