# Auditoría de validación de perfiles — 2026-09-14

## Alcance

Se revisaron los perfiles del listado operativo contra la evidencia
persistida en `docs/`, `artifacts/`, `assets/system_profiles.json` y las
pruebas ejecutadas en Ubuntu con 2× RTX 3090 y P2P disponible. Se separaron
cuatro estados que antes aparecían mezclados:

- **Validado:** prueba reproducible y compatible con la configuración indicada.
- **Histórico:** resultado válido de otra variante o campaña, no repetido con la
  configuración actual.
- **No aplica:** el modelo es texto-only o no tiene un proyector de visión
  compatible; no es una validación pendiente.
- **Falló/bloqueado:** se intentó y la salida, carga o estabilidad no cumple el
  criterio de promoción.

Las pruebas de esta auditoría no cambian automáticamente el dropdown. Un BCB
directo ejecutado sobre un servidor es evidencia funcional útil, pero no se
presenta como equivalente al BCB completo del harness de agente de LlamaCode si
no pasó por HE0, HE20, reparación y tool-use.

## Pruebas nuevas

### QWEN38-Q8 — texto a 262K y BCB directo

Se utilizó `Qwen3.8-27B-UD-Q8_K_XL.gguf`, MTP2, KV `q8_0`, split por capas y
`--ctx-size 262144`.

| Prueba | Resultado | Lectura |
|---|---:|---|
| Carga + `/health` a 262K | OK | El contexto máximo operativo carga en esta ruta. |
| Smoke de texto | OK | Respondió correctamente a consulta factual y código. |
| BCB directo, 8 tareas | **8/8** | Las ocho tareas canónicas ejecutaron correctamente. |
| TPS medio del BCB directo | **51,74 tok/s** | Medido sobre generación de 323–1.136 tokens por tarea. |
| MTP en código | OK | Aproximadamente 56/58 tokens aceptados en la corrida de control. |
| BCB completo del agente LC-H1 | No repetido | El 8/8 directo no reemplaza todavía el score histórico del harness. |

La prueba también encontró una diferencia de estabilidad importante: Q8 sin MTP
falló con `CUDA illegal memory access` en un prefill, mientras que MTP2+Q8 fue
estable para texto a 262K. Por eso el perfil se conserva como experimental y no
se declara “promovido” sólo por el 8/8 directo.

### QWEN38-Q8 — visión

Se cargó el `mmproj-BF16.gguf` compatible con Qwen3.8-27B usando la imagen
`assets/app_icon.png`.

| Configuración | Resultado | Estado |
|---|---|---|
| MTP2 + KV Q8 + visión + 32K | `CUDA illegal memory access` en `ggml_cuda_op_gated_delta_net_fused_cache` | **Falló; no promover** |
| Sin MTP + KV Q4 + visión + 16K | Descripción correcta de la imagen; 135,48 tok/s de prefill y 23,48 tok/s de decode | **Control visual validado** |

Conclusión: QWEN38-Q8 tiene capacidad visual comprobada, pero no en la receta
prioritaria MTP2+KV Q8. Se informa como “visión experimental, sólo control
KV Q4/sin MTP” y no como visión estable del perfil completo.

### TERRA — visión

Se cargó ThinkingCap Qwen3.6-27B con su `mmproj` compatible, contexto 64K,
KV Q8 y split por capas. Con `assets/app_icon.png` respondió correctamente
identificando la llama, los anteojos luminosos y el fondo neón. La medición fue
de aproximadamente 146,11 tok/s de prefill y 39,01 tok/s de decode.

Esto valida la ruta visual de TERRA a 64K. La prueba fue un smoke sin MTP para
aislar visión; el BCB histórico 6/8 y el perfil MTP4 no se reemplazan por este
único caso visual.

La revalidación del 14/09 repitió la receta del lanzador Linux con MTP4,
`--ctx-size 65536`, KV Q4, split por capas y el `mmproj` cargado. También se
repitió un control sin MTP con la captura de almacenamiento. Ambos arranques
fueron correctos y respondieron a la imagen; el MTP registró aceptación 4/4.
Por lo tanto TERRA puede conservar visión en su configuración actual. La ruta
sin MTP sigue siendo el fallback si una actualización del binario vuelve a
mostrar incompatibilidad entre MTP y entradas visuales.

### METEOR — visión actual

El BigBang-v1 y su `mmproj` sí están instalados ahora en el root de modelos de
Linux. Se probó la receta operativa de METEOR a 64K, KV Q8, split por capas,
batch 256/ubatch 64, cont-batching y sin MTP. El servidor cargó el proyector,
respondió correctamente a la imagen y alcanzó 61,69 tok/s en el decode del
smoke. METEOR queda así con visión validada en una ruta estable sin MTP; las
cifras históricas de throughput MTP no se trasladan automáticamente a esta
variante visual.

### QWEN38-VISION — variante segura

El Qwen3.8-27B UD-Q4_K_XL regular y su `mmproj-BF16.gguf` también están
instalados. Se probó a 32K, KV Q4, sin MTP, split por capas y `mmproj` en CPU
para no consumir VRAM adicional. El modelo cargó y describió correctamente la
imagen; el prefill fue de aproximadamente 37,6 tok/s y el decode de 36,4
tok/s en la captura grande.

Se agregó el perfil explícito `QWEN38-VISION` a `profiles/models.json` y
`profiles/launches.json`. No reutiliza QWEN38-Q8: mantiene MTP desactivado y
KV Q4 porque la prueba Q8+MTP+visión termina en `CUDA illegal memory access`.
Es una variante visual experimental de 32K, no un reemplazo del perfil de
262K para texto.

## Revisión de los perfiles que todavía no tienen visión

Se verificó si era seguro adjuntar un `mmproj` a los perfiles que siguen siendo
texto-only:

| Perfil | Evidencia local | Decisión |
|---|---|---|
| **SOL** | La receta vigente es Qwen3.8-27B AutoRound INT4 en vLLM TP2/P2P, MTP4 y KV FP8. Esa variante tiene verificación visual **4/4** junto con BCB 8/8. El fallback GGUF no tiene la misma validación. | Mantener SOL como principal y documentar la visión sólo para la receta vLLM/AutoRound exacta; no transferirla al fallback GGUF. `QWEN38-VISION` cubre la ruta local reproducible separada. |
| **QWEN38-Q8** | El `mmproj-BF16` carga, pero la solicitud visual termina en acceso ilegal de CUDA con KV Q4 y sin MTP. Reducir batch/ubatch no lo resolvió: una receta abortó al cargar y otra volvió a fallar dentro de CUDA. | No agregar visión al perfil Q8. Mantenerlo texto-only experimental. |
| **ASTRA** | El `mmproj-BF16.gguf` oficial de Flash-Next ahora carga y elimina el mismatch anterior, pero el texto sigue devolviendo `/` repetido; la visión con proyector en GPU termina en `CUDA illegal memory access` y con proyector en CPU también devuelve `/`. | No agregar visión ni mejorar el BCB: el backend actual no produce una salida válida. Mantener ASTRA como texto/contexto experimental. Ver la [auditoría específica de ASTRA](astra-vision-bcb-repair-audit-20260914.md). |
| **GALACTA / DEEPSEEK FUSION** | Los artefactos DeepSeek locales no tienen `mmproj` compatible ni una ruta multimodal validada. | Texto-only; no inventar visión con un proyector ajeno. |
| **NINFER-QWEN38** | El contenedor `.ninfer` probado no expone `mmproj` y su runtime validado no tiene entrada multimodal. | Texto-only. |
| **LUNA / MINI** | Ling 3.0 Tiny y MiniCPM5-2B instalados no tienen proyector visual compatible en el catálogo. | Texto-only. |

Resultado: no hay otra incorporación visual segura para esos perfiles. La tabla
de capacidades queda sin falsos positivos: visión validada en SOL sólo para la
receta vLLM/AutoRound TP2/P2P, QWEN35-A3B, TERRA y METEOR; QWEN38-Q8 sólo tiene
un control visual sin MTP/KV Q4 y QWEN38-VISION es la variante experimental
reproducible. ASTRA, GALACTA, DEEPSEEK FUSION, NINFER-QWEN38, LUNA y MINI no
reciben una marca de visión.

## Corrección de LUNA/Ling y revalidación del HE0

Durante la repetición controlada del tool-call de Ling se encontró una causa
concreta del HE0 `0/1`: el servidor devolvía un contenedor JSON válido, pero
incrustaba el siguiente par XML dentro del valor anterior. El payload real era
equivalente a:

```json
{"path":"solution_HumanEval_0.py</arg_value><arg_key>content</arg_key>\n<arg_value>def add(a, b):\n    return a + b"}
```

LlamaCode ahora detecta únicamente este patrón acotado en el ensamblado de
tool-calls nativos, recupera `path` y `content`, y deja intactos los demás
argumentos y respuestas de texto. La regresión `normalizesLingTaggedToolArguments`
pasó dentro de `test_agent_wire`: **50/50**.

La pasada headless con la configuración persistida no es un resultado de
calidad: el registro del daemon no resolvió el binario para LUNA y abortó antes
de cargar el modelo (`startServer abort: perfil inválido ... No binary
selected`). Con la configuración del repositorio, en cambio, el servidor
CUDA cargó correctamente Ling y el endpoint respondió; la campaña estándar se
quedó en el prompt 2/7 y fue cancelada sin score. Por lo tanto el histórico
sigue siendo **HE0 0/1**: el arreglo queda listo, pero todavía no hay una
repetición end-to-end que permita convertirlo en `1/1`.

## Revisión de históricos y alias

Los documentos anteriores mezclan nombres de producto que cambiaron de modelo.
La tabla operativa debe interpretar los resultados así:

| Etiqueta que aparece en históricos | Evidencia que realmente representa | Tratamiento actual |
|---|---|---|
| **LUNA** en `context-matrix-terra-luna-meteor-2026-09-07.md` | ThinkingCap Qwen3.6-27B, HE0 1/1, HE20 20/20, BCB 6/8, ~56,84 tok/s | Reasignar a **TERRA**, que es el alias actual de ThinkingCap. No mezclarlo con Ling. |
| **TERRA** en históricos de Qwen3.8/Qwen 28B | Variantes Qwen3.8 con BCB 8/8 y rutas de 63,94–71,51 tok/s | Marcar como Qwen3.8/TERRA legacy; no usarlo para puntuar el ThinkingCap actual. |
| **LUNA** actual | Ling 3.0 Tiny Q6, ~200,95–206,13 tok/s, tool-call directo válido, HE0 0/1 | Mantener HE0 bloqueado hasta repetirlo con el binario registrado; el nuevo parser corrige una causa observada, pero no aporta todavía un score. |
| **METEOR** | BigBang Q4_K_M reparado, BCB histórico 3/8 y ~211,18 tok/s | Histórico válido sólo para el artefacto BigBang exacto; ahora además tiene visión actual validada en la receta estable sin MTP a 64K. |
| **DEEPSEEK FUSION** | Corridas leloch/Q2-Q4 de 284B, con BCB parcial o histórico | Conservar como histórico por variante y configuración; no presentarlo como una validación vigente del archivo actual. |
| **ASTRA** | Qwen3.8 Flash-Next con cache de expertos, salida repetitiva/contaminada y HE0 no válido | Fallo de modelo/runtime; no es un score histórico recuperable mediante renombrado o sampling. |
| **NINFER-QWEN38** | Artefacto `.ninfer` reparado, BCB 3/8 con thinking, 120K probado | Resultado válido de esa implementación; no equipararlo a SOL ni a un GGUF Qwen3.8. |

Regla aplicada: un score histórico conserva su valor sólo si coinciden modelo,
quant, KV, backend, plantilla, contexto y agente. Si cambia cualquiera de esos
elementos, queda como referencia histórica y no como validación del perfil
actual.

## Tabla de cierre

| Perfil | BCB / calidad | Visión | Contexto operativo | Estabilidad y decisión |
|---|---|---|---:|---|
| **SOL** | **BCB 8/8 validado** en el harness; tool-use OK | **4/4 validado** en la receta vLLM/AutoRound TP2/P2P; fallback GGUF no validado | **262K validado**; 200K recomendado | Principal y default para coding/agentes |
| **GALACTA** | **BCB 8/8 validado**; 9,65 tok/s | **No aplica**: DeepSeek local texto-only | 131K | Calidad máxima; muy lento |
| **DEEPSEEK FUSION** | **BCB 8/8 histórico**; variante exacta debe considerarse histórica | **No aplica**: texto-only | 131K | Alternativo; no se re-promueve sin repetir con el artefacto actual |
| **QWEN35-A3B** | BCB **4/8**; HE20 20/20 en la evidencia disponible | **4/4 validado** hasta 262K | **262K validado**; recuperación de contexto 240.660 tokens | Mejor candidato multimodal/concurrencia; experimental por calidad BCB |
| **QWEN38-Q8** | **BCB directo 8/8**, 51,74 tok/s; BCB LC-H1 pendiente | Ruta corregida sin MTP: 23,3 tok/s @8K y 23,2 @262K; la campaña nueva abortó en 64K/131K dentro de CUDA fused RMS-norm | 8K y 262K smoke; 64K/131K inestables | Experimental: se quitó MTP2+KV Q8 del lanzamiento; visión sólo en QWEN38-VISION separado |
| **TERRA** | **BCB 6/8** histórico; HE0/HE20 válidos | **2/2 smoke actuales** a 64K: sin MTP y MTP4; aceptación MTP 4/4 | 64K | Visión y razonamiento; estable en la ruta probada |
| **ASTRA** | BCB/HE0 **no válido**: salida contaminada/repetitiva incluso con el `mmproj` oficial | **No validable**: el proyector correcto carga, pero GPU aborta en `mtmd` y CPU devuelve `/` repetido | **262K cargable / 196K operativo validado** | Experimental texto/contexto; no agente principal |
| **NINFER-QWEN38** | **BCB 3/8** con thinking; tool-use smoke OK | **No aplica**: artefacto `.ninfer` probado no tiene mmproj | 120K probado / 131K operativo | Experimental; no reemplaza SOL |
| **METEOR** | **BCB 3/8** histórico/reparado | **1/1 smoke actual** a 64K con BigBang + mmproj, sin MTP; 61,69 tok/s decode en el control | 64K | Throughput/lotes; visión disponible en la ruta estable sin MTP |
| **QWEN38-VISION** | Control visual correcto; no reemplaza el BCB del QWEN38-Q8 | **1/1 smoke actual** a 32K con mmproj, sin MTP y KV Q4 | 32K | Variante experimental dedicada a visión; separada de Q8+MTP |
| **LUNA** | **HE0 0/1** para Ling Tiny; BCB bloqueado | **No aplica**: Ling es texto-only | 131K | Rápido, pero no confiable como agente principal |
| **MINI** | **BCB 1/8**, HE0 1/1 | **No aplica**: MiniCPM5-2B instalado sin mmproj validado | 131K | Auxiliar rápido; no coding principal |

## Decisiones

1. **No se agrega una bandera visual falsa.** SOL queda marcado como visual
   sólo en la receta vLLM/AutoRound TP2/P2P; TERRA y QWEN35-A3B conservan sus
   validaciones; METEOR queda visual en su ruta estable sin MTP; QWEN38-Q8 sólo
   queda visualmente validado como control conservador.
2. **No se cambia SOL.** Sigue siendo el único perfil con BCB completo del
   harness y tool-use estable en la tabla prioritaria.
3. **QWEN38-Q8 conserva el BCB directo 8/8**, pero no se promueve: la ruta de
   lanzamiento queda sin MTP y la campaña nueva reprodujo abortos CUDA en 64K
   y 131K. La visión permanece en `QWEN38-VISION`, una variante separada con
   KV Q4 y sin MTP.
4. **ASTRA, LUNA y METEOR no se pueden “completar” artificialmente:** ASTRA
   falla calidad incluso con el proyector oficial, LUNA falla HE0 y el
   artefacto actual de METEOR no está instalado. Quedan clasificados con motivo
   concreto, no como validaciones silenciosamente pendientes.
5. No quedaron procesos `llama-server` ni cargas CUDA activas al finalizar las
   pruebas. No se modificaron pesos, Windows ni los límites máximos de quant/KV
   del proyecto.

6. El parser de tool-calls de Ling quedó corregido en el código y cubierto por
   regresión. LUNA no se promueve todavía: el registro persistido del daemon
   no resuelve el binario en el primer intento (`No binary selected`); usando
   explícitamente el catálogo del repositorio el servidor sí carga, pero la
   campaña estándar se estanca en el prompt 2/7 y se cancela sin score. El
   histórico HE0 permanece en 0/1 hasta completar una repetición end-to-end.
