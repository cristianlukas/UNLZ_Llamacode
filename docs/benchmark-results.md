# Resultados vivos de benchmarking

Este archivo es la tabla operativa vigente. Cada mejora de perfil, harness,
agente o infraestructura debe actualizar esta tabla y agregar una entrada en
[`benchmark-results-history.md`](benchmark-results-history.md).

Última actualización: 2026-08-18.

## Alcance activo

Sólo se ejecutan nuevos benchmarks para perfiles marcados `⚡ BEST`. La
selección activa incluye **⚡ Qwen3.8 UD-Q4 visión** y los cuatro candidatos
experimentales Qwen3.6 de cache/MTP incorporados el 2026-08-18. Estos cuatro
son candidatos de medición, no ganadores promovidos: sus resultados siguen
pendientes y no deben reemplazar perfiles existentes automáticamente.

El esquema obligatorio de cada fila es exactamente: `ID`, `Perfil`, `Agente`,
`HE0`, `HE20`, `BCB`, `Tiempo HE0`, `Tiempo HE20`, `Tiempo BCB`, `TPS HE0`,
`TPS HE20`, `TPS BCB`, `VRAM GPU0`, `VRAM GPU1`, `VRAM total`, `Visión`,
`Drafter`, `Quant`, `Parámetros`, `Contexto`, `Thinking`, `Harness` y `Estado`.
`VRAM total` es el pico
agregado usado por el proceso (`GPU0 + GPU1`, en MB) durante la corrida
reportada; no es la VRAM libre ni la capacidad instalada.

| ID | Perfil | Agente | HE0 | HE20 | BCB | Tiempo HE0 | Tiempo HE20 | Tiempo BCB | TPS HE0 | TPS HE20 | TPS BCB | VRAM GPU0 | VRAM GPU1 | VRAM total | Visión | Drafter | Quant | Parámetros | Contexto | Thinking | Harness | Estado |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---|---|---|---|---|
| `sys-qwen38-27b-udq4-131k` | ⚡ Qwen3.8 UD-Q4 visión | chat | 1/1 | 20/20 | 5/8 | 11,288 s | 237,507 s | 1430,390 s | 39,22 | 60,50 | 65,21 | No medido | No medido | 24.569 MB | Sí | MTP3 | UD-Q4_K_XL | 27B | 131k | No | LC-H1 | BCB calidad |
| `sys-48-katcoder-262k` | KAT2-Coder-7-8-26 | chat | 1/1 | 20/20 | 3/8 | 15,817 s | 183,904 s | 401,169 s | 124,24 | 108,45 | 116,83 | No medido | No medido | 26.761 MB | No | — | Q4_K_M | 35B-A3B | 262k | No | LC-H1 | Reparado |
| `sys-repair-48-bigbang-mtp-balance` | BigBang MTP BALANCE | chat | 1/1 | 20/20 | 3/8 | 11,266 s | 253,067 s | 406,496 s | — | 206,53 | 211,18 | No medido | No medido | 25.644 MB | Sí | MTP embebido | Q4_K_M | 35B-A3B | 65k | No | LC-H1 | Reparado |
| `a03e65f5-2f2c-4d45-b67b-4b1270fa2a6c` | ThinkingCap Qwen3.6 MTP4 | chat | 1/1 | 20/20 | 3/8 | 11,288 s | 118,098 s | 169,431 s | 48,21 | 61,96 | 52,04 | No medido | No medido | 23.624 MB | Sí | MTP4 | Q4_K_M | 27B | 131k | No | LC-H1 | BCB calidad |
| `sys-laguna-s-2-1-q2-48gb-safe` | Laguna S.2.1 · CUDA safe 64k | básico | 1/1 | Pendiente | Pendiente | 150,127 s | — | — | — | — | — | No medido | No medido | 18.891 MB | No | — | UD-Q2_K_XL | 118B-A8B | 65k | No | LC-H1 | HE0 válido |
| `8dd3325d-8658-45ca-9aad-ad80d301b4e9` | Laguna S.2.1 · dual GPU safe · 32k | Máximo | 1/1 | 20/20 | 4/8 | 60,919 s | 392,072 s | 871,561 s | 19,77 | 54,70 | 44,33 | No medido | No medido | 40.760 MB | No | — | UD-Q2_K_XL | 118B-A8B | 32k | No | LC-H1 | Reparado; usa 2×GPU |
| `6b3bf7bd-0889-491a-9b6d-b12128478a5f` | DeepSeek Fusion VRAM histórico | chat | 1/1 | 20/20 | 2/8 | 65,622 s | 775,223 s | 6328,761 s | — | 10,76 | 9,45 | No medido | No medido | 35.903 MB | No | — | Q2/Q4 imatrix | 284B | 131k | No | LC-H1 | BCB calidad |
| `4f5cc556-333d-4310-955e-15042cd874d6` | DeepSeek repetición actual | avanzado | 1/1 | 20/20 | 4/8* | 112,497 s | 1164,244 s | 1396,871 s* | — | 9,58 | — | No medido | No medido | 32.684 MB | No | — | Q2/Q4 imatrix | 284B | 131k | No | LC-H1 | BCB mejor resultado evaluable; repetir cancelado por reparación estancada |
| `sys-experiment-qwen36-cache-mtp2` | ⚡ Qwen3.6 cache híbrido · MTP2 | chat | Pendiente | Pendiente | Pendiente | — | — | — | — | — | — | No medido | No medido | — | Sí | MTP2 | Q4_K_M | 27B | 131k | No | LC-H1 | Candidato BEST; benchmark solicitado |
| `sys-experiment-qwen36-cache-mtp4` | ⚡ Qwen3.6 cache híbrido · MTP4 | chat | Pendiente | Pendiente | Pendiente | — | — | — | — | — | — | No medido | No medido | — | Sí | MTP4 | Q4_K_M | 27B | 131k | No | LC-H1 | Candidato BEST; benchmark solicitado |
| `sys-experiment-qwen36-cache-mtp6` | ⚡ Qwen3.6 cache híbrido · MTP6 p-min 0.5 | chat | Pendiente | Pendiente | Pendiente | — | — | — | — | — | — | No medido | No medido | — | Sí | MTP6 p-min 0.5 | Q4_K_M | 27B | 131k | No | LC-H1 | Candidato BEST; benchmark solicitado |
| `sys-experiment-qwen36-cache-text-mtp4` | ⚡ Qwen3.6 texto-only · cache híbrido · MTP4 | chat | Pendiente | Pendiente | Pendiente | — | — | — | — | — | — | No medido | No medido | — | No | MTP4 | Q4_K_M | 27B | 131k | No | LC-H1 | Candidato BEST; benchmark solicitado |
| `c3a3851d-c3a0-4dc8-8018-1c408f017a95` | llama-debug · ThinkingCap Q3_K_M MTP · ubatch 128 | Chat liviano | 1/1 | Pendiente | Pendiente | 26,242 s | — | — | — | — | — | 12.002 MB | 12.963 MB | 24.963 MB | No | MTP3 | Q3_K_M | 27B | 262k | No | LC-H1 | Copia editable; HE0 válido; HE20/BCB pendientes |
| `d805e63a-f4df-4b99-86b3-5472f8998d63` | llama-debug · ThinkingCap Q3_K_M MTP · batch 1024 / ubatch 128 | Chat liviano | 1/1 | Pendiente | Pendiente | 18,760 s | — | — | — | — | — | 11.954 MB | 12.963 MB | 24.910 MB | No | MTP3 | Q3_K_M | 27B | 262k | No | LC-H1 | Copia editable; HE0 válido; HE20/BCB pendientes |

Las dos filas `llama-debug` fueron solicitadas explícitamente para medición
manual. No están marcadas como ⚡ BEST ni reemplazan al perfil original
`106_MAX-Q`; ambos HE0 se ejecutaron con `agent-chat`, una pasada, y pasaron
`HumanEval (1 ítems)` sin reparación, timeout, crash ni fallo de transporte.

## Experimentos con compuerta HE0

Estas variantes se probaron para repartir más expertos DeepSeek en GPU0. Al no
pasar HE0, quedan bloqueadas y no se ejecutan HE20 ni BCB.

| ID | Perfil | Agente | HE0 | HE20 | BCB | Tiempo HE0 | VRAM total | Estado |
|---|---|---|---:|---:|---:|---:|---:|---|
| `392ea030-059e-4f69-86c6-81d3fa31acbc` | DeepSeek Fusion · VRAM expertos 0–2 | básico | 0/1 | No ejecutado | No ejecutado | 21,105 s | No medido | Salida no evaluable; sin CUDA/OOM |
| `6d4b528f-f26d-4500-99cf-c25a36dd6f54` | DeepSeek Fusion · VRAM expertos 0–3 | chat | 0/1 | No ejecutado | No ejecutado | 32,450 s | No medido | Salida no evaluable; sin CUDA/OOM |
| `0a1b97be-dec6-41b8-8382-417ab840bec7` | DeepSeek expertos 0–2 · dual GPU tilted 32k | Máximo | 0/0 | No ejecutado | No ejecutado | 13,302 s | No medido | OOM en GPU1 |
| `97221bae-60f1-4933-8ae7-fc1421407b7f` | DeepSeek expertos 0–2 · dual GPU 20 layers | Máximo | 0/0 | No ejecutado | No ejecutado | 37,075 s | No medido | Crash backend `ggml-cpu.c:2691 op not implemented` |
| `318368e6-3fb7-4ef8-a76a-23030c544c49` | Laguna S 2.1 · CPU-safe 32k | básico → chat | 0/1 | No ejecutado | No ejecutado | 68,149 s / 74,605 s | No medido | Ambos agentes no crearon el archivo esperado |
| `807c23f8-442c-4303-b96a-e1d0481eaf69` | Laguna S 2.1 · safe CUDA 65k | básico | 0/0 | No ejecutado | No ejecutado | 30,432 s | No medido | `CUDA illegal memory access` en GPU0 |
| `8dd3325d-8658-45ca-9aad-ad80d301b4e9` | Laguna S 2.1 · dual GPU safe · 32k | Máximo | 1/1 | 20/20 | 4/8 | 60,919 s / 392,072 s / 871,561 s | 40.760 MB | Reparado; `tensor-split 1,1`, sin crash |

## Comparación de agentes en DeepSeek BCB

| Agente | BCB inicial → final | Tiempo total | Resultado |
|---|---:|---:|---|
| agent-basico | 1/8 → 2/8 | 830,127 s | No corrigió los fallos funcionales |
| agent-intermedio | 2/8 → 2/8 | 997,436 s | Reparación estancada |
| agent-avanzado | 3/8 → 4/8 | 1396,871 s | Mejor resultado; fallaron 771, 1019, 139 y 360 |
| agent-maximo | 1/8 → 1/8 | 983,893 s | Sólo pasó 906 |

## Criterio de actualización

Cada cambio debe registrar primero HE0, después HE20 y finalmente BCB. Si se
modifica perfil, binario, harness o agente de forma material, los resultados
anteriores quedan marcados como históricos y se repite la cadena desde HE0.
