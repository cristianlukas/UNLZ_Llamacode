# Matriz iterativa de perfiles — 2026-09-14

Esta es la consolidación de la campaña de validación solicitada para los
perfiles curados de LlamaCode. Se combinaron las mediciones históricas que
siguen siendo reproducibles con una repetición nueva en Ubuntu, usando el
binario CUDA `llama.cpp-phase-prefill-e06`, dos RTX 3090 con P2P habilitado y
el Ryzen 9 9950X3D.

## Criterio de lectura

- **PP** es prompt processing (`prompt_tps`), y **TG** es generación (`decode
  t/s`). No se mezclan con throughput agregado de varias solicitudes.
- `TTFT corto` es el tiempo de evaluación del prompt corto del barrido; no es
  el TTFT completo de una sesión con contexto largo.
- Una ventana que carga y responde a un smoke no demuestra que el contexto
  profundo sea correcto. Para marcar una ventana como operativa también se
  exige salida válida y ausencia de abortos.
- `histórico` identifica una medición anterior con el artefacto/runner exacto
  documentado, pero no repetida en esta campaña.
- Visión se marca sólo cuando hubo imagen real y respuesta verificable. Un
  `mmproj` que carga no alcanza para validar visión.

## Campaña nueva reproducible

Se ejecutó `tools/context_tps_matrix.py` con un prompt de código determinista,
96 tokens máximos, `temperature=0`, una solicitud por servidor y reinicio del
servidor para cada ventana.

| Variante | Ventanas | PP observado | TG observado | TTFT corto | Salida | Resultado |
|---|---|---:|---:|---:|---|---|
| MINI, Q4, KV Q8 | 8K/32K/64K/131K | 715 frío; 1.954–2.061 después del primer arranque | 230,3–258,5 | 14,6–42,0 ms | Python válido en 4/4 | Operativo |
| LUNA, Ling Q6, KV Q8 | 8K/32K/64K/131K | 397,5–428,4 | 202,0–205,9 | 88,7–95,6 ms | Python válido en 4/4 | Operativo para texto; HE0 histórico sigue bloqueado |
| TERRA control, Q4, KV Q8, sin MTP | 8K/32K/64K/131K | 252,1–254,3 | 38,2–40,1 | 114,0–115,0 ms | Python válido en 4/4 | Control estable; no reemplaza la receta MTP4 |
| METEOR control, Q4, KV Q8, sin MTP | 8K/32K/64K | 257,9–296,7 | 138,4–147,7 | 97,7–112,5 ms | Python válido en 3/3 | Control estable; la cifra MTP alta queda histórica |
| QWEN38-Q8, Q8, KV Q8, sin MTP | 8K/64K/131K/262K | 160,0 / fallo / fallo / 144,2 | 23,3 / fallo / fallo / 23,2 | 181,2 / — / — / 201,0 ms | Python válido en 2/4 | **Inestable en 64K/131K**: SIGABRT dentro de CUDA fused RMS-norm |

Los artefactos JSON y logs quedan en:

- `artifacts/validation-20260914/mini-context-sweep.json`
- `artifacts/validation-20260914/luna-context-sweep.json`
- `artifacts/validation-20260914/terra-context-sweep-no-mtp.json`
- `artifacts/validation-20260914/meteor-context-sweep-no-mtp.json`
- `artifacts/validation-20260914/qwen38q8-context-sweep-no-mtp.json`

### Visión

Las rutas visuales no se midieron como si fueran equivalentes a texto: se
usaron controles separados con `mmproj`, contexto compatible y sin especulación
cuando el runtime no soportó combinar ambos caminos.

| Perfil/ruta | Ventana | PP | TG | Resultado visual |
|---|---:|---:|---:|---|
| SOL, vLLM AutoRound TP2/P2P | hasta 262K | no comparable con este binario | 74 narrativo / 102 código | Visión 4/4 validada; tool-use OK |
| QWEN35-A3B, vLLM TP2/P2P | hasta 262K | no comparable con este binario | 123,98 BCB / 134,4 directo | Visión 4/4 validada |
| TERRA, ThinkingCap | 64K | ~146,1 en control | ~39,0 en control | Smoke visual válido; MTP4 aceptación 4/4 |
| METEOR, BigBang sin MTP | 64K | — | 61,69 en control visual | 1/1 válido; no transferir la cifra MTP histórica |
| QWEN38-VISION, Qwen3.8 Q4 sin MTP/KV Q4 | 32K | 135,48 | 23,48 | 1/1 válido; es variante separada de QWEN38-Q8 |
| ASTRA, Flash-Next + `mmproj` oficial | 196K/262K | carga del proyector | — | No validada: GPU aborta en `mtmd`; CPU devuelve `/` repetido |

## Tabla final actualizada

| Puesto | Perfil / configuración | Contextos medidos y estado | PP | TG | TTFT corto | HE0 / HE20 / BCB | Visión / MTP | Estabilidad y uso |
|---:|---|---|---:|---:|---:|---|---|---|
| 1 | **SOL** — Qwen3.8-27B AutoRound INT4, vLLM TP2/P2P, KV FP8 | 262K validado; 200K recomendado | Prefill vLLM 1.166 @10K / 942 @90K | 74 narr. / 102 código | 152 ms vLLM | 1/1 · 20/20 · **8/8** | Visión **4/4**; MTP4 | Principal para coding, agentes y tool-use |
| 2 | **GALACTA** — DeepSeek V4 Flash IQ3_S, KV Q4 | 131K histórico | no repetido en esta campaña | 9,65 histórico | no comparable | 1/1 · 20/20 · **8/8** | Texto-only | Máxima calidad validada; muy lento |
| 3 | **DEEPSEEK FUSION** — DeepSeek Fusion IQ3/Q4, KV Q4 | 131K histórico | no repetido | 10,55 histórico | no comparable | histórico 8/8 | Texto-only | Alternativo; la variante exacta debe tratarse como histórica |
| 4 | **QWEN35-A3B** — Qwen3.6-35B-A3B AutoRound INT4, vLLM TP2/P2P, KV FP8 | 262K validado; recuperación 240.660 | no comparable | 123,98 BCB / 134,4 directo | no reportado | HE20 20/20 · **BCB 4/8** | Visión **4/4** | Mejor opción multimodal/concurrencia; no supera a SOL en calidad agentiva |
| 5 | **QWEN38-Q8** — Qwen3.8-27B UD-Q8_K_XL, KV Q8, **sin MTP** | 8K y 262K smoke; 64K/131K abortan con esta build | 160,0 @8K / 144,2 @262K | 23,3 @8K / 23,2 @262K | 181 / 201 ms | directo **8/8**; LC-H1 pendiente | Visión sólo en QWEN38-VISION, no en esta ruta | Fidelidad/contexto; experimental e inestable en ventanas intermedias |
| 6 | **TERRA** — ThinkingCap Qwen3.6-27B Q4, MTP4, KV Q8 | 32K–262K histórico; perfil recomendado 64K | 252–254 control sin MTP | **56–58 histórico MTP4**; 38–40 control sin MTP | 114–115 ms control | 1/1 · 20/20 · **6/8 histórico** | Visión 2/2; MTP4 aceptación 4/4 | Mejor ruta de razonamiento/visión local; 64K diario |
| 7 | **ASTRA** — Qwen3.8 Flash-Next UD-Q4_K_XL, cache experto 188, KV Q8 | 32K/64K/131K/196K medidos; 262K cargable/smoke | no confiable | 16–41 histórico; MTP 4,8–5,7 con corrupción | no comparable | HE0/BCB inválidos | `mmproj` exacto no produce visión utilizable; MTP descartado | Sólo experimental para contexto; no agente |
| 8 | **NINFER-QWEN38** — Qwen3.8-27B `.ninfer`, MTP3, INT8 KV | 120K probado / 131K operativo | no comparable | 73–75 @8K; 50–63 @80–120K | no reportado | 1/1 · — · **3/8** | Sin `mmproj` compatible | Reparado, pero no reemplaza SOL |
| 9 | **METEOR** — BigBang Q4_K_M, ruta MTP histórica y control sin MTP, KV Q8 | 8K/32K/64K nuevo; 64K recomendado | 258–297 control | **211,18 histórico MTP**; 138–148 control | 97,7–112,5 ms | 1/1 · 20/20 · **3/8 histórico** | Visión 1/1 sin MTP; 61,69 | Throughput/lotes; calidad parcial |
| 10 | **LUNA** — Ling 3.0 Tiny Q6, KV Q8 | 8K/32K/64K/131K nuevo; 131K operativo | **397–428** | **202–206** | 88,7–95,6 ms | salida válida 4/4 · HE0 histórico **0/1** · BCB bloqueado | Texto-only | Auxiliar rápido; no agente principal hasta cerrar HE0 |
| 11 | **MINI** — MiniCPM5-2B Q4, KV Q8 | 8K/32K/64K/131K nuevo | 1.954–2.061 estable después de frío | **230–258** | 14,6–15,4 ms estable | **HE0 1/1 · BCB 1/8** | Sin `mmproj` validado | Mejor auxiliar rápido; no coding principal |

## Correcciones aplicadas

1. QWEN38-Q8 dejó de lanzar MTP2+KV Q8 automáticamente. La receta guardada
   queda sin MTP y sin `tensor-split` experimental; el perfil sigue siendo
   experimental por los abortos 64K/131K.
2. La tabla ya no presenta como equivalentes los TG históricos de MTP y los
   controles sin MTP, especialmente en TERRA y METEOR.
3. ASTRA no recibe visión ni BCB artificial: el proyector oficial elimina el
   error de dimensiones, pero no el fallo de `mtmd`/la salida repetitiva.
4. LUNA y MINI reciben PP/TG nuevos de cuatro ventanas, pero no se eleva su
   calidad agentiva: la velocidad no sustituye HE0/BCB.
5. SOL y QWEN35 mantienen su validación visual sólo en la receta vLLM/AutoRound
   TP2/P2P exacta; no se transfiere automáticamente a un fallback GGUF.

No se modificaron pesos ni Windows. Al terminar la campaña no quedaron
servidores `llama-server` activos.
