# Tabla final de benchmarks y recomendaciones

Fecha de corte base: 2026-08-24; auditoría post-campaña: 2026-08-28; actualización
manual DeepSeek nativa: 2026-08-30; actualización Ubuntu/Qwen: 2026-09-06.
**Corte operativo de esta tabla: 2026-09-23.**

Este documento consolida los resultados persistidos disponibles. La campaña
completa del catálogo sigue pausada: la instrumentación de memoria fue corregida
y pasó el gate de 77/77 tests, pero no se reejecutó todo el catálogo. ASTRA sí
tiene una campaña LC-H1 dedicada y reproducible documentada en su fila y en
`docs/qwen38-flash-next.md`; no presento como nuevos resultados las corridas
inválidas por infraestructura.

El catálogo fuente contiene perfiles base y variantes declarativas. En la
campaña post-corrección, LlamaCode reportó **86 perfiles `benchmark=true`
listos**. La campaña del 2026-08-28 llegó hasta el perfil 58/86 antes de
detenerse intencionalmente; sus resultados parciales, descartes y el inventario
fila por fila se detallan en
[`benchmark-profile-ledger-2026-08.md`](benchmark-profile-ledger-2026-08.md).
La tabla de abajo sigue siendo el resumen de promoción; no pretende reemplazar
el ledger ni convertir perfiles no alcanzados en descartados.

## Registro adicional — KV streaming Qwen3.8 (2026-08-29)

Se agregó `sys-bench-qwen38-kvstream-24gb-131k` al listado como perfil
experimental **SUPERIOR en ejecución sintética de contexto largo**: el fork
Windows `sachin-detrax/llama.cpp-adaptive-kv-streaming` (`11a01c8`) completó
8k, 32k, 64k y 131k con Qwen3.8 UD-Q4, una RTX 3090 de 24 GiB, K=`q8_0`,
V=`q4_0`, B/U=`256/256` y pool de 2048 MiB, dejando ~4,7 GiB libres en 131k.
Queda **INFERIOR en latencia larga** (decode ~36,0 tok/s en 8k → ~5,25 en
131k) y no desplaza los perfiles activos: el probe de passkey no obtuvo salida
exacta y la calidad queda sin validar. Es manual-only, texto-only, una GPU y un
slot; no se ofrece como default ni como perfil de visión/MoE.

## Cómo leer la tabla

- HE0, HE20 y BCB son los scores de cada etapa; BCB se expresa sobre 8 casos.
- `TPS BCB` es la velocidad media de la etapa BCB, no la velocidad de cola ni
  la de un prefijo repetido.
- `Tiempos HE0 / HE20 / BCB` son tiempos de etapa en segundos. Cuando se usa
  un tiempo E2E consolidado de una tabla de candidatos, se indica explícitamente.
- `*` significa que el score apareció en una corrida con evidencia de
  infraestructura posterior o mezcla de intentos; no se usa para promover un
  perfil.
- Las filas con `—` no deben leerse como calidad cero: no tienen una medición
  BCB comparable y necesitan reintento.
- Las velocidades marcadas como `directo`, `smoke`, `BCB` o `visión` pueden
  provenir de protocolos distintos y no son comparables automáticamente. Sólo
  los resultados **LC-H1** usan el mismo harness agentivo; en particular, la
  velocidad de ASTRA a 256K y su BCB directo histórico no son la misma medición.

## Modelos generativos disponibles

Esta es la tabla operativa completa. Separa identidad del modelo, receta de
ejecución, evidencia de calidad y estado de promoción. En ASTRA se mantienen
separadas la velocidad de decode, el BCB directo histórico y la nueva campaña
LC-H1 exacta.

| Modelo / perfil | Ubicación y tamaño | Velocidad local | Calidad / estabilidad | Contexto | Visión | Estado | ¿Reemplazado? |
|---|---|---|---|---|---|---|---|
| **SOL** | C y copia duplicada en D · ~18 GB c/u | 74 narr. / **102 código TG** | **BCB 8/8**, HE20 20/20, tool-use estable | **262K** | 4/4 | Default principal | **No** |
| **ASTRA** | D · ~74 GB GGUF + RAM | **47,14 TG @256K**; 53,68 @128K. **BCB directo: ~30,3 TG** con `n-cpu-moe 40` | **LC-H1 exacto:** HE0 1/1; HE20 20/20; BCB 8/8; 87 tool calls, 86 exitosos. BCB directo histórico separado | **256K cargable; needle/passkey 4/4 al 25/50/75/95%** | No validada | MoE/contexto largo experimental; LC-H1 completado, comparación directa con SOL pendiente | **No** |
| **OCCAMY** | C · ~21,2 GB + mmproj | 233 PP / 164 TG @8K; 163 TG @262K | BCB 3/8; HE0 1/1; HE20 20/20; tool-use válido | **262K** | Funcional | Multimodal experimental fuerte | **No** |
| **QWEN35-A3B** | D · ~21,5 GB | 123,98 BCB / 134,4 TG | BCB 4/8 histórico; 1/8 directo; HE0 1/1 | **262K** | 4/4 | Visión y concurrencia | **No** |
| **QWEN38-SHAPELEARN** | C · ~13,1 GB + mmproj | 53,6 TG @8K; **66,2 @262K**; 77,9 HE20 | HE0 1/1; HE20 20/20; BCB bloqueado por salida previa a tools | **262K** | Funcional con MTP3 | Contexto/fidelidad experimental | **No** |
| **METEOR / BigBang** | D · ~22,8 GB + mmproj | **207 texto / 195,3 visión TG** | BCB 3/8 histórico; 2/8 directo; HE0 1/1 | 64K | Funcional | Throughput y lotes | **No** |
| **Qwen3.6-35B-A3B GGUF MTP** | D · ~23,7 GB + mmproj | 140,2 base / **207,8 MTP** | Calidad agentiva no cerrada; MTP+visión inestable | Inferior a AutoRound | Sólo sin MTP | Legacy | **Parcial** |
| **GSQ-RCO + DFlash2 Q2** | C · ~12,1 GB + drafter 536 MB | 67,7 corto / 25 @8K / 52,1 visión | HE0 1/1; HE20 cancelado; BCB no iniciado | 81,9K config. / 9,6K probado | Funcional | Laboratorio DFlash2 | **No** |
| **Qwen3.5-9B MTP** | D · ~5,9 GB + mmproj | 166,1 / 144,2 visión TG | BCB 1/8; HE0 1/1; HE20 19/20 | 8K probado | Funcional | Auxiliar potente | **No global** |
| **Qwen3.5-4B MTP** | D · ~2,8 GB + mmproj | 200 / **206,6 visión TG** | BCB 1/8; HE0 1/1; HE20 20/20 | 8K probado | Funcional | Auxiliar equilibrado | **No** |
| **Qwen3.5-2B MTP** | D · ~1,3 GB + mmproj | **318,9 / 344,8 visión TG** | BCB 0/8; HE0 0/1 | 8K probado | Funcional | Auxiliar ultrarrápido | **No** |

> **SOL = Qwen3.8-27B**. La receta DSH medium de 54,74 tok/s es histórica; la
> receta actual principal es AutoRound/vLLM TP2/P2P, con 74 narrativo / 102
> código.

`SOL · DSH medium` corresponde a **Qwen3.8-27B UD-Q4_K_XL** con Dynamic V3,
DSH medium y MTP2; sus 54,74 tok/s y BCB 8/8 son una referencia histórica de
esa familia, no una segunda identidad de modelo.

### Comparación específica de Occamy

En decode aislado, Occamy queda por encima de QWEN35-A3B y CyberTiel en las
recetas locales disponibles, y por debajo de METEOR en throughput bruto. Su
ventaja adicional es que mantiene aproximadamente 163 TG a 262K y 163 TG con
visión a 32K, sin depender de MTP. Eso lo convierte en el candidato
experimental más interesante para visión y throughput multimodal.

No se lo promueve sobre SOL: ASTRA ya completó HE0 → HE20 → BCB8 y retrieval
LC-H1, pero todavía falta una corrida A/B de SOL y ASTRA con idénticos prompts,
sampling, reparaciones y timeouts.

ShapeLearn queda por encima de QWEN38-Q8 en velocidad local: **66,24 TG frente
a 22,1 TG a 262K**, usando MTP3 y manteniendo el contexto estable. También es
preferible a ASTRA ASCII/P1M para uso multilingüe porque conserva el vocabulario
completo. La ausencia de una comparación A/B directa con SOL impide promoverlo
sobre SOL.

## Perfiles base activos ya consolidados

| # | Perfil | GGUF / familia | HE0 | HE20 | BCB | TPS BCB | Tiempos HE0 / HE20 / BCB (s) | Estado consolidado |
|---:|---|---|---:|---:|---:|---:|---:|---|
| 1 | ULTRA-Q DeepSeek V4 Flash IQ3_S 131k, sin DSpark | DeepSeek V4 Flash UD-IQ3_S | 1/1 | 20/20 | 8/8 | 9,65 | 216,2 / 1.557,8 / 2.830,6 | Único DeepSeek con BCB completo válido; muy lento |
| 2 | DeepSeek V4-7-8-26, sin speculative | DeepSeek V4 | 1/1 | 19/20 | — | — | 138,7 / 1.597,1 / — | HE20 parcial; BCB no comparable |
| 3 | Laguna S 2.1 CUDA safe 64k | Laguna S Q2_K_XL | 1/1 | 20/20 | — | — | 194,9 / 1.069,5 / — | BCB pendiente/bloqueado por timeout |
| 4 | Qwen3.8 Q4_K_M 131k | Qwen3.8-27B Q4_K_M | 1/1 | 20/20 | 5/8 | 53,83 | 27,3 / 265,3 / 603,4 | Calidad parcial; candidato 24 GB |
| 5 | Qwen3.8 Q5_K_M 131k | Qwen3.8-27B Q5_K_M | 1/1 | 20/20 | 3/8 | 47,13 | 28,3 / 314,5 / 293,0 | Calidad parcial; más pesado que Q4 |
| 6 | KAT Coder Q4 | KAT Coder | 1/1 | 20/20 | 3/8 | 111,77 | 40,1 / 250,2 / 639,3 | Rápido, pero BCB inestable en reintentos |
| 7 | BigBang MTP, perfil activo | BigBang | 1/1 | 20/20 | 4/8 | 39,35 | 48,7 / 267,2 / 252,1 | Calidad parcial; no confundir con METEOR reparado |
| 8 | ThinkingCap Qwen3.6 MTP4 | Qwen3.6-27B | 1/1 | 20/20 | 6/8 | 56,84 | 27,9 / 228,8 / 298,8 | Candidato LUNA; baja latencia |
| 9 | Laguna S fit 100k, agent máximo | Laguna S Q2_K_XL | 1/1 | 20/20 | 0/8 | 22,14 | 130,1 / 488,8 / 241,8 | Calidad insuficiente; no recomendar |
| 10 | DeepSeek Fusion leloch | DeepSeek Fusion | 1/1 | 20/20 | 4/8* | 8,57–9,45 | 180,5 / 1.175,7 / 1.396,9–7.169* | Parcial y muy lento; requiere reparación |
| 11 | DeepSeek Fusion leloch, VRAM balance | DeepSeek Fusion | 1/1 | 20/20 | 2/8 | 9,45 | 135,4 / 1.249,7 / 6.328,8 | Experimental; no promocionar |
| 12 | DeepSeek Fusion, expertos 0–2 | DeepSeek Fusion | 1/1 | 20/20 | 3/8 | 8,71 | 163,2 / 1.225,4 / 1.263,9 | Experimental; reparto de expertos costoso |
| 13 | Laguna S CUDA safe 65k | Laguna S Q2_K_XL | 1/1 | 20/20 | 4/8 | 50,54 | 52,4 / 231,1 / 911,1 | Calidad parcial |
| 14 | Laguna S fit 100k | Laguna S Q2_K_XL | 1/1 | 20/20 | 0/8 | 0,21 | 123,1 / 658,9 / 66,5 | Calidad insuficiente |
| 15 | Laguna S dual GPU safe 32k | Laguna S Q2_K_XL | 1/1 | 20/20 | 4/8 | 44,33 | 52,1 / 663,4 / 871,6 | Calidad parcial; contexto largo experimental |
| 16 | Qwen3.8 MTP separado 131k | Qwen3.8 UD-Q4_K_XL | 1/1 | 20/20 | 8/8 | 55,17 | 30,0 / 259,5 / 365,9 | Uno de los mejores controles limpios |
| 17 | Qwen3.8 KV Q8 MTP2 131k | Qwen3.8 UD-Q4_K_XL | 1/1 | 20/20 | 4/8 | 46,07 | 24,9 / 267,6 / 278,4 | KV Q8 no compensó en esta configuración |
| 18 | Qwen3.8 Browser Agent medium 131k | Qwen3.8 UD-Q4_K_XL | 1/1 | 20/20 | 8/8 | 71,51 | 53,3 / 211,3 / 369,1 | Candidato TERRA; E2E aceptado 592,5 s |
| 19 | Qwen3.8 Browser Agent xhigh 131k | Qwen3.8 UD-Q4_K_XL | 1/1 | 20/20 | 8/8 | 65,94 | 36,5 / 212,1 / 513,1 | Alta calidad de harness; más lento que medium |
| 20 | Qwen3.8 DSH medium 160k MTP2 | Qwen3.8 UD-Q4_K_XL | 1/1 | 20/20 | 8/8 | 54,74 | 13,3 / 215,1 / 661,7 | Candidato SOL; E2E aceptado 890,1 s |
| 21 | Qwen3.8 DSH medium 192k MTP2 | Qwen3.8 UD-Q4_K_XL | 1/1 | 20/20 | 8/8 | 55,11 | 14,0 / 227,1 / 403,6 | Máxima calidad/contexto; E2E documentado 644,7 s |
| 22 | Qwen3.8 MTP embebido 131k | Qwen3.8 UD-Q4_K_XL | 1/1 | 20/20 | 7/8 | 49,67 | 29,1 / 266,4 / 646,0 | Casi completo; inferior al MTP separado |
| 23 | Qwen3.8 MTP embebido 64k | Qwen3.8 UD-Q4_K_XL | 1/1 | 20/20 | 8/8 | 52,58 | 26,6 / 468,5 / 625,5 | BCB completo; contexto más corto |
| 24 | QWEN38-Q8 · UD-Q8_K_XL 262k · MTP2 | Qwen3.8 UD-Q8_K_XL | Smoke OK | No ejecutado | **8/8 directo** | **51,74 tok/s BCB directo** | — | Texto validado; agente LC-H1 pendiente; control visual OK sin MTP/KV Q4; MTP2+KV Q8+visión falla |

## Actualización post-corte: KAT APEX-MTP + Qwen mmproj (2026-08-28)

Estas corridas agregan evidencia funcional que no existía al cierre de la
tabla, pero no reemplazan el ranking consolidado: HE20 no quedó validado y la
compuerta de calidad bloqueó BCB. La referencia histórica de KAT sigue siendo
BCB **3/8**. El modelo sí merece entrar como **candidato experimental para
visión y contexto largo**, no como perfil SOL/TERRA/LUNA hasta completar
HE20 → BCB.

La receta común fue KAT-Coder-V2.5-Dev-MTP-APEX-i-quality-v2.gguf con
mmproj-F16.gguf, MTP2, KV `q8_0` en K/V, Flash Attention, `split-mode layer`,
`--skip-chat-parsing` y el parser XML de LlamaCode. En 32k, el smoke de tools
devolvió XML KAT válido (`read_file` + `README.md`), con 17/22 tokens MTP
aceptados y 113,01 tok/s de decode; `test_agent_wire` también pasó.

| Candidato | Evidencia de contexto | MTP / velocidad observada | Decisión |
|---|---|---|---|
| KAT APEX + mmproj · 64k | 47.622 tokens efectivos; marcador exacto; carga estable | 6/8 aceptados; prompt 903,50 tok/s; decode 103,08 tok/s | **Candidato experimental recomendado** para visión + herramientas con más contexto que 32k |
| KAT APEX + mmproj · 131k | 99.371 tokens efectivos; marcador exacto; carga estable | 8/8 aceptados; prompt 801,32 tok/s; decode 98,78 tok/s | **Candidato experimental recomendado** para contexto largo |
| KAT APEX + mmproj · 262k | La configuración 262.144 cargó; 199.856 tokens pasaron el marcador exacto. Una corrida cercana al límite procesó 244.505 tokens sin OOM, pero devolvió el marcador truncado | 7/8 en la corrida de 199k; cerca del límite, 4/4 y decode 39,89 tok/s | **Experimental / no promocionar todavía**: capacidad disponible, recuperación/calidad en el límite pendiente |

HE0 sí pasó 1/1 en 32k. El primer intento auxiliar de HE20 no produjo resultado
válido: el agente entró en anti-loop repitiendo lecturas (11 eventos de fallo
antes de cancelar). En la campaña oficial posterior sí quedaron persistidos dos
cortes completos de esta familia: MTP3 obtuvo 18/20 y 5/8 BCB, mientras el
control sin MTP obtuvo 19/20 y 1/8 BCB. Ambos son resultados de calidad parcial,
no reemplazan el ranking consolidado ni habilitan promoción. Los TPS anteriores
son smokes de contexto/tool calling, no `TPS BCB`.

### Control Q4 y sampling A/B (2026-08-28)

Como control comparable adicional, `sys-48-katcoder-262k` y su clon
`51d46758-fd7c-4d3c-8018-23154a2e0062` usaron Q4_K_M, K/V `q8_0`, contexto
262k, B512/U64, fit adaptativo, reasoning off, el mismo agente/harness y la
misma semilla. El control mantuvo `temp 0.60`, `top-p 0.95`, `top-k 20`,
`min-p 0.0`; el clon usó `temp 0.30`, `top-p 0.90`, `top-k 20`, `min-p 0.05`.

| Perfil | HE0 | HE20 | BCB | Estado para el listado |
|---|---:|---:|---:|---|
| KAT Q4 vigente, 262k | 3/3, 100%, sin reparación | 2/3 corridas completas; 18/20 primer intento | 3/8, 315,509 s, 84,18 tok/s, una pasada | **Speed-first experimental**; no desplaza calidad 8/8 |
| KAT Q4 sampling A/B, 262k | 3/3, 100%, sin reparación | 3/3 finales; 18/20 primer intento y 1 reparación por corrida | Sin resultado: BCB cancelado por un `llama-server` externo que ocupó puerto/GPU | **No promover aún**; falta BCB propio |

El A/B fue ~5,4% más rápido en warm HE0 (29,08 s vs. 30,66 s), pero ~29,3%
más lento en warm HE20 (253,81 s vs. 179,42 s en la métrica disponible) y
necesitó reparación en todos los HE20. Por ello se anotan las variantes 64k,
131k y 262k de APEX como candidatos experimentales en este listado, pero sólo
SOL/TERRA/LUNA/METEOR conservan promoción consolidada.

## Recomendación principal: SOL, TERRA, LUNA y METEOR

Estas etiquetas son decisiones de producto, no sólo un ranking por TPS. Pesan
calidad BCB, tiempo total, estabilidad, contexto y el tipo de trabajo.

| Tier | Perfil recomendado | Calidad BCB | Velocidad | Tiempo total medido | Mi opinión |
|---|---|---:|---:|---:|---|
| SOL | Dynamic V3 DSH medium · 160k · MTP2 | 8/8 | 54,74 tok/s | 890,1 s E2E | Mejor opción para calidad, contexto largo y tareas difíciles. |
| TERRA | Dynamic V3 Browser Agent medium · 131k | 8/8 | 71,51 tok/s | 592,5 s E2E | Mejor equilibrio general para uso diario, agentes y coding. |
| LUNA | ThinkingCap Qwen3.6 · MTP4 | 6/8 | 56,84 tok/s | 298,8 s E2E | Menor tiempo total; bueno para interacción rápida, aceptando menor calidad. |
| METEOR | BigBang MTP reparado | 3/8 | 211,18 tok/s | 670,8 s E2E | Máximo throughput; no lo usaría como modelo principal por su calidad parcial. |

### Nuevos perfiles para esta PC Ubuntu (2× RTX 3090)

Estos dos perfiles ya están agregados al catálogo. No reemplazan todavía las
etiquetas SOL/TERRA/LUNA/METEOR: sus mediciones Ubuntu incluyen rendimiento,
estabilidad de contexto y una muestra diagnóstica de código, pero la compuerta
oficial HE0 → HE20 → BCB sigue bloqueada después de HE0=0/1 en ambos. El nombre
“Qwen 28B” conserva la nomenclatura pedida;
el archivo instalado es el Qwen3.8-27B Q4_K_M.

| Perfil | Launch LlamaCode | Evidencia Ubuntu | Recomendación en esta PC |
|---|---|---|---|
| **MEJOR QWEN NEXT** | `175_MEJOR QWEN NEXT - Flash-Next Q4_K_XL · cache 188` | 41,31 tok/s decode, 54,05 tok/s prefill en 32k; contexto de arranque verificado hasta 196k; BCB diagnóstico 0/8, **45,24 tok/s medios** (41,06–47,05); MTP no recomendado todavía por el crash CUDA reproducible con expert-cache | Para contexto grande y chats donde importe la capacidad MoE; experimental, no lo usaría como default de coding hasta corregir la salida contaminada y validar calidad. |
| **MEJOR QWEN 28B** | `176_MEJOR QWEN 28B - Qwen3.8-27B Q4_K_M · MTP3` | 73,75 tok/s decode, 556,56 tok/s prefill, 83,7% de aceptación MTP; contexto de arranque verificado hasta 131k; BCB diagnóstico 0/8, **36,27 tok/s medios** (0,06–66,48) | Sigue siendo el default de velocidad para coding/chat, pero la promoción oficial Ubuntu queda pendiente: repetir HE0 → HE20 → BCB después de corregir la extracción de código. |

TPS de decode con petición corta y constante por nivel, medido por streaming y
`slot print_timing`: SOL 16,30/16,46/16,66/16,25 tok/s en 32K/64K/131K/196K;
TERRA 48,96/49,86/49,99 tok/s en 32K/64K/131K. SOL no arrancó en 262K y TERRA
no reservó memoria en 196K/262K. En la segunda corrida diagnóstica de los 8
casos BCB seleccionados, SOL dio 0/8 y 45,24 tok/s medios (41,06–47,05), y
TERRA 0/8 y 36,27 tok/s medios (0,06–66,48); ambos generaron código contaminado
con texto/fences y sintaxis inválida. No es un score BCB promocionable porque la
compuerta HE0 de ambos sigue en 0/1. El detalle está en el informe de comparación
Qwen Ubuntu y en `benchmark-runs/Ubuntu_8_official_code_tests_diagnostic_20260907_000138`.

El perfil Qwen 28B usa el draft MTP separado instalado en la carpeta `MTP/` y lo
envía a `CUDA1`. El perfil Qwen Next conserva cache de expertos 188 y expertos en
RAM; no mezcla MTP con esa cache hasta que la corrección de acceso ilegal de la
rama experimental quede validada.

### Accesos curados visibles en LlamaCode

Los cuatro accesos siguientes aparecen arriba de todo en Perfiles y en el selector
del servidor. Son alias operativos: no duplican los pesos ni cambian la tabla
histórica; apuntan a la receta que corresponde a cada criterio.

| Alias | Receta que ejecuta | Configuración principal | Cuándo elegirlo |
|---|---|---|---|
| **SOL** | Qwen Next | Flash-Next UD-Q4_K_XL, cache de expertos 188, expertos en RAM, 32k práctico | Contexto/MoE grande y tareas complejas; aceptar que es experimental. |
| **TERRA** | Qwen3.8-27B | Q4_K_M, MTP3 en `CUDA1`, KV q8, 32k práctico | Coding y chat diario; es la mejor elección de velocidad en esta PC. |
| **LUNA** | ThinkingCap Qwen3.6 | Q4_K_M, MTP4, 131k, mmproj y preset de baja latencia | Respuestas interactivas y razonamiento rápido. |
| **METEOR** | BigBang MTP reparado | Q4_K_M, MTP embebido, preset conservador de 64k/B256/U64 | Lotes y generación masiva; calidad BCB parcial. |

La decisión práctica queda así: **TERRA** es el default diario; **SOL** es el
perfil de mayor capacidad; **LUNA** prioriza tiempo de respuesta; y **METEOR** se
reserva para throughput. Los perfiles técnicos originales siguen disponibles
para A/B y benchmarks detallados.

### Mi orden de preferencia

1. **TERRA** como perfil por defecto: mantiene 8/8 y entrega la mejor
   combinación de velocidad y tiempo total.
2. **SOL** cuando importan más la profundidad, el contexto y la robustez que
   la latencia.
3. **LUNA** para respuestas interactivas y tareas donde 6/8 sea suficiente.
4. **METEOR** únicamente para lotes o generación masiva donde el throughput
   justifique sacrificar calidad.

## Perfiles recomendados por caso de uso

| Caso de uso | Recomendación | Motivo |
|---|---|---|
| Agente general con máxima calidad | SOL · DSH medium 160k MTP2 | 8/8 y contexto amplio; prioriza calidad. |
| Uso diario balanceado | TERRA · Browser Agent medium 131k | 8/8, 71,51 tok/s y tiempo E2E razonable. |
| Documentos muy largos | SOL · DSH medium 192k MTP2 | 192k manteniendo 8/8 y 55,11 tok/s. |
| Razonamiento con baja latencia | LUNA · ThinkingCap MTP4 | 298,8 s E2E y 6/8. |
| Máximo throughput o lotes | METEOR · BigBang reparado | 211,18 tok/s; calidad sólo parcial. |
| Navegación y uso de herramientas | TERRA · Browser Agent medium | Harness validado con 8/8. |
| Coding rápido | Qwen3.8 MTP separado 131k | 8/8 y 55,17 tok/s; más confiable que KAT en BCB. |
| Coding con razonamiento fuerte | Browser Agent xhigh 131k | 8/8 y mayor nivel de thinking, con penalización de tiempo. |
| Visión en 48 GB | Qwen3.8 UD-Q4 196k · MTP2 · KV Q8 · mmproj RAM | 8/8, 43,71 tok/s y 941,9 s E2E; especializado. |
| Visión + herramientas en 48 GB (experimental) | KAT APEX + Qwen mmproj · MTP2 · 64k · KV Q8 | XML KAT válido, mmproj funcional y recuperación exacta probada; HE20/BCB pendientes. |
| Visión con contexto largo (experimental) | KAT APEX + Qwen mmproj · MTP2 · 131k · KV Q8 | 99.371 tokens efectivos y marcador exacto; HE20/BCB pendientes. |
| Capacidad máxima de contexto (experimental) | KAT APEX + Qwen mmproj · MTP2 · 262k · KV Q8 | Configuración cargada y 244.505 tokens procesados sin OOM, pero recuperación degradada cerca del límite. |
| DeepSeek local | **BEST DeepSeek — DeepSeek V4 Flash IQ3_S sin DSpark** (`sys-48-dsv4-nospec`) | Único candidato IQ3_S con BCB 8/8 completo; superior en calidad a Fusion (2–4/8). Sigue siendo experimental para velocidad: 9,65 tok/s BCB histórico. |
| Qwen Next (Ubuntu) | **MEJOR QWEN NEXT** (`175_MEJOR QWEN NEXT - Flash-Next Q4_K_XL · cache 188`) | Máxima capacidad MoE/contexto en las dos 3090; 41,31 tok/s medidos, pero rama experimental y calidad Ubuntu pendiente. |
| Qwen 28B (Ubuntu) | **MEJOR QWEN 28B** (`176_MEJOR QWEN 28B - Qwen3.8-27B Q4_K_M · MTP3`) | Mejor opción local rápida: 73,75 tok/s medidos y 83,7% aceptación MTP; calidad heredada del control Qwen3.8, repetir BCB en Ubuntu antes de promoverlo. |

## Perfiles curados en LANZAR

Desde el 2026-09-08, **SOL queda como único perfil Qwen 28B prioritario visible**
en LANZAR. TERRA se conserva sólo como referencia histórica/benchmark y está
marcado como obsoleto en la configuración compartida, por lo que no aparece en
el dropdown.

La lista desplegable **LANZAR** muestra arriba de todo, en este orden fijo,
los perfiles curados `ASTRA`, `SOL`, `LUNA` y `METEOR`. El orden se
persiste con `menuOrder`, por lo que no cambia al usar otro perfil o al
reiniciar la aplicación. `ASTRA` usa Flash-Next Q2_K_XL, `n-cpu-moe 12`,
`tensor-split 1.4,1` y contexto 256K (47,14 tok/s medidos); `SOL` es
Qwen3.8-27B, con la referencia histórica DSH medium en 160/192K (54,74/55,11
tok/s y BCB 8/8), además de la receta vLLM TP2/P2P actualmente curada. LUNA y
METEOR conservan sus configuraciones anteriores.

## DeepSeek: conclusión

No todos los GGUF DeepSeek funcionan igual. El **IQ3_S sin DSpark** tiene la
calidad E2E más completa de la familia y queda marcado `BEST` dentro de
DeepSeek: BCB 8/8 frente a 2–4/8 de Fusion. No es el ganador universal de
velocidad: antirez conserva BCB histórico 8/8 a 10,548 tok/s, mientras que el
IQ3_S registra 9,645 tok/s.

La campaña local del 2026-08-30 probó IQ3_S, LID CUDA y antirez con b10228/b10331,
KV q4/q8, una/dos 3090 y distintos rangos de expertos. El mejor smoke nativo
IQ3_S fue 6,171 tok/s con 12 capas expertas residentes; antirez dio 8,280 tok/s
a 131k y 9,066 tok/s a 64k/KV q8. Son peticiones de 57 tokens con `ctx-size`
nominal, no decodes después de llenar 128k, y no reemplazan HE0/HE20/BCB.
LID verificó recuperación exacta hasta 262k; 524k/1M no quedaron verificados.
Los dos A/B antirez de 32k con reasoning off/low siguen retirados por latencia
no competitiva; el detalle completo está en la campaña fechada y enlazada desde
los documentos vivos.

## Familias retiradas o no promocionadas

| Familia | Decisión | Motivo |
|---|---|---|
| KAT APEX-MTP | Candidato experimental; todavía no promocionado | HE0 1/1 y visión/tool calling XML funcionales; HE20 quedó inválido por anti-loop, BCB bloqueado por la compuerta; 64k/131k pasaron smokes de recuperación y 262k mostró degradación cerca del límite. |
| Dynamic V3 DFlash2 local | Fuera de la cola activa | El loader falla por incompatibilidad de arquitectura/backend (`wrong number of tensors`, `FGDN_AR`). |
| Dynamic V3 DFlash2 vLLM | No local en Windows | Requiere endpoint vLLM parcheado y drafter externo; no es comparable en este entorno. |
| BigBang base / fast | No promocionados | Fallos históricos de HE0, CUDA o estancamiento; sólo se conserva el control reparado. |
| DeepSeek antirez B2048 | No promocionado | BCB terminó en `0/0` por timeout; se conserva como control para reintento. |
| DeepSeek Q3 / IQ3_S con DSpark | No promocionado | La ruta DSpark no es estable en llama.cpp/Windows; se conserva IQ3_S sin DSpark. |
| Variantes DeepSeek de reparto de expertos | No promocionadas | OOM, crashes o BCB incompleto; no hay ganancia evaluable que justifique promoverlas. |

## Próximo paso para una tabla definitiva post-corrección

La tabla anterior es la mejor consolidación de lo que ya se midió. Para
convertirla en una tabla final post-corrección, hay que reanudar la cola de a
un perfil, ejecutar HE0 → HE20 → BCB, registrar la telemetría fit-aware de
VRAM/RAM y repetir sólo los casos con timeout, estado de turno o backend
inestable. Hasta entonces, los números de SOL/TERRA/LUNA/METEOR son los
candidatos consolidados existentes y no una nueva campaña posterior al parche.

## Revalidación del harness Linux (2026-09-07)

La revalidación separa modelo, backend y argumentos por plataforma: Windows
conserva sus GGUF y opciones originales, mientras Ubuntu selecciona la variante
compatible con su build CUDA. Con `agent-browser` y razonamiento apagado durante
BCB:

| Perfil | HE0 | HE20 | BCB | TPS BCB | Estado |
|---|---:|---:|---:|---:|---|
| TERRA · Qwen 28B Linux Dynamic v3 | 1/1 | 20/20 | **8/8** | **70,37** | Validado; histórico 71,51 (-1,6%) |
| SOL · Qwen 28B Linux Dynamic v3 + MTP3 | 1/1 | 20/20 | **8/8** | **63,94** | Validado |
| ASTRA · Qwen Next cache 188 · 196K (histórico) | 0/1 | — | bloqueado | — | Receta Q4 retirada; sin tool-call válida y salida repetitiva |

La corrida anterior de ASTRA Q4 se probó con razonamiento apagado y encendido,
y con temperatura Linux 0,0; falló antes de crear el archivo evaluable. Esa
receta queda como antecedente histórico. La nueva ASTRA Q2 de 256K se documenta
en la tabla principal; ya cuenta con BCB agentivo LC-H1, aunque la resolución
`platformModelProfileIds` mantiene intacto el comportamiento de Windows.
