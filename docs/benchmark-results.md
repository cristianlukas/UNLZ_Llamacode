# Resultados vivos de benchmarking

Este archivo es la tabla operativa vigente. Cada mejora de perfil, harness,
agente o infraestructura debe actualizar esta tabla y agregar una entrada en
[`benchmark-results-history.md`](benchmark-results-history.md).

Última actualización: 2026-08-17.

| ID | Perfil | Agente | HE0 | HE20 | BCB | Tiempo HE0 | Tiempo HE20 | Tiempo BCB | TPS HE0 | TPS HE20 | TPS BCB | Visión | Drafter | Quant | Parámetros | Contexto | Thinking | Harness | Estado |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---|---|---|---|
| `sys-qwen38-27b-udq4-131k` | BALANCE - Qwen3.8 UD-Q4 visión | agent-chat | 1/1 | 20/20 | 5/8 | 11,288 s | 237,507 s | 1430,390 s | 39,22 | 60,50 | 65,21 | Sí | MTP3 | UD-Q4_K_XL | 27B | 131k | No | LC-H1 | BCB calidad |
| `sys-bench-qwen38-udq4-mtp4` | BALANCE - Qwen3.8 UD-Q4 MTP4 | agent-chat | 1/1 | 20/20 | 4/8 | 10,750 s | 262,737 s | 1507,487 s | — | 56,83 | 60,28 | Sí | MTP4 | UD-Q4_K_XL | 27B | 131k | No | LC-H1 | BCB calidad |
| `sys-48-katcoder-262k` | FAST - KAT2-Coder-7-8-26 | agent-chat | 1/1 | 20/20 | 3/8 | 15,817 s | 183,904 s | 401,169 s | 124,24 | 108,45 | 116,83 | No | — | Q4_K_M | 35B-A3B | 262k | No | LC-H1 | Reparado; BCB calidad |
| `9dda8ad0-ea5a-4a59-b7e2-d4f2f5c4bf94` | FAST - KAT-Coder-7-8-26 | agent-chat | 1/1 | 20/20 | 3/8 | 17,102 s | 273,407 s | 639,302 s | — | 107,14 | 111,77 | No | — | Q4_K_M | 35B-A3B | 262k | No | LC-H1 | Reparado; BCB calidad |
| `cbff7c85-2116-4b42-b1b9-485dd33384cc` | FAST - BigBang MTP | agent-chat | 1/1 | 20/20 | 3/8 | 11,289 s | 222,185 s | 1055,693 s | — | 204,42 | 207,33 | Sí | MTP embebido | Q4_K_M | 35B-A3B | 65k | No | LC-H1 | BCB calidad |
| `sys-repair-48-bigbang-mtp-balance` | BALANCE - BigBang MTP | agent-chat | 1/1 | 20/20 | 3/8 | 11,266 s | 253,067 s | 406,496 s | — | 206,53 | 211,18 | Sí | MTP embebido | Q4_K_M | 35B-A3B | 65k | No | LC-H1 | Reparado; BCB calidad |
| `a03e65f5-2f2c-4d45-b67b-4b1270fa2a6c` | BALANCE - ThinkingCap Qwen3.6 MTP4 | agent-chat | 1/1 | 20/20 | 3/8 | 11,288 s | 118,098 s | 169,431 s | 48,21 | 61,96 | 52,04 | Sí | MTP4 | Q4_K_M | 27B | 131k | No | LC-H1 | BCB calidad |
| `sys-48-thinkingcap-mtp` | BALANCE - ThinkingCap+MTP | agent-chat | 1/1 | 20/20 | 3/8 | 10,265 s | 217,926 s | 401,922 s | 7,46 | 58,64 | 58,15 | Sí | MTP4 | Q4_K_M | 27B | 131k | No | LC-H1 | BCB calidad |
| `8d0dd2e0-c6c6-41ef-81d6-893c20d2f621` | BALANCE - Laguna S 2.1 original | agent-intermedio | 0/0 | No ejecutado | No ejecutado | 47,847 s | — | — | — | — | — | No | — | UD-Q2_K_XL | 118B-A8B | 100k | No | LC-H1 | CUDA illegal access en GPU0 |
| `sys-laguna-s-2-1-q2-48gb-safe` | BALANCE - Laguna S 2.1 · CUDA safe 64k | agent-basico | 1/1 | Pendiente | Pendiente | 150,127 s | — | — | — | — | — | No | — | UD-Q2_K_XL | 118B-A8B | 65k | No | LC-H1 | HE0 válido; sin crash CUDA |
| `4f5cc556-333d-4310-955e-15042cd874d6` | QUALITY - DeepSeek Fusion leloch | agent-chat | 1/1 | 20/20 histórico | 1/8 | 69,794 s | 802,656 s | 2397,063 s | — | 10,35 | 8,57 | No | — | Q2/Q4 imatrix | 284B | 131k | No | LC-H1 | BCB calidad |
| `6b3bf7bd-0889-491a-9b6d-b12128478a5f` | QUALITY - DeepSeek Fusion leloch · VRAM balance | agent-chat | 1/1 | 20/20 histórico | 2/8 | 65,622 s | 775,223 s | 6328,761 s | — | 10,76 | 9,45 | No | — | Q2/Q4 imatrix | 284B | 131k | No | LC-H1 | BCB calidad; 2 reparaciones |
| `4f5cc556-333d-4310-955e-15042cd874d6` | DeepSeek original · repetición actual | agent-avanzado | 1/1 | 20/20 | En curso | 112,497 s | 1164,244 s | — | — | 9,58 | — | No | — | Q2/Q4 imatrix | 284B | 131k | No | LC-H1 | HE20 válido; BCB en curso |

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
