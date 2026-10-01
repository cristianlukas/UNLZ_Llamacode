# Qwen3.8 Coder IQ1_M — LC-H1 apareado

Fecha: 2026-10-01

Estado: evaluación LC-H1 completada; **no promover el candidato**.

Esta corrida cierra la evaluación que quedó pendiente en
[`qwen38-flash-next-gsq-rco-coder-audit-20260930.md`](qwen38-flash-next-gsq-rco-coder-audit-20260930.md).
Se comparó `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` IQ1_M con Swift
Qwen3.8-27B Genesis, en el mismo daemon de test, binario, agente, harness,
semilla y receta. Los perfiles y datos de usuario fueron aislados en raíces
XDG temporales; no se cambiaron perfiles persistentes ni el runtime de la app.

## Resultado

| Etapa | Genesis | Coder IQ1_M | Tiempo Genesis | Tiempo Coder |
|---|---:|---:|---:|---:|
| HumanEval, 1 caso | 1/1 | 1/1 | 24,070 s | 30,074 s |
| HumanEval, 20 casos | 20/20 | 20/20 | 739,751 s | 736,527 s |
| BigCodeBench-Hard, 8 casos | **8/8** | **5/8** | 1097,911 s | 1492,252 s |
| Total de la secuencia | **29/29** | **26/29** | **1861,732 s** | **2258,853 s** |

Los tiempos son los de `totalTime` del harness y contienen tanto generación
como trabajo del agente y evaluación local. En la primera secuencia completa,
Coder tardó 21,3% más en total. HE20 fue prácticamente igual en tiempo (3,224 s
menos para Coder), por lo que no aparece una ventaja general de latencia.

### BCB y repetición

Genesis obtuvo 2/8 en el primer intento de BCB y 8/8 tras dos intentos de
reparación; todos los casos pasaron sus checks locales al final. Coder obtuvo
3/8 en el primer intento y 5/8 al final tras dos reparaciones.

Se repitió BCB para ambos modelos. Coder volvió a empezar con 3/8 y terminó en
4/8 tras dos reparaciones. Volvió a fallar `BigCodeBench/1019`, `/583` y `/360`;
esta vez también `/765`. Los casos `/928`, `/771`, `/906` y `/139` pasaron en
ambas corridas de Coder.

La repetición de Genesis se canceló después de unos 48 minutos en la fase de
reparación, antes de publicar un resultado. No se cuenta como score ni como
timeout del modelo. Por eso hay dos mediciones de Coder, pero sólo una medición
completa de Genesis para BCB; los promedios no se presentan como un benchmark
estadístico equilibrado.

## Receta y entorno

- Runtime: `llama.cpp` 0.3.0-dev build1, commit `9bd97fe`, mismo ejecutable
  `cuda-flashnext-2x3090/llama-server` para los dos modelos.
- Hardware: 2× RTX 3090 de 24 GB; ambos modelos cargaron sin OOM.
- Contexto 65.536; batch 512; ubatch 64; 8 hilos; 999 capas GPU; Flash
  Attention; split por capas con `0.5,0.5`; mmap; KV Q8; cont-batching;
  parallel 1.
- Sampling: `temp 0.60`, `top-p 0.95`, `top-k 20`, `min-p 0.0`,
  `repeat-penalty 1.0`, `presence-penalty 0.0`; razonamiento desactivado;
  máximo 4096 tokens; plantilla Qwen38 tools fija.
- Harness LC-H1: agente `agent-maximo`, semilla 4242, una pasada, orden HE0 →
  HE20 → BCB; hasta dos reparaciones para fallos de aceptación.
- MTP/speculative decoding desactivado en ambos perfiles.

Los dos shards del candidato se verificaron contra la revisión Hugging Face
`5348543e0147355ac9cbcb031184a3546350988e`; tamaños y SHA-256 están en el
manifiesto del artefacto.

## Decisión

**Mantener Genesis como perfil de referencia y no promover IQ1_M.** Coder iguala
HumanEval (21/21), pero en las dos ejecuciones de BCB quedó en 5/8 y 4/8 tras
reparaciones, frente al 8/8 final de Genesis en la corrida completa. La muestra
es pequeña y la réplica de Genesis quedó inconclusa, pero la brecha observada y
los fallos repetidos no justifican cambiar el perfil actual.

La siguiente prueba útil es diagnosticar los casos 1019, 583 y 360 contra sus
checks del harness; no hace falta repetir HumanEval ni cambiar el código de
LlamaCode para tomar esta decisión. El candidato puede seguir disponible como
modelo experimental manual.

## Artefactos

- [Resultados completos de la secuencia apareada](../artifacts/qwen38-coder-lch1-paired-20261001/paired-results.json)
- [Manifiesto de tamaños y hashes](../artifacts/qwen38-coder-lch1-paired-20261001/model-manifest.json)
- [BCB repetido y estado de la repetición Genesis](../artifacts/qwen38-coder-lch1-paired-20261001/additional-bcb-results.json)
