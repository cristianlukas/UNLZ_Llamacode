# Qwen3.8 Flash-Next GSQ/RCO Coder — revisión para LlamaCode

Fecha: 2026-09-30

Candidato: [`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF), quant `IQ1_M`
Estado: **evaluación directa completada; no agregar al catálogo ni reemplazar un perfil**.

## Qué aporta

Es una variante experimental específica para coding que retiene 256 de los 512
expertos por capa y guarda los expertos retenidos a 3,5 bpw. El modelo card
publica 58,4 GB en total, de los cuales 29,6 GB corresponden al working set
residente; el shard n-gram de 28,8 GB puede permanecer en SSD con `--lazy-mode
on`. La comparación publicada es SWE-bench Verified 75,60 vs. 82,80 en BF16 y
LiveCodeBench v6 86,28 vs. 87,43, ambos a xhigh. Son resultados del publicador,
no del harness local.

GSQ y RCO asignan precisión por tensor bajo un presupuesto; RCO también elige
expertos contra KL en datos de calibración. La idea relevante es la
cuantización no uniforme y el pruning dirigido por capacidad. LlamaCode no
necesita implementar esos algoritmos para usar un GGUF ya preparado.

## Evidencia local existente que se reutiliza

No se repiten estos controles:

| Control ya registrado | Resultado disponible | Para qué sirve en esta revisión |
|---|---|---|
| Swift Qwen3.8-27B Genesis NVFP4, contrato de tools, 64K | 5/5 pasadas con `read_file` seguido de `write_file` | Control de formato/orden de tool calls |
| Genesis, BCB directo, 64K | 1/8, transporte 8/8 | Control local de coding; comparar con el mismo pack, aclarando que no es LC-H1 |
| Genesis, Computer Use prompt-order, 48 estados, 5 pasadas y 3 órdenes | 100% exactitud, validez, seguridad y transporte en cada variante; gate total falló por latencia | El benchmark de decisiones está en techo de calidad; no promete ventaja por prompt |
| Genesis, decode 64K, cinco pasadas | mediana 56,35 tok/s | Referencia de velocidad, sin MTP equivalente para este candidato |
| Qwen3.8 GSQ/RCO 27B y otras variantes Flash-Next | Las auditorías previas ya registran problemas de latencia/infraestructura y ausencia de superioridad local | No repetir esas descargas ni confundirlas con el artefacto Coder de ISTA-DASLab |

Fuentes locales: `artifacts/swift-genesis-evaluation-20260929/`;
`docs/qwen38-flash-next-gsq-rco-audit-20260915.md`;
`docs/qwen38-gsq-rco-dflash2-q2-audit-20260918.md`;
`docs/computer-use-sandwich.md`.

## Compatibilidad y resultados locales

La evaluación se ejecutó en 2× RTX 3090 (24 GB cada una), 123 GiB de RAM y
runtime LlamaCode `llama.cpp` 0.3.0-dev, commit `9bd97fe`. Se fijó la revisión
Hugging Face `5348543e0147355ac9cbcb031184a3546350988e`. Shards completos:

| Archivo | Bytes | SHA-256 |
|---|---:|---|
| `IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf` | 29.608.446.496 | `e11083ba855e7666b48ea3f2db6a9c3a20c18751a012cc24f948de91b7087fad` |
| `IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00002-of-00002.gguf` | 28.800.138.432 | `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113` |
| `mmproj-Qwen3.8-Flash-Next-BF16.gguf` | 907.543.008 | — |

Ambos shards cargaron con lazy mmap, split dual GPU, KV Q8 y contexto asignado
de 65.536; el uso observado fue ~15,6 GB por GPU, sin OOM. Esa carga confirma
compatibilidad del runtime en esta receta. No activa MTP/DFlash: la corrida de
decode fue sin speculative decoding. El campo `mtpDraftMax=4` en el JSON del
microbenchmark es metadata heredada del runner, no un flag habilitado en el
servidor; por eso la velocidad no es una comparación MTP equivalente.

Resultados reproducibles guardados en
[`artifacts/qwen38-gsq-rco-coder-eval-20260930/`](../artifacts/qwen38-gsq-rco-coder-eval-20260930/):

| Prueba | Resultado del candidato | Control comparable | Lectura |
|---|---:|---:|---|
| `harness_tool_contract_v1`, 5 pasadas | 5/5; transporte 5/5 | Genesis 5/5 | Paridad en contrato básico `read_file` → `write_file`. |
| BigCodeBench-Hard-8 directo, 64K | 2/8; transporte 8/8 | Genesis 1/8; transporte 8/8 | +1 ítem, muestra pequeña y sin valor LC-H1; señal insuficiente para reemplazar perfil. |
| Decode corto, 5 pasadas | mediana 62,39 tok/s | Genesis 56,35 tok/s | +10,7% observado; orientativo porque las recetas de speculative decoding no están igualadas. |
| Computer Use, 48 estados × 5 pasadas × 3 órdenes | con thinking desactivado: state-first 100%, question-first 97,92%, sandwich 100%; validez/transporte 100% | Genesis: 100% en los tres órdenes | El gate global falla por latencia sandwich (604,98 ms vs 454,67 ms, +33%). No promover sandwich. |
| Visión + consulta de acción, 3 pasadas | 3/3; reconoce “Tema oscuro” como activo; no ejecuta acción | No repetido | Smoke funcional de `mmproj`, no prueba general de grounding. |

En el primer Computer Use, con el thinking nativo habilitado y solo 8 tokens
de salida, los 720 requests tuvieron transporte correcto pero 0% de respuestas
válidas: el presupuesto se consumía en el canal de razonamiento. Se repitió el
mismo fixture y orden de prompts con `chat_template_kwargs.enable_thinking=false`;
state-first y sandwich recuperaron exactitud/seguridad del 100%. No se cambió
el runner compartido ni su default. El script de envoltura reproducible está en
el directorio de resultados.

También se intentó LC-H1 real (HE0 → HE20 → BCB) con perfil y raíces temporales
aislados. El catálogo localizó el modelo, pero `systemProfileReady` fue falso y
`computeEffectiveProfile` devolvió `No binary selected.` en el registro de
binarios de test. No se editó ese registro compartido para forzar la ejecución;
por tanto no hay score LC-H1 válido aún.

## Lectura por subsistema

- **Coding/modelo:** el cambio 1/8 → 2/8 de BCB-Hard-8 es pequeño y una sola
  muestra; HE0/HE20/BCB del Harness LlamaCode sigue siendo el dato faltante.
- **Velocidad:** el candidato marca +10,7% en el microbenchmark sin MTP. No se
  puede atribuir superioridad global mientras Genesis corre con MTP4 y faltan
  comparaciones de velocidad en la misma receta.
- **Computer Use:** thinking debe desactivarse para respuestas ultracortas de
  clasificación. El candidato iguala el techo de exactitud state-first, pero
  no supera el gate de latencia por la variante sandwich; no cambiar el orden
  de prompts compartido.
- **Harness y perfiles:** no modificar HarnessSpec, guardrails, orden global ni
  catálogo por estos resultados. Mantener el IQ1_M como artefacto de evaluación
  manual hasta tener LC-H1 y comparación de coding más amplia.
- **Ingi Charla:** no aplica; no se evaluaron voz ni audio.

## Decisión

**No promover ni editar perfiles/harness.** Se confirma carga 64K, contrato
básico de herramientas y smoke de visión. Hay señales prometedoras pero
insuficientes en BCB y decode; Computer Use no supera su gate completo y LC-H1
quedó bloqueado por la resolución del binario en el daemon de test. Los JSON
anteriores conservan las corridas y permiten continuar sin repetirlas. Para
cerrar la evaluación falta resolver el binario aislado y correr HE0 → HE20 →
BCB LC-H1 contra Genesis con la misma receta de sampling.

## Lectura por subsistema

- **Coding/modelo:** es la oportunidad principal. LiveCodeBench y SWE-bench
  hacen plausible probarlo, pero el SWE publicado ya pierde 7,2 puntos frente
  al BF16 y no se compara directamente con SOL ni con nuestras recetas.
- **Computer Use:** puede evaluarse como decisión de herramientas, pero el
  control Genesis ya marca 100% en el fixture de 48 estados. Sólo sería útil si
  conserva calidad/seguridad y mejora latencia o generaliza a una prueba E2E con
  visión y herramientas reales.
- **Harness:** no hay base para cambiar el HarnessSpec, el orden de prompt ni
  los guardrails. Las métricas del modelo no cambian la autoridad del host, la
  validación de argumentos o las aprobaciones.
- **Ingi Charla:** no aplica. El artefacto es texto/imagen; no incluye ASR, TTS
  ni evaluación acústica. No reemplaza los perfiles de voz ya probados.

## Decisión provisional

No modificar perfiles ni harness sin terminar las pruebas locales. Mantener los
resultados del publicador separados de las mediciones LlamaCode. La evaluación
de carga, coding, Computer Use y visión queda pendiente hasta completar la
descarga; esta limitación de transferencia no es un fallo de calidad del modelo.
