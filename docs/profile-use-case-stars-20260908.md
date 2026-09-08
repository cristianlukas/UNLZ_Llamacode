# Perfiles LlamaCode por caso de uso — Ubuntu — 2026-09-08

Esta es la clasificación operativa después de corregir los perfiles que no
cargaban. Las estrellas son relativas a esta PC con dos RTX 3090; no son una
nota universal del modelo.

## Política de precisión

- El cuantizado de pesos no supera Q8. Los perfiles actuales usan Q2/Q4/Q5/Q6
  o IQ3/IQ4, todos dentro del límite solicitado.
- El KV cache activo no supera Q8: se usa `q4_0` o `q8_0`.
- ASTRA fue cambiado de KV F16 a KV Q8/Q8. Sus mediciones anteriores de
  16,25–41,31 tok/s correspondían a F16 y quedan sólo como referencia
  histórica; deben repetirse con la nueva configuración.
- El mmproj BF16 de METEOR es el encoder de visión, no el modelo ni el KV
  cache cuantizado. No se utiliza una cuantización de pesos superior a Q8.

## Matriz de estrellas

| Perfil | Modelo / quant | Velocidad | Calidad / agentes | Contexto | Visión | Estabilidad | Tool use | Uso recomendado |
|---|---|---:|---:|---:|---:|---:|---:|---|
| **SOL** | Qwen 28B Q4_K_M + MTP3, KV Q4 | ★★★★☆ | ★★★★★ | ★★★★☆ · 131K | ☆☆☆☆☆ · no habilitada en este launch | ★★★★★ · BCB 8/8 | ★★★★★ | Default para coding difícil y agentes |
| **GALACTA** | DeepSeek V4 Flash UD-IQ3_S, KV Q4 | ★☆☆☆☆ · 9,65 tok/s | ★★★★★ · BCB 8/8 | ★★★★☆ · 131K | ☆☆☆☆☆ | ★★★☆☆ · experimental | ★★★★☆ | Máxima calidad cuando la latencia no importa |
| **DEEPSEEK FUSION** | DeepSeek Fusion, IQ3/Q4, KV Q4 | ★☆☆☆☆ · 10,55 tok/s histórico | ★★★★★ · BCB histórico 8/8 | ★★★★☆ · 131K | ☆☆☆☆☆ | ★★☆☆☆ · histórico | ★★★★☆ | Alternativa de calidad; no es alias prioritario actual |
| **ASTRA** | Qwen3.8 Flash-Next UD-Q4_K_XL, cache experto 188, KV Q8 | ★★☆☆☆ · 16,8 tok/s en smoke Q8 | ★★★☆☆ · BCB no válido | ★★★★★ · 196K | ☆☆☆☆☆ | ★★★☆☆ · ahora carga; harness pendiente | ★★☆☆☆ | Documentos y sesiones enormes, experimental |
| **TERRA** | ThinkingCap Qwen3.6-27B Q4_K_M + MTP4, KV Q8 | ★★★★☆ · 56–58 tok/s | ★★★☆☆ · BCB 6/8 histórico | ★★★☆☆ · 64K operativo | ★★★★★ | ★★★★☆ · HE0 1/1 | ★★★★☆ | Visión, conversación y razonamiento interactivo |
| **MINI** | MiniCPM5-2B Q4_K_M, KV Q8 | ★★★★★ · 248,90 tok/s | ★★☆☆☆ · BCB 1/8 | ★★★☆☆ · 131K | ☆☆☆☆☆ | ★★★★★ · HE0 1/1 | ★★★☆☆ | Subagentes, clasificación, resúmenes y tareas cortas |
| **LUNA** | Ling 3.0 Tiny Q6_K + Bailing V3, KV Q8, thinking medium, presupuesto 2048 | ★★★★★ · 200,95 tok/s histórico | ★★★★☆ · smoke razonado + tool call estructurado; BCB pendiente | ★★★★☆ · 131K | ☆☆☆☆☆ | ★★★★☆ · carga estable | ★★★★☆ · función y argumentos JSON válidos en smoke | Perfil diario rápido |
| **METEOR** | BigBang-v1 35B-A3B Q4_K_M + MTP5, KV Q8 | ★★★★★ · 211,18 tok/s histórico | ★★☆☆☆ · BCB 3/8 | ★★★☆☆ · 64K operativo | ★★★★☆ · mmproj cargado | ★★★★☆ · carga corregida | ★★★☆☆ | Throughput, lotes y visión; no agente principal |

`★` = una estrella; `☆` = una estrella no obtenida. Las cifras históricas no
se presentan como una nueva medición cuando la configuración cambió.

## Reparaciones aplicadas y evidencia

- **ASTRA:** `--cache-type-k q8_0 --cache-type-v q8_0`, thinking `on`,
  `reasoning_effort=medium`, presupuesto 8192 y sampling de thinking
  (`temp=1.0`). El servidor cargó a 196K y respondió por API. El smoke de 16
  tokens midió 16,80 tok/s de decode; la calidad BCB todavía debe repetirse
  porque el prefill de Flash-Next sigue siendo experimental.
- **LUNA:** ahora usa Ling 3.0 Tiny sin duplicar Qwen 28B, B1024/U256, KV
  Q8/Q8, thinking `medium` y presupuesto 2048. El template Bailing V3
  bundleado produjo una llamada estructurada con `finish_reason=tool_calls`,
  nombre de función y argumentos JSON válidos; HE0/BCB debe repetirse para
  certificar la calidad completa del harness.
- **METEOR:** el modelo estaba asociado por error a stable 121, que es Qwen
  3.8-27B Q5_K_M. Se corrigió a stable 116, el BigBang Q4_K_M instalado, y
  mmproj stable 117. Cargó a 64K con MTP5/KV Q8 y respondió por API con
  aceptación MTP 4/5.
- **SOL:** el servidor volvió a quedar operativo en `127.0.0.1:8031`. También
  se corrigió la serialización del mensaje de presupuesto: `ok now` se estaba
  separando en dos argumentos y provocaba `invalid argument: now`; el perfil
  Linux usa ahora `ok-now`.
- **TERRA:** ThinkingCap ocupa el nivel intermedio por su mejor razonamiento,
  estabilidad y visión; LUNA queda como el escalón de mayor velocidad.
- **TERRA-LEGACY:** el Qwen 28B antiguo queda oculto/deprecated sólo como
  rollback; ya no compite con SOL ni duplica el modelo activo de TERRA.

## Orden recomendado

1. **SOL** para el trabajo diario de coding y agentes.
2. **TERRA** si hay imágenes o se necesita interacción multimodal.
3. **MINI** para subagentes rápidos y tareas auxiliares.
4. **GALACTA** para calidad máxima con mucha paciencia.
5. **ASTRA** para contexto/MoE grande, sólo cuando se acepte el carácter
   experimental.
6. **LUNA** para herramientas ligeras, búsqueda y razonamiento rápido; no
   sustituye a SOL hasta repetir la suite de calidad.
7. **METEOR** para throughput/lotes, no para decisiones autónomas complejas.

La matriz se refiere a Linux. Las reparaciones específicas quedaron en
`platformArgs.linux`; los argumentos Windows existentes se conservaron.
