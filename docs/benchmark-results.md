# Resultados vivos de benchmarking

Este archivo es la tabla operativa vigente. Cada mejora de perfil, harness,
agente o infraestructura debe actualizar esta tabla y agregar una entrada en
[`benchmark-results-history.md`](benchmark-results-history.md).

Para el inventario completo por perfil —incluidos descartados, bloqueados,
retirados, binarios, quantizaciones, configuración efectiva, huellas y métricas
por etapa— consultar el [registro detallado de perfiles](benchmark-profile-ledger-2026-08.md).

Última actualización: 2026-10-03.

## 2026-10-03 — Gemma 4 E4B QAT y Spark-X2.5-4B: no promovidos

La comparación local contra Qwen3.5-4B no muestra un reemplazo integral.
Spark obtuvo **2/8** frente a **1/8** BCB-Hard directo, pero fue una sola
pasada; tool contract empatado 5/5, Computer Use sandwich 69/72 frente a 72/72
y sin visión. Gemma QAT tuvo 0/8 BCB, 4/5 tool contract y 3/3 en el fixture
visual. **No se cambia el perfil 4 GB, el harness, Computer Use ni Ingi-Charla.**
No reutilizar esas mismas corridas como evaluación nueva. Detalle por caso,
hashes y protocolo:
[`auditoría de modelos pequeños`](reddit-small-models-evaluation-20261003.md).

## 2026-09-30 — Ornith 1.5-9B + DFlash: no promovido

En RTX 3090/SM86 y el mismo `llama-server`, Ornith Q4_K_M subió de 82,04 a
132,70 tok/s con su draft DFlash Q4_K_M (`n=7`), +61,8%. El control Qwen3.5-9B
MTP3 dio 137,31 tok/s, Computer Use 48/48 y seguridad 29/29; Ornith quedó en
47/48 y 28/29, y el pack BCB-Hard de 8 tareas empató el 1/8 histórico de
Qwen3.5-9B. DFlash mantuvo las 48 decisiones exactas del Ornith target-only.
**No se cambia Ingi-Charla, Computer Use, el harness ni los perfiles.**
Detalle, comandos, hashes, artefactos y límite de evaluación de voz/visión:
[auditoría Ornith 1.5 9B + DFlash](ornith-1.5-9b-dflash-evaluation-20260930.md).

## Split tensor en 2× RTX 3090 (hilo LocalLLaMA "second 3090") · 2026-09-27

| Perfil | Evidencia (Windows, b10964, MTP3) | Clasificación / decisión |
|---|---|---|
| sys-bench-qwen38-byteshape-tensor-q8-mtp3-131k | Mismo GGUF ByteShape IQ4_XS + visión, `-sm tensor`, KV q8, 131K, `--cache-ram 1024`. Frente a layer q8: TG código 83,7→**119,8** (+43%), narrativa 60,7→**79,7** (+31%), decode tras 26K 46,8→**66,0** (+41%), PP a 26K 858→**1.070** (+25%). BCB8 directo 1/8 (mismo ítem), Computer Use 48/48, seguridad 29/29, coding 3/3, visión 3/3. Charla: TTFT +36 ms, respuesta total −14%. | **SUPERIOR en TG/PP con dos GPU**; **PARIDAD** de calidad. PP de prompts cortos sin caché −13%. En esta PC el techo estable es 131K por el commit de Windows sin pagefile. LC-H1 pendiente: best=false. |
| sys-bench-qwen38-27b-q6kxl-layer-mtp3-32k | UD-Q6_K_XL, layer, KV q8, 32K, sin visión: TG 65,1/45,3; BCB8 directo 1/8 (mismo ítem) en 55 s. Con tensor o con visión a 65K no entra por commit. | **INFERIOR** en velocidad, **sin mejora de calidad medida**; manualOnly/historial. |

Detalle en [`reddit-dual-3090-tensor-split-audit-20260927.md`](reddit-dual-3090-tensor-split-audit-20260927.md).

## Agention AP Q3_K_XL — estado del candidato · 2026-09-26

| Perfil | Evidencia | Clasificación / decisión |
|---|---|---|
| sys-bench-qwen38-agention-ap-q3kxl-32k | PPL menor que UD-Q3_K_XL y ByteShape IQ4_XS en mixedweb-v1 y Wiki del proyecto; 3/3 fixture visual; Computer Use 48/48 y coding smoke 3/3, en paridad con ByteShape. Speed de AP/UD prácticamente empatada. | **SUPERIOR en PPL local**; **PARIDAD** en los smokes; sin promoción a BEST hasta HE20/BCB LC-H1. |

La PPL no reproduce el KLD de la ficha, y las cifras de SOL no son una A/B con
el mismo backend. AP es inferior en decode bruto a Qwen3.5-9B (37,16 vs 101,36
tok/s), con una diferencia grande de tamaño. No hay mejora demostrada para
Ingi-Charla/audio. Ver [informe local](qwen38-agention-ap-local-benchmark-20260926.md).

## 2026-09-26 — NInfer Huihui Qwen3.8 · RTX 3090

| Perfil | Evidencia local | Clasificación |
|---|---|---|
| `sys-bench-ninfer3090-huihui-groupwise-mtp3-32k` | Tras un OOM inicial con GPU en uso, pesos 16,67 GiB y KV 32K sí cargaron libres; falló warm-up en `gqa_attention_prefill.cu:64` con `cudaErrorInvalidValue`. Se repitió con el launcher C1 a 64K y prefill 1024. | **INFERIOR en compatibilidad operativa SM86** frente al perfil NInfer Qwen3.8 histórico que sí atiende requests; sin score de calidad/velocidad. |
| `sys-bench-ninfer3090-huihui-groupwise-mtp3-vision-32k` | Pesos/proyector de visión 16,95 GiB y KV cargaron, pero falló el mismo kernel en warm-up; no se envió imagen. | **No usable en el runtime probado; Computer Use no evaluado.** |
| `sys-bench-ninfer3090-huihui-groupwise-nospec-32k` | El control sin MTP cargó pesos/KV y falló con el mismo kernel inválido. | **INFERIOR en compatibilidad operativa también sin MTP**; no es un fallo causado sólo por MTP. |

El OOM inicial coincidió con otro proceso local en GPU 1; no lo cuento como evidencia de calidad. Sin contención, el launcher C1 y visión fallaron en el mismo kernel de warm-up. Las cifras 175 tok/s/262K publicadas son de RTX 5090 y no se trasladan a SM86.

A pedido del usuario, el 2026-09-26 se eliminó el archivo de pesos de 18.210.531.328 bytes y se retiraron las tres entradas Huihui del catálogo. Se conserva la evidencia histórica y el ZIP del runtime; el modelo ya no está disponible desde Lanzar.

No hay score de calidad/velocidad, y Computer Use e Ingi Charla no se evaluaron. No cambian SOL, el harness ni los defaults. Ver [auditoría Huihui/NInfer](ninfer-huihui-qwen38-3090-audit-20260926.md) y [artifact de los intentos](../artifacts/ninfer-huihui-qwen38-3090-20260926.json).

## 2026-09-26 — Mica v0.1 4B, juez de opciones para benchmark

| Perfil de evaluación | Alcance | Evidencia | Clasificación |
|---|---|---|---|
| `decision-mica-v0.1-4b-q5-systemone` | Mica Q5_K_M, TypeSafe `/v1/systemone`; selección entre opciones textuales | Réplica CUDA local: fácil 223 líneas, base 25; 797/797 decisiones coinciden con el upstream. Greedy: 285 líneas en ambos scaffolds. | **SUPERIOR** a Laya/Kev en el Tetris publicado; **INFERIOR** al baseline greedy local y más lento que Laya. Benchmark-only; sin promoción productiva. |
| `decision-qwen3.5-4b-q4-systemone-control` | Control propuesto con el mismo protocolo de decisión | No ejecutado; no hay comparación local apareada. | Pendiente; no inferir calidad. |

El artefacto público de 231 casos se validó estructuralmente (231/231 filas válidas, 192 correctas) y la batería local completa confirmó el resultado Tetris publicado; eso no mide coding ni otros dominios. Mica requiere su endpoint TypeSafe, no es un perfil `llama-server` seleccionable. No se cambia el harness de coding, Ingi-Charla, Computer Use ni los defaults hasta tener una integración advisory y un A/B apareado. Ver [auditoría Mica](mica-decision-profile-audit-20260926.md) y [evidencia JSON](../artifacts/mica-decision-profile-20260926.json).

## 2026-09-28 — Flash-Next W4A16-FP8PLE vs SOL, medido (con cuarentena de VRAM)

Misma PC, mismo día y mismo harness de la app (`build_astra`, `agent-maximo`,
1800 s). La cuarentena `fbscan` y el reintento `rmtrace` 64K estuvieron activos
en las dos corridas. Flash-Next corrió con hot cache por placa, ASUS=76 y
PNY=84: hot84 en las dos da OOM en la ASUS, porque además maneja el escritorio.

| Prueba | Flash-Next | SOL | Veredicto |
|---|---:|---:|---|
| LC-H1 HE0 | 1/1 · 21 s | 1/1 · 13 s | Paridad |
| LC-H1 HE20 | 20/20 · 552 s | 20/20 · 234 s | Paridad; Flash-Next 2,4× más lento |
| LC-H1 BCB8 | 8/8 (3/8 al 1.er intento) · 1.328 s | 8/8 (4/8) · 865 s | Paridad |
| ADV v1 (graders corregidos) | 10/10 · 2.434 s | 10/10 · 842 s | Paridad |
| TG código / narrativa | 66,3 / 44,7 | **104,9 / 66,7** | **Inferior** |
| PP / TG a 26K | 1.633 / 49,8 | **1.977 / 63,0** | Inferior |
| PP / TG a 64K | **1.989 / 67,6** | 1.816 / 62,5 | Superior leve |
| PP / TG a 131K | **1.984 / 64,1** | 1.363 / 56,0 | **Superior** (+46 % PP) |
| PP / TG a 257K | **2.159 / 52,4** | 910 / 49,7 | **Superior** (2,4× PP; 164 s menos hasta el primer token) |
| Needle 26K–257K | 5/5 | 5/5 | Paridad |
| Computer Use / seguridad | 46/48 · 27/29 | **48/48 · 29/29** | **Inferior** |
| Visión con tool (hot80, ASUS=72/PNY=80) | 3/3 | 3/3 | Paridad |
| Charla, TTFT mediano | 3.048 ms | **619 ms** | **Inferior** |

**Clasificación:** Flash-Next es **SUPERIOR sólo en prefill de contexto
largo** (≥128K). Es **INFERIOR** en decode corto, Charla, Computer Use
(seguridad) y tiempo de agente, y queda en **paridad de calidad** (LC-H1 y
ADV). SOL sigue como default. ADV se re-puntuó el 2026-09-28 con los graders corregidos: el 7/10 original de los dos salía de 3 graders que contradecían su consigna. La config exacta del post (hot88 en las dos
placas) no entra en esta PC: hot84 ya da OOM en la ASUS. Velocidades medidas
con `fnbench.py` por streaming; requiere 64 GiB de swap y usa ~108 GiB de RAM.

## 2026-09-27 — Flash-Next W4A16-FP8PLE: no evaluable (VRAM defectuosa en GPU0)

> **Superado el 2026-09-28:** con la cuarentena de VRAM se pudo medir (sección de arriba).

| Perfil | Resultado local | Clasificación |
|---|---|---|
| `sys-bench-qwen38-flashnext-albucino-fast256k` | No carga: `tiered packed-byte mismatch` en la GPU ASUS (`01:00.0`) | **No evaluable en esta PC** |
| `sys-bench-qwen38-flashnext-albucino-reddit-hot88-220k` | Ídem (config exacta del post) | **No evaluable en esta PC** |
| `sys-bench-qwen38-flashnext-albucino-vision-hot80-256k` | Ídem | **No evaluable en esta PC** |
| SOL (línea de base del mismo día, harness `build_astra`, `agent-maximo`) | HE0 1/1 · HE20 20/20 · BCB8 8/8 (4/8 al primer intento, 2 reparaciones) · ADV 10/10 (7/10 con los graders rotos) | **Sin cambios: default** |

Esta vez sí había 123 GiB de RAM, con los pesos descargados y verificados por
SHA y el runtime v0.3.0 del mantenedor. La carga falló en 7 intentos, siempre
en la placa física ASUS, también con las GPUs invertidas. Se descartaron la
config (hot80/84/88), el filesystem (NTFS y ext4), el swap (28 y 64 GiB) y la
presión de RAM. Un test de VRAM hecho dentro de la GPU encontró 1.636 palabras
con los bits 25/27/29/31 clavados en 1 en la ASUS y 0 en la PNY. **No es
superior ni inferior**: el modelo no pudo correr. Hay que reevaluarlo después
de reparar la placa. Ver [informe de la falla de VRAM](gpu0-asus-3090-vram-fault-20260927.md).

## 2026-09-26 — Candidato externo Qwen3.8-Flash-Next W4A16-FP8PLE

| Perfil | Contexto / runtime | Resultado | Clasificación |
|---|---|---|---|
| `sys-bench-qwen38-flashnext-albucino-fast256k` | 256k · vLLM fast · hot84 · MTP3 · 2× RTX 3090 + 128 GiB RAM | Reporte externo: hasta 2.654 PP / 103,1 TG a 260k; no medido localmente | **Superior sólo en throughput publicado; calidad agente pendiente** |
| `sys-bench-qwen38-flashnext-albucino-reddit-hot88-220k` | 220k · hot88 · réplica del post | No medido localmente; hot88 tiene menos margen de VRAM durante prefill | **Experimental; posible OOM** |
| `sys-bench-qwen38-flashnext-albucino-vision-hot80-256k` | 256k · visión · hot80 · MTP3 · una imagen por request | Smoke sintético público; fast-256k y Computer Use LlamaCode no revalidados | **Experimental; visión no promovida** |

La máquina observada para esta auditoría tiene 61,7 GiB de RAM y no puede
ejecutar la receta de 128 GiB. El modelo no está descargado; no se interrumpió
el servidor activo de otra aplicación. Los tres perfiles quedan manuales y
fuera de selección/benchmark automático. No reemplazan SOL, que mantiene
BCB8 8/8, tool-use estable y visión 4/4. Ver [auditoría y límites](qwen38-flash-next-albucino-w4a16-audit-20260926.md).

## MiMo-V2.6-Distill-Qwen-9B — descartado tras A/B local 2026-09-23

El candidato temporal se comparó contra Qwen3.5-9B con el mismo runtime y
configuración. MiMo alcanzó 102,9 tok/s frente a 99,8 tok/s de Qwen base, pero
obtuvo 16/20 en HumanEval frente a 19/20. La ventaja de velocidad no compensa
la pérdida de calidad ni supera al perfil Qwen con MTP. El detalle reproducible
está en [`mimo-v2.6-distill-qwen9b-audit-20260923.md`](mimo-v2.6-distill-qwen9b-audit-20260923.md).

Los pesos y el `mmproj` temporales fueron eliminados después de la prueba; no
se agrega ningún perfil MiMo al inventario operativo.

## Tabla productiva comparativa — corte 2026-09-18

Esta es la tabla operativa de los perfiles más útiles para las dos RTX 3090.
Las velocidades son mediciones locales, pero no todas provienen de la misma
huella de contexto, backend o harness. Por eso se conservan por separado los
BCB agentivos, los BCB directos y los smokes de velocidad/visión: no se debe
convertir un resultado pendiente en cero ni comparar un BCB directo como si
fuera LC-H1.

| Perfil | Configuración / peso | PP/TG texto | PP/TG contexto largo | PP/TG visión | HE0 / HE20 | BCB8 | Tool-use | Contexto | Estado productivo |
|---|---|---:|---:|---:|---|---|---|---:|---|
| **SOL** | Qwen3.8-27B AutoRound INT4 · MTP4 · TP2/P2P · KV FP8 · ~19 GB | 74 narr. / **102 código** | 262K validado | 4/4 validada en vLLM/AutoRound | — | **8/8 agentivo** | **Estable** | **262K** | Default principal |
| **GALACTA** | DeepSeek V4 Flash IQ3_S · KV Q4 · ~116 GB | **9,65 BCB** | — | No aplica | 1/1 / 20/20 histórico | **8/8** | No aplica | 131K | Máxima calidad; muy lento |
| **OCCAMY** | Occamy-1.0 35B-A3B Q4_K_M · KV Q8 · TP2 layer · sin MTP · 21,17 GB + mmproj 0,90 GB | **233,09 PP / 164,07 TG @8K** | **131,90 PP / 162,96 TG @262K** | **175,65 PP / 162,68 TG @32K** | Pendiente / pendiente | **1/8 directo; LC-H1 pendiente** | **Válido** (`add`) | **262K estable**; visión probada a 32K | Experimental multimodal de alto throughput |
| **QWEN38-SHAPELEARN** | Qwen3.8-27B ShapeLearn IQ4_XS completo · KV Q8 · MTP3 · TP2 layer · ~13,08 GB | **156,8 PP / 25,85 TG** sin MTP; **180,7 PP / 53,64 TG** con MTP3 @8K | **118,4 PP / 41,77 TG** sin MTP; **108,0 PP / 66,24 TG** con MTP3 @262K | **163,5 PP / 55,92 TG @32K** · aceptación 80% | **1/8 directo; LC-H1 pendiente** | — | Visión correcta; MTP3 funcional | **262K estable** | Experimental de contexto/fidelidad |
| **QWEN35-A3B** | AutoRound INT4 · TP2/P2P · KV FP8 · ~21,5 GB | 123,98 BCB / 134,4 directo | 262K validado | **4/4** hasta 262K | 1/1 / 20/20 histórico; 9/20 actual | **4/8 histórico; 1/8 directo** | Funcional | 262K | Multimodal y concurrencia |
| **CyberTiel** | 35B-A3B Q4 · MTP3 · KV Q8 · ~23,7 GB | **154,3 TG / 155,9 visión** | 184K probado / 262K carga | **155,9 TG** | 1/1 / no concluyente | **1/8 directo** | Funcional en smoke | 262K carga | Experimental; calidad pendiente |
| **QWEN38-Q8** | Qwen3.8-27B UD-Q8_K_XL · MTP2 · KV Q8 · ~31,5 GB | 41,3 @8K | **22,1 @262K** | No validada con MTP2/KV Q8 | Smoke OK / pendiente LC-H1 | **8/8 directo** | Agente pendiente | **262K** | Fidelidad/contexto; experimental |
| **TERRA** | ThinkingCap Qwen3.6-27B Q4 · MTP4 · KV Q8 | **56,84 BCB** | 64K | Smoke visual 2/2 | 1/1 / 20/20 | **6/8 histórico** | Funcional | 64K | Razonamiento y visión |
| **METEOR** | BigBang Q4_K_M · MTP5 · KV Q8 | **207 texto / 195,3 visión** | 64K | **1/1 smoke** sin MTP | 1/1 / no concluyente | **3/8 histórico; 2/8 directo** | Funcional en smoke | 64K | Throughput/lotes; calidad parcial |
| **Qwen3.5-9B** | Q4_K_M · MTP3 · KV Q8 · ~5,7 GB | **166,1 TG / 144,2 visión** | — | Funcional | 1/1 / 19/20 | **1/8 directo** | Auxiliar | 8K probado | Auxiliar multimodal |
| **Qwen3.5-4B** | Q4_K_M · MTP3 · KV Q8 · ~2,8 GB | **200,0 TG / 206,6 visión** | — | Funcional | 1/1 / 20/20; reparación no convergente | **1/8 directo** | Auxiliar | 8K probado | Auxiliar equilibrado |
| **Qwen3.5-2B** | Q4_K_M · MTP3 · KV Q8 · ~1,3 GB | **318,9 TG / 344,8 visión** | — | Funcional | 0/1 / no ejecutado | **0/8 directo** | No confiable como agente | 8K probado | Auxiliar rápido |

### Lectura comparativa de Occamy

## Auditoría de perfiles potencialmente superseded — 2026-09-19

Se aplicó un criterio Pareto conservador: un perfil sólo se considera
`superseded` si otro lo domina simultáneamente en calidad/estabilidad,
velocidad útil, contexto/visión y función práctica. Una ventaja de tamaño,
concurrencia, DFlash2 o throughput bruto mantiene al perfil como no dominado,
aunque no sea recomendable como default.

| Perfil en duda | Evidencia comparada | Veredicto |
|---|---|---|
| **QWEN35-A3B** | Occamy es más rápido (162–164 frente a 134,4 TG) y tiene BCB directo 3/8 frente a 1/8 actual de QWEN35-A3B. QWEN35-A3B conserva visión 4/4 hasta 262K, concurrencia vLLM y un histórico 4/8 no equivalente. | **No superseded**: Occamy domina el throughput simple, pero no la combinación de visión/concurrencia ni existe una comparación BCB LC-H1 idéntica. |
| **QWEN38-SHAPELEARN** | Supera ampliamente a QWEN38-Q8 en velocidad a 262K (66,24 frente a 22,1 TG), pesa ~13 GB y mantiene visión+MTP3. No tiene BCB8 LC-H1 cerrado. | **No superseded**: es el perfil de contexto largo/fidelidad; no compite con METEOR por throughput corto ni con SOL por calidad agentiva. |
| **METEOR** | Es el más rápido en throughput bruto (207/195,3 TG), pero sólo ofrece 64K y BCB 2/8 directo, 3/8 histórico. | **No superseded**: conserva un nicho claro de lotes/throughput. |
| **Qwen3.6-35B-A3B GGUF MTP** | AutoRound/QWEN35-A3B tiene mejor evidencia agentiva y visión estable. El GGUF legacy conserva 207,8 TG con MTP, pero MTP+visión no es estable. | **Parcialmente superseded para producción**, no globalmente: conservar sólo si se necesita su throughput MTP de texto. |
| **GSQ-RCO + DFlash2 Q2** | ShapeLearn pesa sólo ~1 GB más, ofrece 262K frente a 81,9K configurados, 66,24 TG a 262K frente a 25 TG a 8K y visión+MTP3. GSQ sólo tiene HE0 1/1; HE20 se canceló y BCB no se inició. | **Superseded para uso general**; conservar únicamente como laboratorio DFlash2. |
| **Qwen3.5-9B** | Qwen3.5-4B es más rápido y pequeño, pero 9B conserva mayor capacidad en 5,9 GB y tiene HE20 19/20. Occamy ofrece más calidad/contexto, pero no reemplaza su rol liviano. | **No superseded globalmente**; parcialmente desplazado si sólo se busca velocidad auxiliar. |
| **Qwen3.5-4B** | Es más lento que 2B, pero tiene mayor capacidad y HE20 20/20 frente a 0/1 de 2B. Occamy es mucho más capaz, pero 10× más pesado y no es sustituto auxiliar. | **No superseded**. |
| **Qwen3.5-2B** | Es el más rápido y pequeño (318,9/344,8 TG; ~1,3 GB), aunque BCB 0/8 y HE0 0/1. Ningún modelo actual ofrece ese coste/latencia. | **No superseded**; sólo no recomendable como agente principal. |

### Resultado operativo

Entre los perfiles que todavía tienen pesos locales, el único que queda
realmente superseded para uso general es **GSQ-RCO + DFlash2 Q2**. El GGUF
legacy de Qwen3.6 está superseded sólo para producción multimodal, pero no por
throughput de texto. Los demás son perfiles no dominados con trade-offs reales.

Los perfiles ya retirados previamente —CyberTiel, Agnes, ASTRA IQ1_S, ASTRA
IQ4_XS y Flash-Next EXL3— no se volvieron a ejecutar porque sus pesos están en
la papelera; sus resultados históricos ya justificaban el retiro.

Occamy es, con las mediciones locales disponibles, el modelo multimodal de
35B-A3B con mayor decode sostenido entre los candidatos experimentales: supera
los 134,4 TG directos de QWEN35-A3B y los 154,3/155,9 TG de CyberTiel en sus
recetas publicadas. Queda por debajo del throughput bruto de METEOR (207 TG),
pero conserva 262K estable, visión funcional y tool-use válido sin MTP.

La ventaja de velocidad no equivale todavía a una ventaja de calidad: Occamy
no tiene BCB8 LC-H1, HE20 ni una campaña agentiva comparable. SOL sigue siendo
el default porque combina **BCB 8/8**, tool-use estable y contexto validado.
Occamy queda como opción experimental para visión, concurrencia futura y
throughput multimodal.

Detalle reproducible: [`occamy-1.0-audit-20260918.md`](occamy-1.0-audit-20260918.md).

### Lectura comparativa de ShapeLearn

ShapeLearn completo es claramente más rápido que QWEN38-Q8 en las mediciones
locales comparables: llega a **66,24 TG a 262K con MTP3**, frente a **22,1 TG
a 262K** de QWEN38-Q8. Además, conserva vocabulario completo —a diferencia de
ASTRA ASCII/P1M— y la combinación visión+MTP3 funcionó a 32K con 80% de
aceptación. No tiene todavía BCB8 LC-H1, así que no se presenta como superior a
SOL en calidad ni en tool-use agentivo.

Detalle reproducible: [`qwen38-byteshape-shapelearn-audit-20260918.md`](qwen38-byteshape-shapelearn-audit-20260918.md).

## Matriz de candidatos presentes en Disco C/D antes de limpieza — 2026-09-18

Esta matriz se agrega antes de retirar artefactos grandes. Incluye variantes
experimentales y perfiles que no deben confundirse con la tabla productiva:
las cifras de velocidad son smokes locales y sólo los resultados marcados como
BCB8 LC-H1 son comparables como calidad agentiva. Los candidatos con estado
“retirar/mover” no se ofrecen como defaults.

| Perfil / artefacto | Velocidad local | Calidad / estabilidad | Contexto | Visión | Evaluación para almacenamiento |
|---|---:|---|---:|---|---|
| **ASTRA IQ1_S** | 58,2 PP / 25,4 TG @8K; 58,0 PP / 25,6 TG @262K; MTP compartido 41,6–58,5 TG warm | Micro-suite 4/6; BCB8 LC-H1 pendiente; tool-call válido con MTP | **262K probado** | No hay `mmproj` compatible validado | Experimental de contexto largo; conservar sólo si se seguirá investigando |
| **ASTRA Flash-Next IQ4_XS** | 16,5 TG control; 36,0 con caché 188; ~45,5 con caché 150 | Salida corrupta o repetitiva en las recetas rápidas; no BCB válido | 196K/262K configurado, no fiable como agente | No funcional de forma utilizable | **Mover o archivar; no justifica conservarlo en C** |
| **Flash-Next EXL3 4.05bpw** | 35,4 TG texto; 34,7 TG visión; 63,5 TG a 103K con otra variante EXL3 | **BCB 1/8**; tool-call válido; MTP no disponible en este artefacto | **262K funcional**; 103K llenado; 512K sólo reservado | Funcional con `mmproj` | Experimental de laboratorio; mover a D, no necesario en C |
| **Opti-27B** | 232,6 PP / 39,1 TG @16K; 215,2 / 39,1 @262K; ~86,4 TG agregado en 4 slots | BCB/HE pendientes; tool-call válido con reasoning off; reasoning on degenera | 262K carga; 123,9K de prefill probado | Funcional con reasoning off | Mover a D o archivar; no reemplaza SOL |
| **Agnes-3.0-Flash** | 139,2 PP / 33,3 TG texto; 506,5 PP / 33,1 TG visión | **1/8 directo**; BCB8 LC-H1/HE20 pendientes; tool-call smoke válido | 262K carga; escalera completa pendiente | Funcional con `mmproj` | Mover a D; candidato multimodal, pero no productivo |
| **NInfer Qwen3.6-35B-A3B** | MTP3: **190,1 TG** sostenidos; C2 concurrente validado | BCB LC-H1 pendiente; runtime experimental | 262K texto; visión falla al reservar 262K | 131K funcional; 262K no | Conservar mientras siga activo el perfil NInfer |
| **QWEN35-A3B GGUF MTP** | 140,2 TG base; **207,8 TG con MTP** | BCB comparable pendiente; estabilidad de MTP+visión no demostrada | Menor que la ruta AutoRound validada | Visión sin MTP funcional; MTP+`mmproj` incompatible | Variante vieja; mover a D o retirar al usar sólo AutoRound |
| **Ling 3.0 Tiny / LUNA** | ~1.260 PP / **204 TG** histórico | HE0 0/1; sin BCB agentivo vigente | 131K declarado | No | **Supersedido por Qwen3.5-2B/4B/9B; retirar** |
| **ByteShape ASCII/P1M IQ4_XS** | 79–88 TG corto; ~45 TG @262K | BCB directo 1/8; limita idiomas no ASCII | 262K estable | Funcional con MTP2 | Supersedido por ShapeLearn completo; retirar si no se necesita inglés/código ASCII |
| **GSQ-RCO + DFlash2 Q2** | 67,7 TG corto; 25,0 TG @8K; visión 52,1 TG; HE0 29,09 TG | HE0 LC-H1 1/1; HE20 cancelado en prompt 5/20 por latencia operativa; BCB bloqueado por compuerta | 81,9K configurado; 9,6K probado | Funcional | Experimental; conservar sólo como referencia DFlash2, no productivo |

### Componentes sin benchmark propio

`Qwen3.8-27B-DFlash2-W4A16` (1,28 GB) es un drafter, no un perfil
independiente; se conserva hasta cerrar la comparación SOL+DFlash2. La copia de
SOL que existe en C y D tiene los mismos ocho archivos de pesos
`.safetensors` byte a byte; la copia de D sólo agrega metadatos y archivos de
descarga, por lo que es redundante.

## PCIe/bifurcación de las 2× RTX 3090 — 2026-09-18

Se auditó la sugerencia de PCIe x8/x8. Ambas placas ya cuelgan de root ports de
CPU, con `PHB` entre GPUs, y P2P lectura/escritura funciona. La campaña previa
midió sólo ~0,2% de diferencia con P2P usando reparto por capas; no se cambia
la placa madre ni los perfiles. Detalle:
[`dual-3090-pcie-bifurcation-audit-20260918.md`](dual-3090-pcie-bifurcation-audit-20260918.md).

## Laya / Jev — componente auxiliar de routing 2026-09-18

Laya es un motor de decisión no autoregresivo, no un perfil generativo. La
auditoría local está en [`laya-jev-audit-20260918.md`](laya-jev-audit-20260918.md).

| Componente | Resultado local | Uso recomendado | Estado |
|---|---:|---|---|
| Laya 421M | **13–15 ms warm en RTX 3090**; 248–564 ms en CPU | Routing, guardrails y triage delante de SOL | Experimental; no aparece como modelo |

Detectó correctamente coding, prompt injection, intención técnica y clases de
operación de PC. Su señal genérica de “requiere confirmación” fue inconsistente,
por lo que las reglas deterministas de seguridad de LlamaCode siguen siendo la
autoridad.

## Opti-27B — auditoría aislada 2026-09-18

Se compiló el runtime parcheado requerido por Opti para SM86 y se probó el
modelo localmente sin cambiar el backend estable de LlamaCode. El detalle,
hashes y límites están en [`opti-27b-audit-20260918.md`](opti-27b-audit-20260918.md).

| Perfil | Configuración | Velocidad local | Calidad / tool-use | Contexto | Visión | Estado |
|---|---|---:|---|---:|---|---|
| Opti-27B | 3,47 bpw · runtime parcheado · TP2 layer · KV q8 | **39,1 TG dual**; ~86,4 TG agregado en 4 slots | BCB LC-H1 pendiente; tool-call válido con reasoning off | **262K carga**; 123,9K prefill probado | **Funcional con reasoning off** | Experimental aislado; no supera SOL y no entra al dropdown |

Opti reduce presión de VRAM y permite explorar concurrencia, pero queda por
debajo de SOL en decode, no tiene validación agentiva y su reasoning activado
produjo salida degenerada en esta build. No se asigna BCB/HE0/HE20 ni se
promueve hasta integrar el runtime de forma reproducible.

## Occamy-1.0 Q4_K_M — 2026-09-18

La auditoría local está en [`occamy-1.0-audit-20260918.md`](occamy-1.0-audit-20260918.md).
Occamy es el primer candidato de 35B-A3B que combina en nuestra máquina un
decode de ~163 TG sin MTP, 262K estable, visión correcta y tool-use válido.
La escalera LC-H1 ya cerró: HE0 1/1, HE20 20/20 y BCB8 3/8. Queda por debajo
de SOL como decisión de calidad aunque sea más rápido que QWEN35-A3B y
CyberTiel en esta receta.

| Perfil | Configuración | Velocidad local | Calidad | Contexto | Visión | Estado |
|---|---|---:|---:|---:|---|---|
| `sys-occamy-35b-q4km-262k` | Occamy-1.0 35B-A3B Q4_K_M · KV Q8 · TP2 layer · sin MTP | **164,07 TG a 8K; 162,96 TG a 262K**; 162,68 TG visión; **143,59 TG BCB** | **HE0 1/1 · HE20 20/20 · BCB8 3/8**; tool-call válido | **262K estable** | **Funcional a 32K** | Experimental multimodal; no reemplaza SOL |

## Qwen3.8 ByteShape ShapeLearn IQ4_XS — 2026-09-18

La variante completa de vocabulario se descargó y probó después del quant
ASCII/P1M. El detalle está en
[`qwen38-byteshape-shapelearn-audit-20260918.md`](qwen38-byteshape-shapelearn-audit-20260918.md).
MTP3 integrado funciona y permite 66,2 TG a 262K en 2× RTX 3090; visión+MTP3
también es funcional. HE0 1/1 y HE20 20/20 quedaron validados con el perfil
de agente compacto `Con fases`; el BCB sigue bloqueado por salida previa a
tools, no por carga ni CUDA. No se promueve ni se compara como reemplazo de
SOL.

| Perfil | Configuración | Velocidad local | Calidad | Contexto | Visión | Estado |
|---|---|---:|---:|---:|---|---|
| `sys-qwen38-27b-byteshape-shapelearn-262k` | ByteShape ShapeLearn IQ4_XS · KV Q8 · MTP3 · TP2 layer | 53,6 TG a 8K; **66,2 TG a 262K**; 55,9 TG visión; **77,91 TG HE20** | **HE0 1/1 · HE20 20/20**; BCB8 bloqueado por protocolo de agente | **262K estable** | **Funcional con MTP3** | Experimental; no reemplaza SOL |

## Qwen3.8 ByteShape ASCII/P1M — 2026-09-18

La auditoría completa está en
[`qwen38-byteshape-ascii-audit-20260918.md`](qwen38-byteshape-ascii-audit-20260918.md).
El candidato reduce el peso a 12,25 GB, carga 262K con KV Q8 en las dos RTX
3090 y permite visión+MTP2, pero restringe la entrada práctica a inglés/código
ASCII y obtuvo sólo **1/8** en el BCB8 directo. Se conserva como candidato
especializado, no como reemplazo de SOL.

| Perfil | Configuración | Velocidad local | Calidad | Contexto | Visión | Estado |
|---|---|---:|---:|---:|---|---|
| `sys-qwen38-27b-byteshape-ascii-262k` | ByteShape IQ4_XS ASCII/P1M · KV Q8 · MTP2 · TP2 layer | 79–88 TG corto; 45 TG a 262K; 67,6 visión+MTP2 | BCB8 directo **1/8** | **262K estable** | **Funcional con MTP2** | Experimental; inglés/código ASCII |

## Campaña Harness de calidad — 2026-09-15

La comparación agentiva solicitada para QWEN35-A3B, CyberTiel, METEOR y los
auxiliares Qwen3.5 está documentada en
[`harness-quality-campaign-20260915.md`](harness-quality-campaign-20260915.md).
La tabla separa HE0/HE20/BCB actuales de controles directos e históricos; no
se asignan scores BCB cuando la compuerta HE20 no se completó.

## Reejecución BCB8 directa — 2026-09-15

Se completó una corrida directa de 8 tareas para los perfiles pequeños y
experimentales solicitados. El detalle reproducible está en
[`bcb8-rerun-direct-20260915.md`](bcb8-rerun-direct-20260915.md). Estos scores
no reemplazan los BCB LC-H1 porque no incluyen herramientas, reparación ni
reintentos de agente.

| Perfil | BCB8 directo | Tiempo generación / 8 casos | Estado |
|---|---:|---:|---|
| QWEN35-A3B vLLM · TP2/P2P · KV FP8 | **1/8** | 156,849 s | Control vLLM 0.27.1, 32K |
| METEOR / BigBang · MTP5 · KV Q8 | **2/8** | 13,187 s | Control GGUF funcional |
| QWEN35-A3B GGUF · MTP3 · KV Q8 | **1/8** | 17,583 s | Experimental |
| CyberTiel · MTP3 · KV Q8 | **1/8** | 15,288 s | Experimental |
| Qwen3.5-9B · MTP3 · KV Q8 | **1/8** | 20,882 s | Auxiliar |
| Qwen3.5-4B · MTP3 · KV Q8 | **1/8** | 12,445 s | Auxiliar |
| Qwen3.5-2B · MTP3 · KV Q8 | **0/8** | 9,865 s | Sólo tareas rápidas |
| Qwen3.5-4B CPU · sin MTP | **2/8** | 418,982 s | Control CPU; MTP no compatible en el runtime disponible |

La evidencia oficial anterior se conserva: QWEN35-A3B vLLM permanece en 4/8
agentivo y BigBang en 3/8 histórico. No se modificó el default SOL.

## Cierre de validaciones Ubuntu — 2026-09-14

La auditoría de perfiles está en
[`profile-validation-audit-20260914.md`](profile-validation-audit-20260914.md).
QWEN38-Q8 ya tiene un BCB directo reproducible de **8/8** a 262K con MTP2 y
KV Q8, a 51,74 tok/s de media. Ese resultado no se mezcla con el BCB LC-H1:
la ruta de agente completa sigue pendiente. La visión del mismo perfil sólo
pasó en un control sin MTP con KV Q4; MTP2+KV Q8+visión falló con acceso ilegal
CUDA. TERRA tiene además un smoke visual 1/1 a 64K sin MTP. Los perfiles
texto-only se marcan como “No aplica” en visión, no como validación pendiente.

## 2026-09-26 — LFM2.5-VL-3B F16 + Liquid DSpark local

| Perfil | Configuración | Evidencia local | Clasificación |
|---|---|---|---|
| `sys-bench-lfm25-vl3b-f16-control-20260926` | F16 + mmproj F16 · 8k · b10964 · temp 0 | Lectura de estado correcta. `desktop_click` válido, pero apuntó al centro (0,5; 0,5) y no al interruptor. | Control; no promover como agente visual |
| `sys-bench-lfm25-vl3b-dspark8-20260926` | Igual + DSpark n=8 F16 | Decode 2,30× en descripción y 2,35× en lectura de estado. Tool-call válida pero mismo click erróneo; mediana Computer Use 987 ms vs 895 ms control. | **Superior sólo en decode; inferior/no promover para Computer Use** |
| `sys-bench-lfm25-vl3b-dspark9-20260926` | Igual + DSpark n=9 F16 | Decode 3,33× en descripción y 2,26× en lectura de estado. Tool-call válida pero mismo click erróneo; mediana Computer Use 890 ms vs 895 ms control. | **Superior sólo en decode; inferior/no promover para Computer Use** |

Las velocidades de visión son del primer request de cada prompt y el end-to-end depende del prefill de imagen; el test real del schema de acción repitió tres veces sin reutilizar KV de prompt. Los perfiles quedan `manualOnly`, `best=false` y `favorite=false`. No se cambió el harness: el parser acepta el tool-call, el error observado está en las coordenadas que el modelo eligió. No hay evidencia sobre calidad de ingeniería de software ni mejora de Ingi-Charla/STT/TTS. Pesos instalados localmente en `D:\Models\llamacpp\LFM2.5-VL-3B-DSpark-bench`; detalle, protocolo, limitaciones y fuentes en [auditoría DSpark](lfm25-vl-dspark-audit-20260926.md).

## Variantes ngram para comparar

Se agregaron copias declarativas para medir `ngram-mod` sin modificar los
perfiles base. En los perfiles con MTP se usa deliberadamente
`--spec-type draft-mtp,ngram-mod` para probar ambos mecanismos juntos, con
`--spec-ngram-mod-n-match 24`, `--spec-ngram-mod-n-min 16` y
`--spec-ngram-mod-n-max 64`. KAT y Laguna no tienen un drafter MTP en su perfil
base, por lo que sus copias prueban `ngram-mod` solo.

| Variante | Base | Modo |
|---|---|---|
| `sys-bench-qwen38-udq4-mtp3-ngram` | Qwen3.8 UD-Q4 | MTP3 + ngram |
| `sys-bench-qwen38-q4km-mtp3-ngram` | Qwen3.8 Q4_K_M | MTP3 + ngram |
| `sys-bench-qwen38-q5km-mtp3-ngram` | Qwen3.8 Q5_K_M | MTP3 + ngram |
| `sys-bench-48-kat-ngram` | KAT2-Coder | ngram |
| `sys-bench-48-bigbang-mtp-ngram` | BigBang MTP balance | MTP5 + ngram |
| `sys-bench-laguna-s-2-1-q2-48gb-ngram` | Laguna CUDA safe | ngram |
| `sys-bench-maxq-ngram` | MAX-Q ThinkingCap | MTP4 + ngram |
| `sys-bench-qwen36-cache-mtp2-ngram` | Qwen3.6 cache MTP2 | MTP2 + ngram |
| `sys-bench-qwen36-cache-mtp4-ngram` | Qwen3.6 cache MTP4 | MTP4 + ngram |
| `sys-bench-qwen36-cache-mtp6-ngram` | Qwen3.6 cache MTP6 | MTP6 + ngram |
| `sys-bench-qwen36-cache-text-mtp4-ngram` | Qwen3.6 texto-only MTP4 | MTP4 + ngram |

## Variantes inspiradas en el control público de Qwen3.8

Se agregaron variantes declarativas para comparar la familia Qwen3.8 bajo
`llama.cpp`, sin incorporar vLLM ni alterar los perfiles base. Replican sólo
los ejes que tienen equivalente local: contexto 262k con KV `q8_0`, batch 8192
y concurrencia de 2/4/6 slots. La variante de 262k usa B2048/U512 para evitar
confundir `max-num-batched-tokens` de vLLM con un flag idéntico de llama.cpp.

Cada eje existe para UD-Q4, Q4_K_M y Q5_K_M, con IDs `*-post-262k-kv8`,
`*-post-b8192`, `*-post-parallel2`, `*-post-parallel4` y
`*-post-parallel6`. Son controles de medición, no candidatos promovidos;
deben compararse con el mismo harness, prompts y huella de configuración.

## Benchmark de ciclo de artefactos

El flujo inspirado en DocStash se mide como una capacidad separada de
HumanEval/HE20/BCB: generar un artefacto autocontenido, dejar un manifiesto
privado y demostrar que preparar/stash no publica nada. La suite bundleada es
[`artifact_lifecycle_v1.json`](../assets/benchmarks/custom/artifact_lifecycle_v1.json)
y compara los perfiles `agent-artifact-local` y
`agent-artifact-publisher` sobre el mismo runtime Qwen3.8 UD-Q4.

| ID | Perfil de agente | Suite | Resultado | Estado |
|---|---|---|---|---|
| `sys-bench-qwen38-udq4-artifact-local` | `agent-artifact-local` | `artifact_lifecycle_v1` | Pendiente | Candidato; stash privado sin red |
| `sys-bench-qwen38-udq4-artifact-publisher` | `agent-artifact-publisher` | `artifact_lifecycle_v1` | Pendiente | Candidato; web/browser disponibles, publish con aprobación |

Estas filas no se mezclan con HE0/HE20/BCB. Registrar `qualityScore/qualityTotal`,
tiempo total, reparaciones, archivos producidos, manifiesto y cualquier intento
de publicación; una publicación no solicitada cuenta como fallo de seguridad.

## Alcance activo

Sólo se ejecutan nuevos benchmarks para perfiles marcados `⚡ BEST`. La
selección activa incluye **⚡ Qwen3.8 UD-Q4 visión**, el `BEST` DeepSeek
`sys-48-dsv4-nospec` y los cuatro candidatos experimentales Qwen3.6 de cache/MTP
incorporados el 2026-08-18. Los candidatos Qwen3.6
son de medición, no ganadores promovidos: sus resultados siguen
pendientes y no deben reemplazar perfiles existentes automáticamente.

## Campaña DeepSeek local — 2026-08-30

Se ejecutó una matriz manual sobre los artefactos DeepSeek disponibles en esta
PC: UD-IQ3_S en cuatro shards, la variante LID CUDA y el híbrido antirez. Se
probaron builds b10228/b10331, una y dos RTX 3090, KV `q4_0`/`q8_0`, reparto
`tensor-split 1,0`/`1,1`, tres rangos de expertos residentes y los modos de carga
`mmap`/`none`. La tabla nativa usa una petición caliente de 256 tokens con
prompt de 57 tokens; no debe leerse como decode después de llenar 128k. El
recibo completo, logs y fallos están en
[`artifacts/deepseek-campaign-20260830`](../artifacts/deepseek-campaign-20260830/README.md).

| Perfil/familia | Evidencia E2E histórica | Native smoke 2026-08-30 | Estado y decisión |
|---|---|---|---|
| `sys-48-dsv4-nospec` · UD-IQ3_S | BCB **8/8**, 9,645 tok/s, 131k | 6,171 tok/s con 12 capas expertas en CUDA1; 5,764 con 8 | **BEST dentro de DeepSeek por calidad**; no ganador universal de velocidad |
| `sys-ultraq-dsv4-0731-lid-cuda` · UD-IQ3_S | Recuperación exacta 131k y 262k con f16 KV | 4,733 / 4,877 tok/s en esos recibos | Capacidad confirmada hasta 262k; 524k/1M no verificados |
| `sys-48-antirez-dsv4-q2q4-0731` · híbrido Q2/Q4 | BCB **8/8**, 10,548 tok/s, 131k | 8,280 q4/131k; 9,066 q8/64k | Referencia DeepSeek de velocidad; BCB histórico más rápido |
| `sys-48-dsv4-iq2m` · UD-IQ2_M | Sin resultado | GGUF local ausente | No se descarga ni se inventa score; queda pendiente |

Resultado de comparación: `sys-48-dsv4-nospec` queda marcado como `BEST` en el
catálogo porque supera a DeepSeek Fusion en calidad histórica (BCB 8/8 frente a
2–4/8). No se lo marca como ganador absoluto: antirez conserva 8/8 y mayor TPS
BCB histórico, aunque con un coste total alto. La campaña nativa tampoco
reemplaza la cadena HE0 → HE20 → BCB.

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
| `c7e4b1a2-6d93-4f0e-8a75-2b1c9d6e4f80` | QWEN38-Q8 · UD-Q8_K_XL · 262K | chat | Smoke OK | No ejecutado | **8/8 directo** | — | — | — | **51,74 tok/s BCB directo** | — | — | No medido | No medido | — | Control visual OK sin MTP/KV Q4; MTP2+KV Q8+visión falla | MTP2 | UD-Q8_K_XL | 27B | 262k | medium | LC-H1 directo | Texto validado; agente LC-H1 y visión prioritaria pendientes |
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
| `sys-bench-qwen38-q4km-24gb-tg128` | Qwen3.8 Q4_K_M · control 24GB · tg128 cold | Máximo | Pendiente | Pendiente | Pendiente | — | — | — | — | — | — | No medido | No medido | — | No | — | Q4_K_M | 27B | 32k | No | llama-bench/LC-H1 | Control nuevo; validar offload completo |
| `sys-bench-qwen38-q6k-24gb-tg128` | Qwen3.8 Q6_K · control 24GB · tg128 cold | Máximo | Pendiente | Pendiente | Pendiente | — | — | — | — | — | — | No medido | No medido | — | No | — | Q6_K | 27B | 32k | No | llama-bench/LC-H1 | Control nuevo; registrar margen/OOM |
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

## Corrida auxiliar HumanEval 20 — 2026-08-27

Esta corrida usa modelo real y sirve como control de agente/sampling; no
reemplaza la cadena oficial HE0 → HE20 → BCB de la tabla operativa. Artefactos:
`%LOCALAPPDATA%\LlamaCode\LlamaCode\benchmark-runs\HumanEval_20_tems__20260827_222122`.

| Perfil | HE20 | Pasadas | Tiempo total mediano | TPS mediano | Estado |
|---|---:|---:|---:|---:|---|
| `174_KAT Q4 K_M · sampling A/B 0.30/0.90` (`51d46758-fd7c-4d3c-8018-23154a2e0062`) | 20/20 | 3/3 | 277,601 s | 84,18 | Estable |
| `FAST - KAT2-Coder-7-8-26` (`sys-48-katcoder-262k`) | 20/20 en 2/3 | 2/3 | 214,785 s | 106,30 | Una pasada 19/20 por calidad |

El `comparison.json` persistido registra 5/6 corridas aceptadas y no muestra
fallo de infraestructura. No se promueve un ganador con esta muestra auxiliar.

## Campaña oficial en curso — 2026-08-27

El runner `tools/run-benchmark-post-correction.ps1` se inició con el binario
Release en `127.0.0.1:8765`, detectó 86 perfiles listos y está ejecutando en
serie HE0 → HE20 → BCB. Al momento de esta anotación se encuentra en
`141_QUALITY - DeepSeek Fusion leloch`, BCB, prompt 1/8; por lo tanto las
columnas oficiales no se actualizan ni se considera cerrada la campaña hasta
que exista un resultado persistido o un cierre explícito del runner.

## Seguimiento de campaña reanudada — 2026-08-28

Tras verificar la PC libre, se relanzó la campaña con el Release headless y la
cobertura persistida. El runner volvió a detectar 86 perfiles, omitió los que
ya tenían HE0/HE20/BCB válidos y avanzó hasta el perfil
`141_QUALITY - DeepSeek Fusion leloch · VRAM experts 0-2`, que inició BCB con
modelo real. En el mismo control, el perfil `153_BALANCE - Laguna S 2.1 · fit
on 100k · agent-maximo` permanecía incompleto con HE0 bloqueado.

No se agregaban filas ni se cambiaban rankings en ese corte intermedio. La
campaña quedó posteriormente detenida de forma intencional en el perfil 58/86;
el detalle auditado del cierre se registra abajo.

## Auditoría del corte de campaña oficial — 2026-08-28

El log persistente
`%LOCALAPPDATA%\LlamaCode\LlamaCode\benchmark-campaign-post-correction.log`
registra una campaña de 86 perfiles iniciada a las 09:32. Hubo cierre explícito
para los perfiles 1–57: **27 `complete` y 30 `incomplete`**. El perfil 58
(`antirez · 32k · reasoning low`) inició HE20 y fue cancelado en el prompt 5/20;
por eso no tiene línea de cierre propia. En esta clasificación, `complete`
significa que no quedó una etapa pendiente o bloqueada en el runner; no implica
BCB 8/8.

Perfiles cerrados como `complete`: `1`, `3–6`, `8`, `11–12`, `14–22`,
`39–47` y `55`. Cerrados como `incomplete`: `2`, `7`, `9–10`, `13`, `23–38`,
`48–54` y `56–57`. Los artefactos del 28 de agosto agregan 42 JSON de resultado
para 30 nombres de perfil; el resto de la cobertura se reutilizó desde corridas
persistidas anteriores.

Los 17 JSON de HE0 con `0/0` y `failureStage=server-load` corresponden a
`DeepSeek V4-7-8-26` y las 16 variantes ULTRA-Q de los perfiles 13 y 23–38.
No son puntuaciones de calidad: el servidor no llegó a dejar una pasada
evaluable. El perfil 10, `VRAM balance`, dejó un intento BCB 5/8, pero su cierre
global quedó `infra-timeout` tras tres intentos; se conserva como resultado
provisional, no como promoción.

Resultados nuevos con evidencia persistida que faltaba reflejar:

| Perfil | HE0 | HE20 | BCB | Estado de lectura |
|---|---:|---:|---:|---|
| `[bench 48GB] KAT APEX-MTP + visión · MTP3 · 32k` | 1/1 · 46,149 s | 18/20 · 429,338 s | 5/8 · 463,354 s | Calidad parcial; cierre completo, sin promoción |
| `[bench 48GB] KAT APEX-MTP + visión · sin MTP · 32k` | 1/1 · 43,946 s | 19/20 · 702,375 s | 1/8 · 342,839 s | Control válido, calidad insuficiente |
| `[bench antirez stress] 64k · B4096 · U1024 · KV q8_0` | 1/1 · 156,513 s | 19/20 · 1150,040 s | 3/8 · 2049,730 s | Calidad parcial; no desplaza candidatos |

Las rutas de evidencia son, respectivamente,
`HumanEval_1_tems__20260828_123336` + `123721` +
`BigCodeBench-Hard_8_tems__20260828_124543`,
`HumanEval_1_tems__20260828_125509` + `125706` +
`BigCodeBench-Hard_8_tems__20260828_131007`, y
`HumanEval_1_tems__20260828_171744` + `172159` +
`BigCodeBench-Hard_8_tems__20260828_174241`, dentro de
`%LOCALAPPDATA%\LlamaCode\LlamaCode\benchmark-runs`.

## Retiro de perfiles antirez A/B — 2026-08-28

Se retiraron de la cola activa las variantes declarativas:

| Perfil | HE0 | HE20 | Decisión |
|---|---:|---:|---|
| `sys-48-antirez-dsv4-q2q4-32k-reasoning-off` | 1/1 en 217,863 s | timeout a 1801,3 s; 0/0 evaluable | Retirado; no escala a HE20 |
| `sys-48-antirez-dsv4-q2q4-32k-reasoning-low` | 1/1 en 270,169 s | cancelado en prompt 5/20 tras ~14 min; sin score | Retirado; demasiado lento y sin calidad HE20 demostrada |

El control DeepSeek Fusion comparable completó HE20 en 1216,85–1300,74 s
con 20/20. Los resultados y metadata de esta campaña permanecen en
`%LOCALAPPDATA%\LlamaCode\LlamaCode\benchmark-runs`; no se elimina evidencia.
La campaña oficial se canceló de manera intencional después de este gate y no
se presenta como matriz completa.

## 2026-09-18 — GSQ-RCO IQ3_S con drafter DFlash2 Q2

Se descargó `HermiHg/Qwen3.8-27B-DFlash2-Q2_K_S-MIX-GGUF` (~536 MiB) y se
probó contra el target local `ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF` con el
binario CUDA DFlash2 de Ampere, 2× RTX 3090/P2P y contexto 81.920. El control
autoregresivo obtuvo 221,77 PP / 42,48 TG; DFlash `n-max=3` obtuvo 183,61 PP /
67,02 TG, con 85/123 tokens aceptados (69,1%). `n-max=5` no fue consistente
(58,77–68,44 TG; aceptación 44,2–55,4%). Tool-use y visión funcionaron; a
9.592 tokens la receta K8/V4 midió 102,18 PP / 17,67 TG y 19/33 aceptados.

Se agrega el perfil manual experimental
`sys-bench-qwen38-gsq-rco-iq3s-dflash2-q2-81k`. No se promueve ni reemplaza
SOL: el target todavía no tiene HE20/BCB8 con el harness oficial y la ganancia
de decode cae con el contexto. Detalle reproducible:
`docs/qwen38-gsq-rco-dflash2-q2-audit-20260918.md`.

## 2026-09-18 — SOL AutoRound INT4 + DFlash2 vLLM local

Se descargó en el Disco D `syvai/Qwen3.8-27B-DFlash2-W4A16` (1,28 GB) y se
aplicó el backport DFlash2 sobre vLLM 0.27.1. Con el mismo target AutoRound de
SOL, TP2/P2P y n=7, BF16/Flash-Attention midió 109 tok/s narrativo y 144 tok/s
de código en requests cortos; FP8 E4M3/FlashInfer arrancó con 262K configurado
y midió 103–108 narrativo y 124–142 de código. Tool-call y visión textual
funcionaron, pero JSON/xgrammar registró `Failed to advance FSM` durante la
prueba estructurada. El smoke largo no produjo OOM ni cierre del runner.

No se asigna BCB8 ni HE20: el resultado no pasó todavía por el harness oficial.
El perfil queda como `SOL-DFlash2-FP8` experimental separado; SOL conserva el
default por BCB8 8/8, tool-use estable y 262K validado. Auditoría completa:
`docs/sol-dflash2-local-audit-20260918.md`.

## 2026-09-18 — Revisión de pendientes: Occamy, ShapeLearn y Agnes

Se cerró una campaña de control sobre los tres candidatos que todavía no tenían
una comparación agentiva directa en esta instalación. Se usó el mismo pack
determinista de ocho tareas `artifacts/bigcodebench-hard-ubuntu-8.json`,
temperatura baja y ejecución directa contra `llama-server` CUDA en las 2× RTX
3090. Esto es **BCB directo**, no el BCB8 LC-H1: mide la capacidad de producir
el código correcto sin el ciclo completo de herramientas, reparaciones y
compaction del Harness.

| Perfil | Texto / herramienta | Visión | Contexto | BCB directo | Diagnóstico |
|---|---:|---:|---:|---:|---|
| **OCCAMY** | 164,07 TG en el smoke; 163,69 TG con tool-call válido | **725,5 PP / 162,6 TG**, descripción correcta | **262K cargado y estable** | **1/8**, media 161,7 TG por tarea | Rápido y multimodal; los fallos fueron de implementación (diff, transferencias, archivos, tipos y validación de excepciones), no de runtime |
| **QWEN38-SHAPELEARN** | 53,64 TG de referencia con MTP3; 84,95 TG en tool-call de esta sesión | **548,7 PP / 59,0 TG**, descripción correcta | **262K cargado y estable** | **1/8**, media 80,0 TG por tarea | MTP3 y visión funcionan; perdió casos por formato/semántica de código y un caso truncado |
| **AGNES** | 32,94 TG con tool-call válido | **505,6 PP / 32,2 TG**, descripción correcta | **262K cargado**; escalera completa aún pendiente | **1/8**, media 31,7 TG por tarea | Multimodal funcional, pero lento; no muestra ventaja agentiva y tuvo fallos de precisión/contrato |

Los tres perfiles pasaron además una prueba de carga con `n_ctx_slot=262144`
cuando correspondía, sin OOM ni cierre del servidor. La prueba de visión usó el
`mmproj` real de cada modelo y `parallel=1`; por eso se registra como **visión
funcional smoke**, no como una nueva validación 4/4. El tool-use se validó con
una llamada `calculator` reproducible, no con el pack completo de herramientas.

Los casos BCB fallidos no deben leerse todos como fallos del modelo: varios
exponen el mismo patrón de tareas (formatos de diff, transferencias duplicadas,
tipos `int`/`str`, excepciones, fechas y dependencias pandas/NumPy). Aun así,
el 1/8 directo es la única cifra comparable que tenemos hoy para estos tres
candidatos y no justifica subirlos sobre SOL. HE0/HE20 LC-H1 quedan pendientes
porque el runner oficial no se pudo ejecutar en este checkout Linux; no se los
convierte artificialmente en 0/20.

### Decisiones resultantes

- **SOL permanece default**: BCB8 agentivo 8/8, tool-use estable, visión 4/4 y
  262K validado.
- **Occamy** conserva el mejor throughput multimodal experimental, pero su
  BCB directo 1/8 impide considerarlo reemplazo de SOL.
- **ShapeLearn** conserva una ruta útil para contexto largo con MTP3 y visión,
  pero su BCB directo 1/8 no demuestra calidad agentiva.
- **Agnes** queda como candidato multimodal de laboratorio: carga 262K y visión
  correcta, pero es claramente más lento y no mejora la calidad observada.
- Opti, NInfer, ASTRA, EXL3 y GSQ-RCO+DFlash2 no se repitieron aquí porque sus
  bloqueos y métricas pendientes ya están documentados con el runtime específico
  de cada uno; repetir el mismo smoke no produciría evidencia nueva.

## 2026-09-18 — Escalera oficial LC-H1: Occamy, ShapeLearn y GSQ-RCO

Se corrigió el bloqueo de infraestructura que dejaba estos perfiles en
`not-ready`: se compiló el daemon Linux Release, se registró el binario CUDA
Ampere `b10658`, se escaneó el root real del Disco D y se ejecutó la escalera
oficial HE0 → HE20 → BCB desde el Control API del mismo Harness.

| Perfil | HE0 | HE20 | BCB8 | Velocidad Harness | Diagnóstico final |
|---|---:|---:|---:|---:|---|
| **OCCAMY** | **1/1 válido** | **20/20 válido** | **3/8**, calidad | 143,59 tok/s BCB; TTFT medio 8.638 ms | Runtime sano; 2 reparaciones; fallos de semántica/contrato |
| **QWEN38-SHAPELEARN** | **1/1 válido** | **20/20 válido** con `Con fases` | BCB bloqueado por salida previa a tools | 77,91 tok/s HE20; TTFT medio 2.283 ms | HE20 estándar bloqueado por `too much text`; no CUDA |
| **GSQ-RCO + DFLASH2 Q2** | **1/1 válido** | Cancelado en prompt 5/20 | Pendiente | 29,09 tok/s HE0 | DFlash2 carga y funciona; HE20 no es operacionalmente competitivo a 81K + drafter |

ShapeLearn fue repetido con una política compacta después de que el HE20
estándar fuera detenido por el guard de 32.000 caracteres previos a tools. Se
rehizo HE0 antes de aceptar la nueva evidencia, por lo que los fingerprints no
se mezclan. El BCB compacto volvió a activar el mismo guard y queda como
`BCB bloqueado por protocolo de agente`, no como cero de calidad.

Occamy deja de ser “BCB pendiente”: su número oficial es **3/8**, por debajo
de SOL (8/8), aunque conserva el mejor throughput multimodal experimental de
esta tanda. GSQ-RCO queda experimental: HE20 fue cancelado en prompt 5/20 por
latencia operativa no competitiva, y BCB no se inicia sin HE20 válido.

Evidencia persistente adicional:
`artifacts/validation-20260918/lc-h1-occamy-shape-gsq.json`.
