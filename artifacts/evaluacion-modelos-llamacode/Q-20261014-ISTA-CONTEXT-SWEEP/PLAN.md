# Plan — ISTA IQ2_XS, barrido de contexto y memoria

**ID:** `Q-20261014-ISTA-CONTEXT-SWEEP`  
**Estado:** Completa; cuatro probes de rendimiento válidos (131K, 262K, 512K, 1M)  
**Lock:** `52166fcb-ce3b-4709-959c-97e04408b1c8`

## Pregunta y criterio

Medir ISTA-DASLab Qwen3.8-Flash-Next GSQ-RCO IQ2_XS con Strata en cuatro límites de contexto: 131.072, 262.144, 524.288 y 1.048.576 tokens. Registrar, por cada corrida, longitud real de prompt, TTFT, prefill tokens/s, decode tokens/s, duración total, pico de VRAM en cada RTX 3090 y pico de RAM del proceso/sistema. El objetivo es capacidad y rendimiento; no puntúa calidad general del modelo.

Un punto cuenta como probe de rendimiento válido si el servidor inicia con el límite indicado, acepta un prompt que ocupa al menos el 95% de ese límite y devuelve los 64 tokens solicitados sin error de transporte/infraestructura. `finish_reason=length` en ese tope es esperado; no se evalúa si la respuesta semántica está completa. Un fallo de carga, OOM, timeout o transporte se informa como límite/infraestructura, nunca como cero de calidad.

## Candidato y configuración fijada

- Modelo: ISTA-DASLab `Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS`, revisión `ed59f92082b1e93c0e96d60a8b11aab089b52f09`.
- Shards SHA-256: `92cee27ae5bbadcd732416a0f7a7f0acc092399dbbe8f5a5efa707c2ec0a49d7` y `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`.
- Runtime Strata 0.1.41, commit `fb58e0dbc8399662c0e47c76578c6e878b14f6cf`, CUDA 12.8.93 / SM86, dos RTX 3090 de 24 GiB.
- Perfil dedicado ASTRA DEFAULT `/home/cristian/.config/LlamaCode/astra-iq2xs-strata.json`, SHA-256 `b4b83171c136d8cb4b1944de532c096276844da5a2cd987d1d1517dd0a73b484`. No editarlo; cada brazo usa una copia efímera en este directorio de artefactos.
- Parámetros conservados: mismos GGUF/pack/tokenizer, `--kv int8`, `--kv-resident 32768`, `--spec 4`, `--spec-min-p 0.70`, caché de expertos y prefill `auto`, `--pcie-frac 0.00`, GPUs 0 y 1, una solicitud a la vez, `cache_prompt=false`.

## Brazos y protocolo

Ejecutar en orden ascendente, reiniciando Strata y cambiando sólo los parámetros de contexto/rope entre brazos:

| Límite | Rope previsto | Prompt previsto | Estado |
|---:|---|---:|---|
| 131.072 | Configuración nativa del perfil (sin escala) | ≥124.519 tokens; 64 tokens de salida | Válida: 124.535 tokens, 95,013% |
| 262.144 | Contexto nativo Qwen (sin escala) | ≥249.037 tokens; 64 tokens de salida | Válida: 249.146 tokens, 95,042% |
| 524.288 | YaRN, factor 2, base original 262.144 | ≥498.074 tokens; 64 tokens de salida | Válida: 498.122 tokens, 95,009% |
| 1.048.576 | YaRN, factor 4, base original 262.144 | ≥996.148 tokens; 64 tokens de salida | Válida: 996.163 tokens, 95,002% |

El prompt sintético se construye con el tokenizer del pack y un needle fijo en posición tardía para forzar el prefill efectivo. Se conserva su texto/token count y SHA-256. Una solicitud sin caché por contexto; muestreo greedy para repetibilidad; sin concurrencia. Timeout duro de 15 minutos por punto y 30 minutos acumulados. La capacidad sólo queda confirmada hasta el mayor punto que complete el prompt ≥95% y la generación.

Un monitor muestrea cada segundo `nvidia-smi` (memoria por GPU/proceso y uso) y RAM del proceso Strata, `MemAvailable` y swap; además se guardan logs del engine/API y el recibo JSON de cada solicitud. Se calculan prefill TPS = prompt tokens / prompt-eval seconds y decode TPS = completion tokens / generation seconds; se conservan también TTFT y tiempo total para no mezclar métricas.

## Guardas antes de cada carga

- Antes de cada brazo, exigir `MemAvailable` ≥32 GiB. El swap ocupado no es por sí solo un bloqueo; se deja intacto. Muestrear PSI y deltas de `pswpin`/`pswpout` cada segundo.
- Monitor final: abortar si `pswpout` aumenta más de 1024 páginas (4 MiB), si `MemAvailable` cae bajo 20 GiB, o si PSI `some avg10` ≥80% o `full avg10` ≥60% durante 15 muestras seguidas. Los umbrales PSI se ampliaron tras conservar los intentos iniciales que dispararon falsos abortos durante la carga del arena. Cada versión del monitor y su resultado se conservan en los recibos; ninguna corrida válida alcanzó un criterio de aborto. Antes de cada brazo se exigieron `MemAvailable` ≥32 GiB, cero procesos de inferencia ajenos y puertos libres.
- Ambas GPU verificadas como RTX 3090 disponibles para esta prueba; confirmar VRAM base, puertos 8350/8898 libres y rutas/hashes del modelo/runtime. Si se supera el límite de 15 minutos por punto o 30 minutos acumulados, detener la secuencia sin matar procesos ajenos ni cambiar swap/config productiva.
- 512K/1M necesitan YaRN explícito; guardar la línea de comando/config exacta. Si el runtime no acepta la escala o el resultado muestra posiciones inválidas, clasificarlos como incompatibles/inconclusos, no como límite de capacidad del modelo.

## Preflight inicial observado a las 2026-10-14T13:52:29Z

- RAM: 123 GiB total, 108,371 GiB disponibles.
- Swap: 7,577 GiB de 8,0 GiB usados; incumple el límite preregistrado de <2 GiB.
- GPU0: RTX 3090, 1.113 MiB usados / 24.576 MiB, utilización observada 21%.
- GPU1: RTX 3090, 108 MiB usados / 24.576 MiB, utilización observada 27%.
- `nvidia-smi --query-compute-apps` no mostró procesos compute. No se descargó ni cargó el modelo; no se inició servidor, no se envió prompt y no se cambió configuración.

**Decisión original:** bloqueada antes de inferencia por un límite de swap usado de 2 GiB. Esta guarda fue reemplazada al reanudar, luego de la pregunta del usuario: se mantiene el swap intacto y se evalúa presión activa.

## Artefactos previstos

- `RESULTS.md`: tabla de los cuatro puntos y clasificación de cada intento.
- `receipts/preflight.json`: hardware, RAM/swap, puertos, procesos y timestamp.
- `receipts/configs/`: config base efectiva y, al reanudar, copias exactas por contexto.
- `receipts/runtime-manifest.json` y `runtime-context-flags.txt`: hash/commit del binario y opciones locales de contexto/YaRN.
- `receipts/runs/<contexto>/`: prompt, hashes, monitor de memoria, logs del engine/API y respuesta cruda.
- `receipts/summary.json`: métricas agregadas sin reemplazar corridas históricas.


## Preflight de reanudación a las 2026-10-14T13:58:29Z

Lock propio `52166fcb-ce3b-4709-959c-97e04408b1c8`. `MemAvailable` fue 107,96 GiB; swap usado 7,54 GiB. En una muestra de 10 s: PSI `some/full avg10=0.00`, `pswpout` no cambió y `pswpin` avanzó 49 páginas (~0,19 MiB). Esto no muestra presión activa. GPU0 tenía 1080/24576 MiB y GPU1 108/24576 MiB; no aparecieron procesos compute, Strata/llama-server ni listeners 8350/8898. Se verificaron SHA-256 del runtime, perfil/config, expert profile, servidor y archivos MTP; tamaños y mtimes de los shards de 68,0 GB coinciden con los recibos, sin rehash completo en esta reanudación.

**Decisión:** continuar en serie sin liberar swap. Antes de cada punto se vuelve a exigir `MemAvailable` ≥32 GiB; durante la corrida se aplican los límites de seguridad descritos arriba para swap-out, PSI sostenida y un piso de 20 GiB disponibles. Evidencia detallada: [`preflight-resume.json`](receipts/preflight-resume.json).


Las muestras de los primeros intentos se conservan: el primer launch falló por ruta relativa del config antes de cargar; los intentos siguientes iniciaron la carga del arena (~39 GiB), pero un umbral PSI del monitor demasiado bajo los cortó antes de que el API quedara listo. En ambos casos no se envió prompt ni hubo swap-out; el umbral se recalibró y las mediciones de esos intentos no cuentan como TPS.


El intento 512K inicial se conservó como incompleto: el monitor antiguo se activó con PSI full máximo de 19,05% durante la carga documentada del arena; el mínimo de MemAvailable fue 66,17 GiB y `pswpout` no cambió. Se amplió el umbral PSI para distinguir esa pausa temporal de falta de memoria o swap-out.


El intento inicial de 1M quedó incompleto por el mismo corte del monitor: PSI máximo 40,74%, con MemAvailable ≥61,94 GiB y `pswpout` sin cambios. El perfil siguió cargando la arena cuando se detuvo; no hubo request ni medición de TPS. Se conserva para no confundirlo con un límite del modelo.


El segundo intento 1M se conservó: el proceso alcanzó 47,57 GiB RSS con 59,34 GiB mínimos disponibles; hubo 7 páginas (~28 KiB) de swap-out global y PSI máximo de 30,38%, antes de que el endpoint quedara listo. No hubo prompt. El pequeño delta global por sí solo no demuestra falta de memoria; se tolerará hasta 4 MiB en el último intento, registrándolo, con el piso de RAM y el límite PSI severo como protección.


## Resultado final — 2026-10-14

Las cuatro sondas se completaron válidamente, una solicitud por contexto y en serie. Cada servidor aceptó un prompt real de al menos 95% del límite y generó 64 tokens; `finish_reason=length` es el tope solicitado, no un error de transporte. El benchmark mide rendimiento/ocupación, no exactitud del needle ni calidad de la respuesta. No se modificó el perfil de ASTRA DEFAULT, que conserva 131.072 tokens.

| Contexto | Extensión | Prompt / ocupación | Prefill / decode | TTFT / petición | RAM pico del árbol / MemAvailable mínimo | VRAM pico total GPU0 / GPU1 | Swap-in / swap-out global |
|---:|---|---:|---:|---:|---:|---:|---:|
| 131.072 | Nativa | 124.535 (95,013%) | 3.265,5 / 139,1 tok/s | 38,14 / 38,64 s | 39,23 / 68,35 GiB | 23.734 / 20.776 MiB | 171 / 0 páginas |
| 262.144 | Nativa | 249.146 (95,042%) | 3.163,8 / 133,2 tok/s | 78,75 / 79,31 s | 40,89 / 66,60 GiB | 23.782 / 20.906 MiB | 1.138 / 0 páginas |
| 524.288 | YaRN ×2 | 498.122 (95,009%) | 2.860,8 / 113,1 tok/s | 174,12 / 174,86 s | 44,31 / 63,22 GiB | 23.352 / 21.912 MiB | 692 / 0 páginas |
| 1.048.576 | YaRN ×4 | 996.163 (95,002%) | 2.232,9 / 85,6 tok/s | 446,13 / 447,24 s | 51,14 / 55,64 GiB | 23.822 / 22.454 MiB | 109.670 / 48 páginas |

VRAM es memoria total observada por tarjeta; el recibo también conserva el delta sobre la ocupación base. RAM pico es RSS conjunto de server+engine, no toda la RAM del host. La disponibilidad mínima de RAM del host descendió desde aproximadamente 107 GiB antes de cargar hasta 55,64 GiB en 1M. `pswpin/pswpout` son contadores globales del kernel, no asignables sólo al modelo; el swap no se vació y al final quedaron usados 7,004 GiB con 107,375 GiB disponibles. La variación de swap no impidió estas corridas.

El prefill baja de 3.265,5 a 2.232,9 tok/s y el decode de 139,1 a 85,6 tok/s entre 131K y 1M; el RSS sube de 39,23 a 51,14 GiB. El tiempo de petición no incluye la carga inicial del modelo. Es una muestra por tamaño y una salida limitada a 64 tokens; repetir con varias seeds/cargas sería necesario para una caracterización estadística. La salida cortada por el límite tampoco valida recuperación de los datos sembrados.

Intentos incompletos de arranque anteriores a cada receipt válido se guardan junto a logs y JSON: 131K, dos abortos del monitor (uno fue una ruta relativa inválida); 262K, un falso aborto PSI; 512K, un falso aborto PSI; 1M, un falso aborto PSI y otro aborto tras 7 páginas de swap-out global. Ninguno alcanzó el endpoint listo ni envió prompt, así que no son resultados de calidad ni fallos de capacidad.

Consolidado reproducible: [`receipts/summary.json`](receipts/summary.json); recibos, prompts y respuestas crudas en `receipts/runs/<contexto>/`; estado del sistema posterior en [`receipts/postflight-cleanup.json`](receipts/postflight-cleanup.json). No se ejecutaron builds ni tests del producto: sólo artefactos de evaluación y documentación.
