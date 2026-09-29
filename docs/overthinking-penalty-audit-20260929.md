# Auditoría de sesgo a marcadores de overthinking — 2026-09-29

## Pregunta

Se evaluó si conviene aplicar en LlamaCode la penalización de logits propuesta
para marcadores como `wait`, `maybe` y `perhaps`, con foco en el modelo, el
harness y Computer Use. La [investigación de Meta](https://arxiv.org/abs/2606.00206)
reporta mejoras en cinco benchmarks y modelos cuantizados de 1,5B a 32B; la
publicación de Reddit adjunta extiende una prueba a Qwen3.5-4B, pero sólo con
50 preguntas MATH-500. Ninguna de esas pruebas valida nuestros flujos agentivos.

## Evidencia anterior revisada

- El adjunto incluye un análisis observacional de 85 sesiones Qwen3.8-Flash-Next
  (6.851 bloques, ~2,2 M tokens de thinking), sin activar la penalización.
  Sólo `Hmm`, `Wait` y `Actually` quedaron como candidatos. El ahorro superior
  estimado fue 1,6–7% del thinking (aprox. 1–4% de todos los tokens); el análisis
  juzgó útil la mayoría de sus apariciones y advirtió que los usos en tool calls,
  código y respuestas también se verían afectados por un sesgo global. Es una
  cota observacional, no una medición de calidad bajo penalización.
- `docs/computer-use-sandwich.md` ya tiene corpus de Computer Use con distractores
  y permisos. Sus resultados distinguen exactitud, seguridad y latencia; por eso
  se usó ese corpus difícil, manteniendo `state-first` en todas las variantes.
- `docs/harness-quality-campaign-20260915.md` y las auditorías posteriores ya
  describen los ciclos no convergentes del harness. El diagnóstico es que mucho
  del desperdicio viene de volver a planificar o inspeccionar, no de palabras
  concretas. El harness ya aplica bloqueos y replanteo ante herramientas
  repetidas; una penalización léxica no sustituye esos controles.
- `docs/ingicharla-local-voice-audit-20260918.md` y las pruebas de compactación
  mantienen Charla orientada a respuestas breves y baja latencia. No se halló
  una medición de calidad de voz que justifique cambiar su muestreo.

## A/B local reproducible

Runner: [`tools/benchmark_overthinking_penalty.py`](../tools/benchmark_overthinking_penalty.py).
Corpus inmutable: `assets/benchmarks/custom/computer_use_prompt_order_hard_v1.json`.
La prueba envía decisiones seguras por API y no ejecuta acciones reales de
escritorio.

```bash
python3 tools/benchmark_overthinking_penalty.py \
  --url http://127.0.0.1:18089/v1/chat/completions \
  --model Qwen3.5-9B-Q4_K_M --passes 3 \
  --reasoning-budget 256 --max-tokens 768 --bias-values 0.5,1.0 \
  --out artifacts/overthinking-penalty-qwen35-9b-computer-use-20260929.json
```

Condiciones: Ubuntu; Qwen3.5-9B Q4_K_M, SHA-256
`03b74727a860a56338e042c4420bb3f04b2fec5734175f4cb9fa853daf52b7e8`; build
local de `llama.cpp` commit `c28d538`; 2× RTX 3090, `ctx=8192`, split por
capas, sin speculative decoding; reasoning activo, presupuesto de 256 tokens,
`temp=0.6`, `top_p=0.95`, `top_k=20`. Cada token se resolvió contra el
tokenizer del modelo; el JSON de salida conserva los IDs y las filas completas.
Las tres variantes se intercalaron en el mismo orden aleatorio y usaron las
semillas 11, 42 y 77.

| Variante | Correctas | Seguridad | Respuesta exacta | Mediana latencia | Mediana tokens generados | Mediana chars de thinking |
|---|---:|---:|---:|---:|---:|---:|
| Sin sesgo | 57/72 (79,17%) | 50/63 (79,37%) | 70,83% | 2.456,70 ms | 326,5 | 1.018 |
| Penalización −0,5 | 57/72 (79,17%) | 50/63 (79,37%) | 69,44% | 2.455,97 ms | 333,6 | 1.018 |
| Penalización −1,0 | 57/72 (79,17%) | 50/63 (79,37%) | 70,83% | 2.457,53 ms | 326,5 | 1.018 |

No hubo cambio de exactitud ni de seguridad. El sesgo de −0,5 tuvo una
respuesta exacta menos y generó ligeramente más tokens; −1,0 cambió dos
decisiones en sentidos opuestos. La diferencia de latencia es ruido. La API no
devolvió un contador separado de tokens de razonamiento, así que el informe
guarda caracteres del bloque como referencia y tokens totales generados. Algunas
respuestas llegaron al límite de salida de 768 tokens, reflejado en `finishReason`.

El primer ensayo del 28-09 se descartó: mandaba `reasoning_budget`, campo que
este build de llama.cpp ignora. La corrida válida usa `reasoning_budget_tokens`
y etiquetas `<think>`/`</think>` explícitas; una solicitud de control confirmó
que el sampler aplicó el límite. No se usan las métricas del primer ensayo.

## Decisión

- **No se cambia ningún perfil ni el sampling general.** El A/B válido no mostró
  una mejora en calidad, seguridad, longitud o latencia.
- **No se agrega sesgo global al harness.** Puede cambiar texto de código,
  argumentos de tools y respuesta final, y los datos anteriores indican que la
  mayor parte de los usos de `Hmm`/`Wait`/`Actually` sí son útiles. El mecanismo
  probado tampoco limita el sesgo a un bloque de thinking.
- **No se cambia Ingi Charla.** La corrida fue de selección textual en Computer
  Use; no prueba latencia de voz, calidad acústica ni conversación natural.
- **No se promueve el resultado a Qwen3.8-Flash-Next.** Ese perfil externo usa
  otra arquitectura/runtime con speculative decoding y sólo hay análisis de
  trazas, no A/B de penalización en ejecución. La corrida local usa Qwen3.5-9B
  sin speculative decoding.

La prueba queda registrada como no promotora. Para reabrir la decisión hace
falta una A/B pareada sobre el perfil/runtime objetivo de Flash-Next y tareas
agentivas reales con receipts, separando el thinking de las llamadas de tools;
volver a correr MATH-500 con la lista de 50 palabras no respondería esa pregunta.
