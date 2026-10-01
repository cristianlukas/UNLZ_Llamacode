# Victoria y Maple — revisión del hallazgo de Reddit

Fecha: 2026-09-30. Estado: **Victoria evaluada localmente; no supera los perfiles vigentes. Maple no es ejecutable en el hardware/runtime local revisado.**

## Hipótesis y decisión final

El post aporta una hipótesis útil para un perfil de coding: podar expertos de Qwen3.8-Flash-Next no basta; Victoria atribuye la recuperación de calidad al entrenamiento posterior al pruning y a 4 bits, usando al modelo sin podar como teacher. Esa hipótesis ya se contrastó con el GGUF publicado en nuestra máquina. Victoria cargó, pero no superó SOL en BCB-Hard-8 y quedó por debajo de Genesis en Computer Use; no se cambia ningún perfil ni el harness. Maple no sirve como reemplazo de Ingi Charla ni como perfil general: es NVFP4 para B200/B300, prioriza jurisdicción canadiense y no publica GGUF.

## Qué afirma cada fuente

- [Post de Reddit](https://www.reddit.com/r/LocalLLM/comments/1wtlbhp/two_openweights_releases_victoria_qwen38flashnext/): el autor añade en comentarios que el pruning dañó mucho el rendimiento y que lo recuperó con entrenamiento continuado sobre millones de tokens generados por el teacher BF16 sin podar. Es la hipótesis de entrenamiento que vale la pena contrastar; no es un resultado local nuestro.
- [Tarjeta de Victoria](https://huggingface.co/rmonsurate/Victoria): elimina 224 de 512 expertos por capa (44%), mantiene 5,9B parámetros activos, y atribuye la recuperación a entrenamiento a 4 bits. En NVFP4/vLLM sobre una B300 informa 70,0% avg@3 en Terminal-Bench 2.1; la tabla separa tres corridas de 75,3%, 68,5% y 66,3%. La build GGUF Q4_K_M informa 75,28% en una sola corrida y 93,2% avg@5 en HumanEval. Son checkpoints distintos: la tarjeta aclara que el GGUF es anterior al NVFP4 actual.
- La misma tarjeta atribuye 279,6 tok/s con draft head a una B300 y 50 prompts de coding/agentic. No se traslada esa cifra a las RTX 3090 ni se toma como medida de calidad.
- La build GGUF lleva un draft head de 32 tensores que la tarjeta dice que la rama principal de llama.cpp rechaza (`expected 1256, got 1224`); remite al fork `rmonsurate/llama.cpp`. La [PR upstream #27836](https://github.com/ggml-org/llama.cpp/pull/27836) para agregar el draft head aparece como **Draft**, no como soporte integrado. Nuestra corrida local usó el fork fijado a `1d8de7c1b0c7d2febf8f983174d8e6a711e2b1af`; no se debe asumir compatibilidad de cualquier build por el solo hecho de aceptar la arquitectura `qwen4exp`.
- [Repositorio oficial de Qwen3.8-Flash-Next](https://github.com/QwenLM/Qwen3.8-Flash-Next) describe el modelo base como 125B parámetros más 51B de embeddings n-gram y 6B activos por token. Victoria conserva los expertos activos, pero no elimina el costo de los embeddings n-gram.
- [REAP](https://github.com/CerebrasResearch/reap) ofrece un criterio reproducible de pruning que pondera la compuerta del router y la norma de activación de cada experto. Por sí solo no demuestra una mejora de LlamaCode; el entrenamiento posterior de Victoria es parte esencial de la hipótesis.
- [Tarjeta de Maple](https://huggingface.co/rmonsurate/Maple): es una adaptación de Victoria para contestar preguntas no localizadas desde Canadá, requiere búsqueda para citar fuentes oficiales y sólo publica NVFP4/vLLM para B200/B300. En los 600 casos held-out reporta 21,8% de respuestas que pasan todos los criterios con búsqueda, con evaluación de dos jueces IA y sin revisión humana. La tarjeta consultada no publica la cifra de 62,9% de citas oficiales mencionada en Reddit. No existe build GGUF.

## Evidencia local que se conserva y no se repite

El checkpoint **Swift Genesis no es Victoria**. Sus resultados sirven como referencia de nuestro hardware y harness, no como resultado sustituto de la build candidata:

| Prueba existente | Resultado guardado | Lectura para esta evaluación |
|---|---:|---|
| LC-H1, Genesis, 2026-09-29 | HE20 20/20 en 759 s; BCB8 2/8 en 417 s | Falla el gate de coding frente a SOL (HE20 20/20 y BCB8 8/8). No repetir Genesis con el mismo harness/dataset. |
| BCB-Hard-8 directo, Genesis | 1/8 en el runner de endpoint; el recibo LC-H1 dio 2/8 | El harness de agentes es la referencia final; no mezclar los dos protocolos. |
| Contrato de tools, Genesis | 5/5 pasadas `read_file` → `write_file` | Confirma contrato básico, no calidad de coding. No repetir esta receta para Genesis. |
| Computer Use easy + hard, Genesis | 48 tareas × 5 pasadas × 2 semillas; 720 requests. Las tres variantes dieron 100% de decisión/validez/seguridad/transporte. Medianas: state-first 654,84 ms; question-first 633,73 ms; sandwich 795,47 ms. | El gate no promovió sandwich por latencia (+21,5% vs state-first). No repetir esta matriz para Genesis. |
| Decode corto, Genesis | 56,35 tok/s mediana, contexto asignado 64K, MTP4, reasoning apagado | No es una ventaja sobre SOL (~74 narrativo / ~102 coding); tampoco es comparable con B300. |
| Swift Q4_K_M y REAP-320 Q3, campañas previas | Ambos 1/8 en BigCodeBench-Hard local | Son checkpoints distintos. No repetir sus descargas o corridas; sirven para explicar por qué una cifra externa de pruning no basta. |

Fuentes locales: [`docs/swift-genesis-qwen38-evaluation-20260929.md`](swift-genesis-qwen38-evaluation-20260929.md), [`docs/swift-qwen38-audit-20260914.md`](swift-qwen38-audit-20260914.md) y [`docs/reap320-qwen38-flash-next-audit-20260914.md`](reap320-qwen38-flash-next-audit-20260914.md). Los resultados y recibos Genesis están en `artifacts/swift-genesis-evaluation-20260929/`.

## Evaluación nueva de Victoria

Esta prueba usa otro checkpoint, así que reutilizar BCB-Hard-8 y Computer Use permite comparar con los controles locales sin fingir que son una corrida previa de Victoria. Se registra aquí el checkpoint, protocolo y cada resultado para que una continuación no repita una etapa completada.

- Hardware local disponible: 2× RTX 3090 de 24 GB y 123 GiB de RAM; build CUDA local del fork fijada en `rmonsurate/llama.cpp@1d8de7c1b0c7d2febf8f983174d8e6a711e2b1af`.
- Artefacto pedido: `rmonsurate/Victoria`, GGUF `victoria-s410-bitexact-tbl8-*-of-00003.gguf` (Q4_K_M, descarga declarada 107,2 GB). Se descarga fuera del repo a `models/Victoria-Qwen3.8-Flash-Next-GGUF/` para no mezclar los shards con los artefactos fuente.
- Se descargaron los tres shards GGUF tbl8 declarados (107,2 GB) y se cargaron con el fork indicado. La configuración fue contexto 16K, K/V Q8, dos RTX 3090, `--n-cpu-moe 20`, `--split-mode layer` y `--tensor-split 1,1`. El servidor quedó healthy; una generación smoke respondió `7` en 0,652 s.
- BCB-Hard-8 usó el mismo pack fijado en `artifacts/bigcodebench-hard-ubuntu-8.json`, con temperature 0,6, top-p 0,95, top-k 20 y hasta 6144 tokens. Se preserva el recibo completo en `artifacts/victoria-maple-audit-20260930/bcb_hard_8.json`.
- Aunque Victoria no pasó BCB8, sí se corrió una pasada del contrato Computer Use easy+hard (48 tareas) porque es una capacidad distinta de coding. También se corrió cinco veces el contrato read→write de tools. No se ejecutó LC-H1 completo: el filtro de calidad quedó muy lejos de SOL y las suites previas de Genesis ya cubren el caso de harness completo.
- Ingi Charla queda fuera de esta campaña: la mejora publicada es coding/agentic; ni Victoria ni Maple aportan una prueba local de ASR/TTS o latencia de voz. Maple además está especializada para una jurisdicción que no corresponde a Argentina.

### Resultados de Victoria

| Prueba | Resultado | Comparación / lectura |
|---|---:|---|
| Carga y health | Carga correcta; health OK | Compatible con el fork `qwen4exp-mtp`; no con la build mainline indicada por la tarjeta. |
| Smoke | `3 + 4 = 7`; 0,652 s | Generación funcional. |
| BigCodeBench-Hard-8 directo | **1/8**, transporte 8/8; mediana 20,94 s/request | SOL tiene 8/8 en el mismo pack local. No se justifica correr HumanEval/LC-H1 para promoción. |
| Contrato básico de herramientas | **5/5**, transporte 5/5; mediana 1,77 s en primera llamada y 1,66 s en segunda | Puede emitir el par read→write sencillo; coincide con Genesis (5/5), no es una mejora. |
| Computer Use easy | **18/24**; seguridad 5/8; mediana 4,05 s | Inferior a Genesis, que logró 100% en la matriz de 720 requests; la mediana es ~6,2× mayor que los 654,84 ms de Genesis/state-first. |
| Computer Use hard | **11/24**; seguridad 9/21; mediana 4,67 s | Los casos sin `tool_call` fueron un fallo frecuente; seguridad insuficiente para automatización. |
| Computer Use combinado | **29/48**; seguridad **14/29**; transporte 48/48 | No cambiar prompts, perfil de desktop ni harness. La prueba fue una pasada/seed 42, suficiente para descartar una promoción, no para estimar una capacidad estable. |

Los artefactos completos están en `artifacts/victoria-maple-audit-20260930/`: `smoke.json`, `bcb_hard_8.json`, `tool_contract_5.json` y `computer_use_48.json`. Los runners reutilizados de la evaluación Genesis son `artifacts/swift-genesis-evaluation-20260929/run_bcb.py`, `run_tool_contract.py` y `run_computer_use_production_contract.py`; no se volvieron a ejecutar con Genesis.

## Efecto sobre perfiles y harness

No promover Victoria ni Maple. Mantener SOL como control/default de coding. Victoria no supera SOL en BCB y queda por debajo de Genesis en Computer Use, con mediana de latencia varias veces mayor; el contrato básico de tools ya estaba en 5/5 con Genesis. No hay evidencia para tocar el harness, el perfil de computer-usage o Ingi Charla. No trasladar al perfil cifras de Terminal-Bench, B300 o reducción de tokens que no se reprodujeron en nuestro runtime y tareas.

El checkpoint Victoria usado fue GGUF Q4_K_M tbl8 y no el NVFP4 más nuevo de la tarjeta. Tras guardar los recibos se borraron los tres shards descargados (107,2 GB) y el servidor de prueba para recuperar espacio; el GGUF no queda disponible localmente. No descargar de nuevo este mismo artefacto ni repetir estas cuatro pruebas sin cambio de checkpoint, runtime o corpus. Mantener los JSON locales como recibo reproducible.

### Reutilización de esta evaluación

La solicitud del 2026-10-01 no requiere una segunda campaña: el mismo checkpoint, fork, hardware y protocolos ya se probaron el 2026-09-30. No repetir el smoke, BCB-Hard-8, contrato de tools 5× ni Computer Use easy+hard 48 tareas/seed 42. Reabrir la evaluación sólo si cambia el checkpoint (por ejemplo, la build NVFP4 actual frente al GGUF anterior), el runtime/compatibilidad MTP o el corpus. Maple sigue sin una prueba local porque no hay GGUF y el formato publicado requiere Blackwell; una prueba de Ingi Charla tampoco está justificada sin una variante con ASR/TTS y una hipótesis de latencia de voz. Las cifras externas de Terminal-Bench, HumanEval y throughput en B300 no sustituyen esas pruebas locales.

La única idea técnica para conservar es metodológica: cuando se evalúe otro modelo podado, probar el checkpoint completo que incorpora la recuperación posterior al pruning y separar resultados por variante/runtime. El resultado de este GGUF no da motivo para incorporar REAP, cambiar el prompt de Computer Use, ni alterar los perfiles de coding o voz.
