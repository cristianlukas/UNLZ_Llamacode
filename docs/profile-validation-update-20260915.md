# Actualización de validación de perfiles — 2026-09-15

## Alcance

Se repitieron las pruebas que todavía eran reproducibles en Ubuntu con 2× RTX
3090, P2P PCIe activo y el Ryzen 9 9950X3D. Se respetó el límite del proyecto:
pesos y KV como máximo Q8; los proyectores de visión BF16/F16 se tratan como
componentes auxiliares y no como quant de pesos o KV.

Los resultados marcados como **directos** se ejecutaron contra un endpoint
OpenAI-compatible y no sustituyen automáticamente al BCB completo del agente
de LlamaCode. Para promocionar un perfil siguen siendo necesarias las
compuertas HE0 → HE20 → BCB del harness.

## Validaciones nuevas

### CyberTiel 35B-A3B

Configuración: `cuda-flashnext-2x3090`, split por capas, KV K/V `q8_0`,
contexto 32K, MTP3, sampling conservador.

- Arranque y `/health`: OK.
- Código simple: salida Python válida.
- Tool-use: `read_file` emitido como tool-call nativo con JSON válido.
- HE directo sobre HumanEval/0–19: **19/20 estricto**. El único fallo fue
  `HumanEval/4`, cuya respuesta era semánticamente correcta pero comenzó la
  primera línea sin la indentación del cuerpo de función; no se cuenta como
  20/20 para no ocultar un problema de formato.
- MTP: aceptación variable; en el control de tool-use y código se observaron
  generaciones válidas y aceptación suficiente para mantener MTP3 experimental.
- Visión: smoke correcto con `mmproj-BF16.gguf`; la imagen fue descrita y el
  texto visible fue leído. El control midió aproximadamente 65,62 tok/s de
  prefill y 130,83 tok/s de decode con 1.266 tokens de prompt visual.
- No se ejecutó un BCB completo del agente en esta pasada; queda **BCB
  pendiente**, no cero.

Decisión: CyberTiel gana una validación HE directa y conserva visión/tool-use
operativos, pero sigue experimental. No se promueve sobre SOL: falta BCB
comparable y el modelo es uncensored/abliterated, por lo que no es el default
para agentes autónomos.

### QWEN35-A3B

Se inició el artefacto AutoRound real desde Disco local con vLLM 0.27.1,
TP=2/P2P, KV FP8, contexto configurado a 262K, prefix caching y chunked
prefill. El servidor cargó ambas GPUs correctamente; el log informó un pool KV
de 1.819.120 tokens y concurrencia máxima estimada de 6,94× a 262.144 tokens.

- HE0 directo: **1/1** con thinking desactivado para evitar consumir todo el
  presupuesto en razonamiento oculto.
- HE20: **20/20**, evidencia previa compatible con el mismo artefacto.
- BCB: **4/8**, por lo que continúa experimental.
- Tool-use: `read_file` emitido correctamente por el parser `qwen3_coder`.
- Visión: imagen procesada y descrita correctamente en la receta vLLM/TP2;
  se conserva la validación visual 4/4 existente.
- No aparecieron accesos ilegales CUDA ni OOM en el smoke.

Corrección aplicada: se reemplazó la etiqueta falsa `BCB pendiente` del perfil
por `HE0 directo 1/1`, `HE20 20/20`, `BCB 4/8` y `visión 4/4`. No se lo
promueve a principal porque el BCB sigue debajo de SOL.

### Qwen3.5 auxiliares

Se ejecutó el mismo control directo de 20 tareas HumanEval, contexto 8K, KV
Q8, sin visión:

| Modelo | HE directo | Tiempo medio por tarea | BCB | Visión |
|---|---:|---:|---|---|
| Qwen3.5-9B | **20/20** | 6,82 s | Pendiente | No tiene `mmproj` compatible instalado |
| Qwen3.5-4B | **19/20** | 4,82 s | Pendiente | No tiene `mmproj` compatible instalado |
| Qwen3.5-2B | **19/20** | 2,60 s | Pendiente | No tiene `mmproj` compatible instalado |

Estos scores son controles directos de generación de código; no se presentan
como BCB de agente. Las velocidades PP/TG de la tabla operativa se mantienen
porque este control fue de calidad, no una nueva medición de throughput.

## Revisión de fallos pendientes

### QWEN38-Q8

Se repitió la ventana problemática con PDL desactivado, batch/ubatch reducido,
otra build CUDA y split por filas. El modelo sigue cargando en los smoke de 8K
y 262K, pero falla en 64K/131K dentro de kernels CUDA (MUL_MAT, RMS norm o
scale, según la build); split por filas tampoco inicia porque SM86 no admite
split buffers en esa ruta. No se encontró una combinación estable que lo
arregle.

Se conserva el dato **BCB directo 8/8** de la campaña anterior, pero se marca
como directo y no como BCB completo de LlamaCode. La entrada operativa queda
sin MTP y sin tensor split; la visión sólo se considera válida en el control
separado QWEN38-VISION con KV Q4 y sin MTP.

### ASTRA IQ1_S

La reparación MTP correcta es el head Q8 compartido: carga, acepta tokens y
mantiene tool-use básico. Sigue sin BCB completo y la visión no es válida: el
proyector oficial carga, pero la salida visual no es confiable/puede abortar
en CUDA. No se agrega visión ni se promueve por encima de SOL.

### Perfiles de texto-only

GALACTA, DEEPSEEK FUSION y NINFER-QWEN38 no reciben un proyector ajeno. Sus
resultados HE/BCB permanecen históricos o de texto-only según la variante
exacta; “No aplica” es más correcto que “pendiente de visión”.

## Tabla operativa corregida

| Perfil | Configuración | Velocidad local | HE / BCB / calidad | Contexto | Visión | Estado |
|---|---|---:|---|---:|---|---|
| **SOL** | Qwen3.8-27B AutoRound INT4 · MTP4 · vLLM TP2/P2P · KV FP8 | 74 narr. / 102 código tok/s | **HE0/HE20 válidos · BCB 8/8 · tool-use OK** | 262K validado | **4/4 validada** en la receta vLLM | Principal |
| **GALACTA** | DeepSeek V4 Flash UD-IQ3_S · KV Q4 | 9,65 tok/s | **HE0 1/1 · HE20 20/20 · BCB 8/8** | 131K | No aplica, texto-only | Calidad máxima; histórica pero consistente |
| **DEEPSEEK FUSION** | DeepSeek V4 antirez Q2/Q4 · KV Q4 | 10,55 tok/s histórico | HE0/HE20 válidos en la variante histórica · **BCB 8/8 histórico** | 131K | No aplica, texto-only | Alternativo histórico |
| **QWEN35-A3B** | Qwen3.6-35B-A3B AutoRound INT4 · vLLM TP2/P2P · KV FP8 | 123,98 BCB / 134,4 directo | **HE0 directo 1/1 · HE20 20/20 · BCB 4/8** | 262K | **4/4 validada** | Experimental fuerte; visión, contexto y concurrencia |
| **CyberTiel** | Cyber-Tiel Coder 35B-A3B Q4 · MTP3 · KV Q8 | 183 código / 219 JSON | **HE directo 19/20 estricto** · BCB pendiente · tool-use smoke OK | 262K carga; 184K probado | **Smoke validado** con mmproj | Experimental; no default autónomo |
| **QWEN38-Q8** | Qwen3.8-27B UD-Q8_K_XL · sin MTP · KV Q8 | 23,3 @8K / 23,2 @262K | **BCB directo 8/8** · HE0/HE20 LC pendientes | 8K y 262K smoke; 64K/131K inestables | Sólo control QWEN38-VISION: KV Q4/sin MTP | Experimental e inestable |
| **TERRA** | ThinkingCap Qwen3.6-27B Q4 · MTP4 · KV Q8 | 56–58 tok/s | **HE0 1/1 · HE20 20/20 · BCB 6/8 histórico** | 64K estable | **2/2 smoke actual**; MTP4 y fallback | Secundario; razonamiento y visión |
| **ASTRA IQ1_S** | Qwen3.8 Flash-Next UD-IQ1_S · head MTP Q8 compartido · KV Q8 | 58–60 PP / 24–26 TG | HE/BCB completos pendientes; BCB parcial no comparable | 262K smoke/operativo | No validada; salida visual no confiable | Experimental de contexto largo |
| **NINFER-QWEN38** | Qwen3.8-27B `.ninfer` · MTP3 · INT8 KV | 73–75 @8K / 50–63 @80–120K | HE0 1/1 · **BCB 3/8** | 120K probado / 131K operativo | No aplica, artefacto sin mmproj | Experimental histórico |
| **Qwen3.5-9B** | Q4_K_M · KV Q8 | 2.443 PP / 100 TG | **HE directo 20/20** · BCB pendiente | No medido formalmente | No | Auxiliar con más capacidad |
| **Qwen3.5-4B** | Q4_K_M · KV Q8 | 2.837 PP / 148 TG | **HE directo 19/20** · BCB pendiente | No medido formalmente | No | Auxiliar intermedio |
| **Qwen3.5-2B** | Q4_K_M · KV Q8 | 3.044 PP / 257 TG | **HE directo 19/20** · BCB pendiente | No medido formalmente | No | Auxiliar más eficiente |

## Criterio de promoción

SOL sigue siendo el único perfil con BCB 8/8 completo del harness y tool-use
estable. QWEN35-A3B es el mejor segundo perfil multimodal, CyberTiel el más
rápido de los candidatos con visión pero aún sin BCB, y TERRA el fallback de
razonamiento visual. Los auxiliares Qwen3.5 ya tienen control HE directo, pero
no deben confundirse con agentes de calidad validada hasta completar BCB.

No quedaron procesos llama-server ni vLLM activos al finalizar la campaña.
