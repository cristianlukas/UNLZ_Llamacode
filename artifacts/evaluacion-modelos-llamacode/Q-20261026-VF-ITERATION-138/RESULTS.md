# Q138 — Resultados del piloto de reverse engineering

## Resultado

**No promover Qwen3.8-27B Q4_K_M como reemplazo de ASTRA.** En este fixture sintético de Ghidra, Qwen acertó más, pero el tiempo mediano por solicitud fue **2,84×** el de ASTRA y supera el límite preregistrado de 1,25×. El resultado sólo aplica a estas 12 preguntas/3 semillas. No hubo preguntas de seguridad o criticidad, así que ese gate no se puede dar por aprobado. ASTRA y SOL productivos permanecen intactos.

## Comparación

| Perfil completo | Exactitud | Prefill mediano | Decode mediano | Latencia mediana | p95 solicitud | Arranque | Tiempo de solicitudes |
|---|---:|---:|---:|---:|---:|---:|---:|
| ASTRA Flash-Next IQ2_XS · Strata dual RTX 3090 | 22/36 (61,11%) | 1.543,8 tok/s | 139,1 tok/s | 8,118 s | 10.814 s | 495.32 s | 299.486 s |
| Qwen3.8-27B Q4_K_M · llama.cpp dual RTX 3090 | 31/36 (86,11%) | 1.547,6 tok/s | 34,6 tok/s | 23,065 s | 32.372 s | 33.03 s | 807.711 s |

Qwen mejoró exactitud **25 puntos porcentuales** (11 victorias, 2 derrotas y 23 empates en los 36 pares). Su decode mediano fue 4,02× más lento; el prefill quedó prácticamente igual. El cociente de aciertos correctos por segundo de solicitud fue 0.522× el de ASTRA. Para estas tareas, Qwen ofrece una señal de calidad, no una mejora de velocidad/calidad-tiempo.

Aciertos por semilla: ASTRA {'4242': 8, '5051': 7, '6061': 7}; Qwen {'4242': 10, '5051': 10, '6061': 11}. Los errores Qwen frente al control ocurrieron en Q4/seed4242 y Q7/seed5051; Qwen ganó en 11 pares. No hay casos etiquetados como críticos ni pruebas de seguridad en este corpus.

## Configuración y harness

- Fixture C sintético propio; oráculo del binario 12/12; Ghidra 12.2 + Temurin 25.0.5. Corpus final: 22 funciones/9.082 caracteres, SHA-256 `fd64ae63b1e0add2a1f842e349a6cfc54a8f3b841e69a1a34bd9af190337cadd`.
- 12 preguntas de opción A–D, tres semillas (4242, 5051, 6061), 36 solicitudes por perfil; prompt decompilado idéntico, máximo 1.024 tokens, puntuación por coincidencia exacta y orden serial ASTRA→Qwen.
- ASTRA: Strata 0.1.41, Flash-Next IQ2_XS, 1.048.576 contexto, YaRN×4, KV int8 con 32.768 residentes, MTP-4, ambas 3090, sampling 0,6/0,95/top-k20/min-p0/repeat1/presence0.
- Qwen: llama.cpp b11554/commit `966baae76`, Qwen3.8-27B Q4_K_M, contexto 32.768, batch/ubatch512, KV q4_0, Flash Attention, split tensor 1,1, ambas 3090 y sampling igual. Es una comparación de perfiles completos, no de pesos aislados.

## RAM, swap y estabilidad

A05 llegó a API READY tras **495,32 s** de arranque ASTRA; Q117 había tardado 282 s en cargar expertos y A04 había vencido el límite anterior de 900 s. A05 valida que 900 s era un límite insuficiente para ese arranque, no evidencia de crash por memoria.

El cgroup de la campaña alcanzó 83.7 GiB; MemAvailable mínima observada 59.0 GiB. El worker mantuvo swap 0 y OOM 0, la guarda nunca aplicó hard-stop, y ambos servidores terminaron limpiamente. La PSI superó el umbral diagnóstico durante parte de la carga, pero no paró el trabajo cuando aún había RAM disponible. Al cierre quedaron 8521240576 bytes usados en el swap global de 8589930496; el cgroup del worker no usó swap y no se capturó atribución por proceso.

Qwen empezó con solo 0.032 GiB libres de swap global, pero con 110.4 GiB de RAM disponible; no registró swap/OOM propio. Esto merece una comprobación de sistema separada si reaparece, sin imputarlo a esta inferencia.

## Recomendación

1. Mantener ASTRA como perfil productivo y no modificar ASTRA/SOL.
2. No adoptar Qwen27B como reemplazo bajo el gate actual: su exactitud en este fixture subió, pero la mediana E2E no cumple el límite de velocidad.
3. Si el caso de uso de reverse engineering prioriza precisión sobre tiempo, conservarlo como candidato experimental y validar después con un holdout más amplio y preguntas de criticidad explícita antes de llamarlo especialista.
4. No cambiar detector ni límites de RAM por esta corrida: el worker completó alto consumo sin OOM, sin swap cgroup y sin hard-stop. Investigar por separado el swap global casi lleno porque no se atribuyó a un proceso.

## Evidencia

- Campaña final: `receipts/campaign-attempt05-final.json`; respuestas crudas: `runs/attempt05/responses.jsonl`.
- Análisis reproducible y gates: `receipts/ab-analysis-attempt05.json`.
- Telemetría: `runs/attempt05/resource-monitor.jsonl`; logs del server: `runs/attempt05/logs/`; preflight: `receipts/preflight-attempt05.json`.
- Prerregistro del timeout, incidencias preflight y hashes: `receipts/amendment-06-startup-timeout-preregistration.json`.
