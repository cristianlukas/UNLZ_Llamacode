# Historia, descubrimientos y anotaciones de benchmarking

Este archivo es el espejo histórico de [`benchmark-results.md`](benchmark-results.md).
El detalle auditable por perfil está consolidado en el [registro detallado de
perfiles](benchmark-profile-ledger-2026-08.md): conserva identidad, modelo,
quant, binario, configuración, huella, métricas, causa de descarte y estado de
los perfiles no alcanzados. Este historial conserva además la narrativa y los
eventos operativos; ambos documentos se complementan y no reemplazan resultados
anteriores.

## 2026-10-03 — Gemma 4 E4B QAT y Spark-X2.5-4B · no promovidos

Se compararon contra Qwen3.5-4B en Computer Use (24 estados × 3 pasadas),
contrato de tools (5 pasadas), visión con tool (3 pasadas para los modelos con
mmproj) y BCB-Hard-8 directo (una pasada). Spark quedó 2/8 frente a Qwen 1/8,
pero empató el tool contract, perdió un estado en sandwich y no tiene visión;
no hay evidencia LC-H1 para asignarle coding delegado. Gemma QAT dio 0/8 BCB,
4/5 tools y paridad 3/3 visual. No cambian Ingi-Charla, Computer Use, el
harness ni los perfiles. Los JSON por caso, hashes, runtime y condiciones de
repetición están en
[`reddit-small-models-evaluation-20261003.md`](reddit-small-models-evaluation-20261003.md)
y [`artifacts/reddit-small-model-evaluation-20261003/`](../artifacts/reddit-small-model-evaluation-20261003/).

## 2026-09-30 — Aura y agentes locales de horizonte largo

Se comparó la demo de 2048 y el repositorio público Aura con las capacidades y
pruebas existentes de LlamaCode. **No se cambian código, harness, perfiles ni
sampling**: la demo es una corrida única sin ablación apareada, y la prueba no
establece generalidad fuera del entorno 2048. Sí se registra como criterio
futuro la ablación de capacidad con tareas resolubles por el control, presupuesto
igual y delta incierto reportado como tal. No repetir las suites Computer Use
48 estados/720 requests ni compactación de cinco resets para esta hipótesis.
El análisis, el protocolo propuesto y los artefactos previos concretos están en
[`aura-long-horizon-audit-20260930.md`](aura-long-horizon-audit-20260930.md).

## 2026-09-30 — Ornith 1.5-9B + DFlash en RTX 3090

Se probó el target Ornith 1.5-9B Q4_K_M con drafter DFlash target-specific
Q4_K_M en `llama-server` CUDA/SM86. El target cargó en modo normal y en
`draft-dflash` (`block_size=16`, `n-max=7`). El decode corto mediano subió
82,04 → 132,70 tok/s (+61,8%); el control Qwen3.5-9B MTP3 alcanzó 137,31
tok/s. En el contrato Computer Use (48 casos), Ornith target-only y DFlash
coincidieron en las 48 elecciones y lograron 47/48, seguridad 28/29; Qwen3.5
MTP3 logró 48/48 y 29/29. En BigCodeBench-Hard-8, Ornith+DFlash obtuvo 1/8,
igual al resultado previo de Qwen3.5-9B en esos IDs. No se promueve perfil ni
se cambia el harness, Computer Use o Ingi-Charla. La prueba no evaluó voz
acústica, visión por screenshot ni LC-H1 completo.

Los dos GGUF de evaluación se borraron el 2026-09-30 por pedido del usuario; se
conservan hashes, resultados y JSON/scripts en
`artifacts/ornith-1.5-evaluation-20260930/` para no repetir la misma matriz:
[auditoría detallada](ornith-1.5-9b-dflash-evaluation-20260930.md).

## 2026-09-28 — Corrección de ADV v1: 3 graders rotos

Revisando por qué SOL y Flash-Next fallaban exactamente las mismas 3 tareas de
ADV, resultó que los graders contradecían sus consignas:

- **`safe_path_join` y `sql_parameterization`:** el mismo doble escape que
  rompía los `\n` convirtió la prueba de NUL en `'bad\\x00name'`, una barra
  literal. Los modelos rechazaban el NUL real y aceptaban ese nombre válido,
  que es lo correcto.
- **`deadline_scheduler`:** esperaba `['d','a']` con `now=10`, eligiendo un job
  con deadline 5, aunque el enunciado excluye `deadline <= now`. Los valores
  esperados ahora siguen la consigna: `['b']`, `['expired','d','b','a']` y `[]`.

Re-puntuación de los artefactos guardados: **SOL 10/10** (corridas del 23/9 y
del 27/9), **Flash-Next 10/10** y **ASTRA 5/10**. ASTRA falla de verdad en
TTL, JSONL y config, y le faltan 2 tareas por timeout. Arreglo con test en la
rama `session/adv-grader-fix` (`a1dd395`, gate 77/77): el test rechaza
cualquier barra doble en los graders y valida los tres con una solución que
sigue la consigna y otra defectuosa. La copia instalada en la app ya tiene los
graders corregidos (backup `.bak-20260928-pre-grader-fix`). Donde este
historial dice "ADV 7/10", el valor corregido es 10/10.

## 2026-09-28 — Flash-Next W4A16-FP8PLE medido contra SOL, con cuarentena de VRAM

La investigación de la falla de la ASUS
(`C:\Users\cristian\gpu0-vram-diagnostico\INFORME_COMPLETO.md`) dejó una
mitigación en Linux que desbloqueó la medición:

- `fbscan hold`: cuarentena física de 64 KiB sobre las 1.636 direcciones malas.
- `rmtrace.so` (LD_PRELOAD): reintenta a 64 KiB las reservas de 2 MiB que la
  cuarentena fragmenta.

Con las dos cosas, `vram_integrity_test.py` dio 0 palabras malas en 21 GiB de
la ASUS, y Flash-Next cargó con las 48 capas verificadas en las dos placas.

Ajustes necesarios en esta PC:

1. **Hot cache por placa.** hot84 en las dos placas carga, pero la ASUS se
   queda sin memoria en el primer request (el escritorio y la cuarentena le
   restan ~0,9 GiB). hot80 tampoco alcanzó. Recortar las dos placas por igual
   desperdiciaba la PNY, así que se agregó un parche local mínimo al runtime
   (imagen `qwen38-flash-next-2x3090:v0.3.0-perrank`):
   `VLLM_WNA16_STATIC_HOT_CACHE_SIZE_BY_RANK="76,84"`, un tamaño por dispositivo.
   Sin la variable, el comportamiento no cambia. El log confirma 199 contra
   208 MB por capa.
2. `rmtrace.so` montado en los contenedores de Flash-Next y de SOL (override de
   compose `vram-quarantine.override.yml`, sin tocar `mtp.yml`).
3. 64 GiB de swap temporal para la carga (queda ~31 GiB en uso con el server
   arriba y ~108 GiB de RAM ocupada).

Resultado, con el mismo harness y la misma ventana que SOL (tabla completa en
[`benchmark-results.md`](benchmark-results.md)):

- **Calidad: paridad.** HE0 1/1, HE20 20/20, BCB8 8/8 (3/8 al primer intento
  contra 4/8 de SOL) y ADV **10/10**, igual que SOL (medido 7/10 con las mismas 7
  tareas; las otras 3 eran graders rotos, ver la corrección de abajo).
- **SUPERIOR en prefill largo:** 1.984 PP a 131K (SOL 1.363) y 2.159 PP a
  257K (SOL 910). A 257K llega 164 s antes al primer token, con decode igual o
  mejor (52,4 contra 49,7).
- **INFERIOR en todo lo demás:**
  - Decode corto: 66/45 TG, contra 105/67 de SOL.
  - Charla: TTFT de 3,0 s contra 0,62 s. El prefill de cada turno pasa por
    los expertos en RAM.
  - Computer Use: 46/48 y seguridad 27/29, repetido en dos cargas, contra
    48/48 y 29/29.
  - Tiempo agentivo: HE20 2,4× más lento y ADV 2,9× más lento.
- Visión (hot80, ASUS=72/PNY=80): 3/3, igual que SOL.

Veredicto: **perfil superior sólo para prompts ≥128K** (análisis de documentos o
repos largos de una sola pasada). No reemplaza a SOL como default de agente,
Charla ni Computer Use. El 80 tps del post no se reproduce en esta PC: da 66
en código y 45 en narrativa, con 4,5 GiB menos de RAM, la ASUS recortada a 76
y el escritorio en GPU0. La config exacta del post (hot88) no se probó: ya
hot84 simétrico da OOM en la ASUS.

Lanzador reproducible: `artifacts/flashnext-albucino-20260927/serve.sh` más
`env/perrank-76-84-256k.env` y el runtime `/home/cristian/src/fn-runtime-q`
(clon fijado en `b395412`, con `rmtrace` en `docker_serve.sh`). Resultados:
`fnbench_fn_perrank_76_84.json`, `fnbench_fn_vision_72_80.json`,
`fnbench_sol_quarantine.json` y las corridas `benchmark-runs/*_20260928_*`.

## 2026-09-27 — Flash-Next W4A16-FP8PLE en Linux: no evaluable por VRAM defectuosa en GPU0

> **Superado el 2026-09-28** (entrada de arriba): la cuarentena de VRAM
> permitió medirlo.

Se retomó el post de LocalLLM (albucino W4A16-FP8PLE, hot88/220k, "80 tps /
2k+ prefill") en Ubuntu, que sí tiene los 123 GiB que la auditoría del
2026-09-26 no tenía. Se bajó el checkpoint fijado (`ef55414…`, 120 GiB,
SHA256SUMS OK) y se compiló localmente la imagen v0.3.0 del mantenedor sobre la
misma base. El check de P2P/custom all-reduce pasó.

**Resultado: no evaluable en esta PC.** Las tres variantes (hot84/256k del
mantenedor, hot88/220k del post y hot80) cortan la carga con
`tiered packed-byte mismatch`, siempre en el worker que corre sobre la RTX 3090
**ASUS** (`01:00.0`). La otra placa termina las 48 capas. Descartes, uno por uno:

| Hipótesis | Prueba | Resultado |
|---|---|---|
| Config del post | hot88, hot84, hot80 | Falla igual (capa 31–35 de TP0) |
| Swap insuficiente | 28 GiB y después 64 GiB, como el mantenedor | Falla igual |
| Pesos en NTFS (ntfs3) | Copia verificada en imagen ext4 por loop | Falla igual |
| Presión de RAM / caché | `drop_caches` cada 10 s, pico de swap 11 GiB | Falla igual |
| Rank del runtime | `CUDA_VISIBLE_DEVICES=1,0` | **El fallo sigue a la placa ASUS** |
| VRAM de la ASUS | Test dentro de la GPU, sin PCIe, 6 patrones | **1.636 palabras con bits 25/27/29/31 clavados en 1 (`0xAA000000`); la PNY da 0** |

La falla es determinística: mismas direcciones físicas entre procesos, un solo
byte lane, y no cambia con ventiladores al 100 % y 250 W. Las GeForce no
remapean filas. Cualquier carga que ocupe la zona alta de la VRAM de GPU0 puede
corromperse sin aviso. El runtime de Flash-Next la detecta porque verifica cada
copia de expertos; llama.cpp y vLLM estándar no verifican nada. Test
reproducible: `tools/vram_integrity_test.py`. Informe y pasos para replicarlo en
Windows: [gpu0-asus-3090-vram-fault-20260927.md](gpu0-asus-3090-vram-fault-20260927.md).

**Línea de base SOL del mismo día**, con el harness de la app (`build_astra`),
`agent-maximo` y timeout 1800 s: HE0 1/1, HE20 20/20, BCB8 8/8 (4/8 al primer
intento, 2 reparaciones, 865 s) y ADV 7/10 (10/10 con los graders corregidos el
2026-09-28). Es idéntica a la histórica. ADV
se puntuó con los graders ocultos (`artifacts/flashnext-albucino-20260927/adv_grade.py`),
que reproducen exactamente el 7/10 de SOL y el 3/10 de ASTRA del 23/9.

Hallazgos colaterales:

- **SOL no arrancaba en Linux**: el compose montaba un `models-cache` vacío en
  `~/.cache`, y los pesos estaban en `D:\Models\llamacpp\club-3090`. Se
  arregló con un `.env` (`MODEL_DIR`) en el directorio del compose.
- **ADV v1 puntuaba 0/10 en la app en Linux**: los graders tenían `\n`
  doble-escapado y no había `python`. El arreglo, con test, quedó en la rama
  `session/adv-grader-fix` (`99e7dc7`), gate 77/77.

Flash-Next queda **sin clasificar** (ni superior ni inferior) hasta repetir la
campaña con la placa reparada. Los pesos siguen en
`models/Qwen3.8-Flash-Next/albucino-w4a16-fp8ple` y la imagen
`qwen38-flash-next-2x3090:v0.3.0-local` queda para ese reintento. Artefactos:
`artifacts/flashnext-albucino-20260927/`.

## 2026-09-27 — `-sm tensor` y Q6 del hilo "Just bought a second 3090"

El hilo de LocalLLaMA recomienda, para dos 3090: dejar Q4 por Q6/Q8,
`-sm tensor` en llama.cpp (densos más rápidos), vLLM TP2 con FP8 + DFlash2,
Flash-Next con el repo de DominikBucko y un subagente dedicado en la segunda
placa. Flash-Next/DominikBucko (128 GiB de RAM) y DFlash2 en vLLM (crash en SOL)
ya estaban auditados. Esta vez se midió en Windows lo que faltaba.

**Split tensor: SUPERIOR.** En Qwen3.8-27B ByteShape IQ4_XS con MTP3 y
visión, b10964, tensor con KV q8 rindió 119,8/79,7 TG (código/narrativa)
frente a 83,7/60,7 de layer, y 66,0 frente a 46,8 de decode tras 26K de
prompt, con 1.070 frente a 858 de PP. `llama-bench` confirma +26–32% de TG y
sólo −13% de PP en prompts cortos. El investigation doc del 2026-09-18 decía
que tensor no admitía KV cuantizado. Con b10964 **KV q8 funciona y es la
variante más rápida**, así que se respeta el tope Q8 de la política. La calidad
queda en paridad: BCB8 directo 1/8 en el mismo ítem, Computer Use 48/48,
seguridad 29/29, coding 3/3 y visión 3/3, con la latencia de visión-tool
bajando de 0,63 a 0,51 s. Se agregó
`sys-bench-qwen38-byteshape-tensor-q8-mtp3-131k` a la cola de benchmark.

**Q6_K_XL: INFERIOR.** Con layer da 65,1/45,3 TG y el mismo 1/8 de BCB8
directo, en 55 s. Con tensor o con visión no entra. El perfil
`sys-bench-qwen38-27b-q6kxl-layer-mtp3-32k` queda como historial `manualOnly`.

**Descubrimiento operativo.** Windows no tiene pagefile, y WDDM cuenta la VRAM
contra el commit. Con 61,7 GiB de límite, el techo lo pone el commit y no los
48 GB de VRAM. El default `--cache-ram` de 8 GB mata el servidor sin mensaje
al restaurar la caché después de un prompt largo, y le pasa también al perfil
layer 262K. `--cache-ram 1024` lo estabiliza. Además, los `taskkill` con PID de
MSYS no matan el `llama-server` nativo: los servidores huérfanos contaminaron
las primeras corridas, que se descartaron. Detalle y tablas:
[`reddit-dual-3090-tensor-split-audit-20260927.md`](reddit-dual-3090-tensor-split-audit-20260927.md).

## 2026-09-26 — NInfer-4090 Windows y Ternary Bonsai 2 27B (post LocalLLM)

El post propone NInfer-4090 Windows (prefill int8, MTP + n-gram, KV E8) y
Ternary Bonsai 2 27B. **El motor no corre en 2× RTX 3090**: exige compute
capability 8.9 en CMake y en runtime, y usa FP8 `e4m3` de Ada. Sus ideas ya
están cubiertas o en curso: MTP + n-gram existe como `draft-mtp,ngram-mod`
(`sys-bench-qwen38-udq4-mtp3-ngram`, BCB8 8/8) y el prefill W4A8 llegó al
upstream SM86 `ninfer-3090` el 22/09 (otra sesión evalúa el 0.6.1).

Se probó localmente **Ternary Bonsai 2 27B PQ2_0** con el fork llama.cpp de
PrismML (b10743, CUDA 12.4) en una RTX 3090: pp512 1.234 / tg128 59,4 tok/s,
12,3 GB con visión a 64K. Computer Use v1 y hard: 100% exactitud y seguridad,
mediana 318–445 ms. Escalera LC-H1: HE0 1/1, HE20 20/20 en 219 s, **BCB8 2/8
en 1.361 s**.

Veredicto: **`[INFERIOR agente / SUPERIOR VRAM]`**. Inferior a todo Qwen3.8
(8/8) y a los FAST (3/8) en coding agentivo; superior en huella (27B + visión
en una placa de 24 GB con la mitad libre). Perfil manual
`sys-bench-bonsai2-27b-pq2-64k` y motor de catálogo `prism-ternary`.

Aclaraciones: la máquina es 2× RTX 3090, pero ni NInfer-4090 ni NInfer-3090
reparten entre placas; la ventaja dual sigue siendo de SOL. NInfer-3090 **no**
se volvió a correr (referencias: BCB8 3/8 del 08/09 y el fallo del kernel con
Huihui 0.6.1). Queda pendiente el 0.6.1 con el artefacto oficial y el prefill
W4A8. El GGUF de Bonsai se envió a la papelera tras medir (7,3 GB); el perfil
queda como registro histórico.

Detalle: [auditoría NInfer-4090 + Bonsai](ninfer-4090-bonsai-reddit-audit-20260926.md).

## 2026-09-26 — Liquid LFM2.5-VL-3B-DSpark: ventaja sólo en decode

Se contrastó el post de Liquid AI con `LFM2.5-VL-3B` F16 y su drafter DSpark F16 en una RTX 3090, usando llama.cpp oficial b10964 y una fixture de configuración de Windows. Se agregaron el control, DSpark n=8 y DSpark n=9 como perfiles manuales. En dos tareas visuales de lectura/descripción, la primera solicitud decodificó 2,30–2,35× más rápido con n=8 y 2,26–3,33× con n=9. Son tareas y mediciones pequeñas, no una estimación general del rendimiento ni de la calidad.

La prueba Computer Use se repitió con el schema real de `desktop_click` de LlamaCode y sin ejecutar la acción. Los tres perfiles generaron una llamada JSON válida, pero todos propusieron el centro de la pantalla `(0.5, 0.5)` en vez del centro visible del control `(≈0.88, ≈0.296)`. La mediana end-to-end fue 895 ms control, 987 ms n=8 y 890 ms n=9; por lo tanto, DSpark no mejoró esta interacción. n=8 y n=9 aceptaron 17/64 (26,6%) y 18/63 (28,6%) tokens de draft en esa salida corta. Veredicto: **superior sólo en decodificación; inferior/no promovible para Computer Use** con la configuración evaluada. El fallo es de grounding del modelo; el harness parseó los tool-calls. No se justifica cambiar el parser general por una sola fixture.

La lectura de estados sintética fue correcta con control y drafts. Una descripción con n=8 tuvo variación léxica a temperatura 0, aunque conservó los estados. No se corrieron tareas de ingeniería de software ni pruebas de Charla: el drafter es específico de este target VLM y no sustituye STT/TTS. Los perfiles se marcaron `manualOnly`, `best=false`, `favorite=false`; se mantienen para benchmark sin promoverlos al default.

Artefactos: [`lfm25-vl-dspark-3090-20260926.json`](../artifacts/lfm25-vl-dspark-3090-20260926.json), [`lfm25-vl-dspark9-3090-20260926.json`](../artifacts/lfm25-vl-dspark9-3090-20260926.json), [`lfm25-vl-dspark-computer-use-contract-3090-20260926.json`](../artifacts/lfm25-vl-dspark-computer-use-contract-3090-20260926.json) y [`lfm25_vl_dspark_ui_settings_v1.png`](../assets/benchmarks/custom/lfm25_vl_dspark_ui_settings_v1.png). Procedimiento y fuentes: [auditoría LFM2.5-VL-3B-DSpark](lfm25-vl-dspark-audit-20260926.md).

## 2026-09-26 — Qwen3.8-Flash-Next W4A16-FP8PLE de albucino

El post de LocalLLM propone el checkpoint
`albucino/Qwen3.8-Flash-Next-W4A16-FP8PLE`, hot cache de 88 expertos y contexto
220k en 2× RTX 3090. La evaluación del post atribuye ~80 tok/s y más de 2k
tok/s al prefill. El mantenedor publicó el 25 de septiembre un runtime
fast-256k más reciente para los mismos pesos objetivo: hot84/MTP3, con tres
corridas de 131k a 2.693–2.757 tok/s de prefill y 94,2–104,5 tok/s de decode;
en 260.096 tokens, 2.653–2.654 tok/s y 92,6–103,1 tok/s. Son cifras externas
de servicio, no comparables con BCB ni con la calidad de SOL.

La réplica local queda **bloqueada por hardware**: la sesión actual reporta
61,7 GiB de RAM física y WSL sólo expone 30 GiB, mientras el runtime exige
128 GiB y swap NVMe. Los pesos albucino no están descargados y ambas RTX 3090
ya tenían un `llama-server` activo de otra aplicación. No se detuvo ese proceso
ni se descargó el checkpoint.

Veredicto: **candidato superior sólo en throughput publicado; no demostrado
superior como agente, modelo de Charla ni perfil local**. La campaña previa del
mismo checkpoint con el runtime anterior obtuvo 1/8 BCB directo, un fallo de
JSON y un smoke visual sintético correcto sin MTP; MTP3+visión falló en
warmup. El fast-256k actual aún requiere repetir HE0/HE20/BCB y Computer Use.
Se agregaron perfiles manuales hot84/256k, hot88/220k y visión hot80/256k,
fuera de la selección automática por el requisito de 128 GiB. Charla sólo
podría usarlo como backend de texto; no sustituye STT/TTS.

Detalle, fuentes y protocolo: [auditoría W4A16-FP8PLE de albucino](qwen38-flash-next-albucino-w4a16-audit-20260926.md).

## 2026-08-29 — Qwen3.8 adaptive KV streaming desde LocalLLM

El reporte adjunto aportó una idea útil para el stack local: un fork de
`llama.cpp` que mantiene el KV autoritativo en RAM pinned y usa una piscina CUDA
acotada para streaming/prefetch. No se confundió con el engine existente
`llama.cpp-adaptive`, que en LlamaCode es un fork de MTP/speculative decoding.

Se incorporó el engine experimental `llama.cpp-kv-streaming` y el perfil
`sys-bench-qwen38-kvstream-24gb-131k`, marcado `benchmark=true`, `extra=true` y
`manualOnly=true`. La receta es texto-only, una GPU, un slot, Flash Attention,
K=`q8_0`, V=`q4_0`, B/U=`256/256` y `--kv-stream-stage-mib 2048`. El binario se
construyó en Windows desde `sachin-detrax/llama.cpp-adaptive-kv-streaming`,
rama `feature/adaptive-kv-stream`, commit `11a01c8`.

| Prueba | Resultado | Clasificación |
|---|---|---|
| Sweep sintético 8k → 131k, 8 tokens por punto | 16/16 puntos OK; 131k: prefill 617,1 tok/s, decode 5,25 tok/s; ~19.621 MiB usados | **SUPERIOR en ejecución/capacidad de contexto largo con B256/U256** |
| NIAH/passkey con Qwen3.8 UD-Q4 | ambos runtimes sin salida exacta; el oficial además cae con B/U=256/256 | **Calidad sin validar; no promover** |
| Latencia larga | prefill 1226,2 → 617,1 tok/s; decode 36,02 → 5,25 tok/s de 8k a 131k | **INFERIOR para speed-first** |
| Streaming desactivado en el fork (`stage=0`) | cuelga al comenzar el prompt sintético de 8k; GPU queda en 0% | **CONTROL INFERIOR / NO USAR** |
| Benchmark sintético upstream en Windows | `SIGINT` falla con `Unsupported signal: 2`; se corrigió sólo en la copia externa con `terminate()` para la corrida | Mejora de robustez del harness |

La conclusión es acotada: el perfil sirve para investigar contexto largo cuando
la velocidad es secundaria, pero no reemplaza el perfil Qwen3.8 oficial ni se
promueve a BEST/TERRA/LUNA. El A/B ahora acepta `serverExe` por variante para
comparar builds distintos sin duplicar el modelo/receta, y la matriz de contexto
acepta `--startup-only` para separar capacidad de arranque de calidad del probe.

## 2026-08-21 — Consolidación de ranking y casos de uso

Se documentaron las mejoras del dashboard web y del Ranking nativo: agrupación de
HE0/HE20/BCB por perfil + huella + harness, orden numérico de fracciones,
filtros persistentes, columnas visibles y reordenables, specs, thinking, saltos
de línea, dos decimales, widths ajustables y modo normal/dev con observabilidad
de rendimiento. La guía completa está en
[`benchmark-ranking-and-use-cases.md`](benchmark-ranking-and-use-cases.md).

La recomendación actual mantiene como referencias Qwen3.8 Dynamic V3 192k/MTP2
(`abc1df7a-2af1-4957-9d12-dbe2d01988aa`), Dynamic V3 160k/MTP2
(`8797a8cf-fea9-46cb-934a-0d62f3ee8ca7`), Dynamic MTP 64k
(`37269d11-26db-4fd0-ade3-3c595f70e4cd`) y el control UD-Q4 con visión
(`sys-qwen38-27b-udq4-131k`). DFlash2, Ling híbrido, RVN, NInfer y vLLM quedan
documentados como experimentales, no listos o fallidos por infraestructura según
la evidencia de cada perfil. No se promovió ni deprecó automáticamente ningún
perfil en esta actualización documental.

## 2026-08-20 — Controles Qwen3.8 para el piso de 24 GB

El reporte de LocalLLM separa una medición reproducible de `llama-bench tg128`
de los números de chat, ngram y cola cloud. Se agregaron dos controles
texto-only al catálogo:

| Variante | Quant | Receta | Estado |
|---|---|---|---|
| `sys-bench-qwen38-q4km-24gb-tg128` | Q4_K_M | `-ngl 99`, Flash on, B512/U512, ctx 32k, KV q4_0, sin MTP/cache/mmproj | Pendiente de HE0/tg128 |
| `sys-bench-qwen38-q6k-24gb-tg128` | Q6_K | misma receta, cambiando sólo el quant | Pendiente de HE0/tg128 |

Cada familia conserva variantes de ngram y prefix-cache warm para diagnóstico,
pero no se mezclan con la tabla de velocidad cold: un prefijo cacheado o un hit
de ngram puede ser una repetición del prompt y no throughput autoregresivo. El
Q8 no se ofrece como candidato 24 GB porque el reporte indica que no entra con
`-ngl 99`; si una máquina lo intenta y hace offload/OOM, eso se registra como
infraestructura y no como una velocidad baja.

## 2026-08-20 — A/B de ciclo de artefactos

El flujo externo aporta una dimensión útil que no queda cubierta por
HumanEval/HE20/BCB: producir un artefacto autocontenido, conservarlo privado,
validarlo y separar el stash de una publicación con efectos externos. Se
agregaron dos presets inmutables y dos variantes declarativas sobre el mismo
runtime Qwen3.8 UD-Q4:

| Variante | Perfil | Cambio controlado | Resultado |
|---|---|---|---|
| `sys-bench-qwen38-udq4-artifact-local` | `agent-artifact-local` | core, sin MCP/web/browser; manifiesto + validación local | Pendiente |
| `sys-bench-qwen38-udq4-artifact-publisher` | `agent-artifact-publisher` | core + web + browser/MCP bajo demanda; approval ask | Pendiente |

La suite [`artifact_lifecycle_v1.json`](../assets/benchmarks/custom/artifact_lifecycle_v1.json)
crea un pitch deck HTML y una checklist de publicación. Exige `private by
default`, `published: false` y aprobación explícita; no autoriza una publicación
real durante el benchmark. Las filas se medirán por separado de HE0/HE20/BCB,
con archivos producidos, manifiesto, reparaciones, tiempo y cualquier intento
de red. No se promueve ninguna variante hasta que ambas pasen la validación
funcional y el perfil publisher demuestre que no publica durante la fase de
preparación.

## 2026-08-18 — Candidatas `llama-debug` de runtime

Se agregaron a la tabla viva dos copias editables del perfil
`106_MAX-Q ThinkingCap Q3_K_M MTP` para medir el efecto de `ubatch=128` sin
modificar el perfil original. Ambas usan `parallel=1`, Flash Attention, KV
`q4_0`, contexto 262k y muestreo conservador; una conserva `batch=512` y la
otra usa `batch=1024`.

| Launch ID | Configuración | HE0 | Tiempo | VRAM agregada | Estado |
|---|---|---:|---:|---:|---|
| `c3a3851d-c3a0-4dc8-8018-1c408f017a95` | batch 512 / ubatch 128 | 1/1 | 26,242 s | 24.963 MB | HE0 válido; HE20/BCB pendientes |
| `d805e63a-f4df-4b99-86b3-5472f8998d63` | batch 1024 / ubatch 128 | 1/1 | 18,760 s | 24.910 MB | HE0 válido; HE20/BCB pendientes |

La segunda fue más rápida en esta única pasada, pero la diferencia de
generación no se considera concluyente. Ninguna variante se promueve a BEST.

## 2026-08-18 — Primer A/B de HARNESS (mismo modelo, distinto HarnessSpec)

Primera corrida real de `tools/harness_ab.ps1`: mismo launch
(`116_FAST · KAT-Coder`, 2×3090), mismo benchmark (`llamacode_local_coding_smoke`,
3 ítems), 2 pasadas, y como única variable el **perfil de agente**.

| Perfil de agente | Tools (tok de schemas) | Calidad | Éxito | Tiempo | Archivos | Runs |
|---|---|---:|---:|---:|---:|---:|
| `agent-intermedio` | 10 (~1110) | 100,0 % | 50,0 % | 211,1 s | 4,0 | 2 |
| `agent-minimal` | 6 (~630) | 100,0 % | 50,0 % | **98,5 s** | 4,0 | 2 |

Delta: calidad 0,0 pp · éxito 0,0 pp · **tiempo −34,7 %**. Con esta muestra (n=2,
un benchmark corto) el harness minimal hace lo mismo en dos tercios del tiempo;
no alcanza para declararlo mejor en general, pero sí para dejar de suponer que
más tools es gratis. Informe completo en
`docs/benchmark-levels-artifacts/harness-ab-minimal-vs-intermedio.json`.

**Tres defectos que sólo aparecieron corriéndolo de verdad** (los tres corregidos):

1. `compareHarnessBenchmarks` agrupaba TODO el historial: la primera corrida
   comparó 30 corridas viejas de `agent-intermedio` contra 1 de `agent-minimal`
   y daba +36,7 pp de éxito a favor del nuevo. Ahora el barrido acota por
   `sinceEpochMs` y el informe trae `balanced`, con aviso explícito si las
   muestras son dispares.
2. Un perfil con 5/6 criterios y 0 corridas exitosas se imprimía como
   "calidad 0,0 %", que se lee como "mucho peor" cuando en realidad es
   **sin dato** (las medianas se calculan sólo sobre corridas exitosas, a
   propósito). Ahora dice `s/d` y marca el delta como no interpretable.
3. Formato `{n,+6:N1}` inválido en .NET: el script moría por `FormatException`
   justo antes de imprimir el resumen.

## 2026-08-17 — Reparación del tier DeepSeek VRAM 0–5

Se investigó la conclusión anterior que atribuía el bloqueo del tier 0–5 a la
generación/harness. La evidencia nueva obliga a corregirla: el primer fallo de
la variante 0–5 reducida ocurrió en el primer prompt con `CUDA error: an illegal
memory access` en GPU0, antes de que el agente pudiera crear
`solution_HumanEval_0.py`. Por lo tanto, no se habilitó HE20 ni BCB.

Se conservaron las variantes históricas y se probaron copias separadas:

| Variante | Cambio | HE0 | Resultado técnico |
|---|---|---:|---|
| `VRAM experts 0-5` | reparto histórico, ctx 131k | 0/1 | El agente llegó a generar, pero el watchdog terminó una reparación sin cambios; luego el agente básico omitió el archivo esperado. |
| `VRAM experts 0-5 · HE0 safe` | mismo reparto; `predict=4096`, ctx 65k, batch 2048, ubatch 512 | 0/1 | `CUDA error: an illegal memory access` en GPU0 al primer prompt; server salió con código `-1073740791`. |
| `VRAM experts 0-5 · CUDA stable` | además `flash-attn off`, `no-mmap` | 0/0 | No carga: el GGUF usa cache V cuantizada y exige Flash Attention. Al corregir Flash Attention a `on`, la carga quedó inestable y el daemon desapareció antes de finalizar HE0. |

Se hizo una repetición adicional del tier histórico 0–5 con `agent-chat`, sin
cambiar el reparto CUDA: `0/1` en `61,421 s`, `10,38 t/s`, sin archivo creado y
sin acceso ilegal a CUDA. Cambiar de agente no corrigió el resultado; el fallo
queda clasificado como salida/modelo no evaluable, no como infraestructura. Por
la compuerta HE0, no se ejecutaron HE20 ni BCB para ninguna variante 0–5/0–9.

La conclusión operativa queda así: **DeepSeek VRAM 0–1 sigue siendo la mejor
variante DeepSeek validada (HE0 1/1 y HE20 histórico 20/20)**. Mover expertos
0–5 sí aumenta la ocupación de GPU0, pero con el binario/GGUF actuales no es una
configuración validada: presenta acceso ilegal intermitente o caída durante la
carga. El problema no es sólo generación ni harness, y no corresponde presentar
0–5 como candidato a HE20 hasta obtener una combinación de backend, binario y
reparto que pase HE0 limpio. El tier 0–9 permanece descartado por OOM en GPU0
(`24663.67 MiB` solicitados sobre `24576 MiB`).
No se reescriben resultados anteriores: cada mejora agrega una entrada nueva
con fecha, configuración, evidencia y decisión.

El ID de la primera columna es el `launchId` persistente de LlamaCode. El
nombre visible puede cambiar sin perder la asociación con sus resultados.

## 2026-08-17 — Selección operativa

La tabla viva se redujo a los siete perfiles solicitados. Se marcó con `⚡` el
Qwen3.8 UD-Q4 visión como BEST de esta selección por tener el mayor BCB
registrado (5/8). Los demás perfiles no llevan el indicador BEST.

Desde esta fecha, el conjunto operativo queda restringido a perfiles con el
indicador `⚡ BEST`; los demás se conservan sólo como histórico y no se
benchmarkean nuevamente sin autorización explícita.

## 2026-08-17 — Telemetría DeepSeek: VRAM por GPU y TPS

La telemetría histórica de LlamaCode conserva `vramMb` agregado y `ramMb`, no
el desglose por GPU. Por eso no se inventa una separación GPU0/GPU1 para las
corridas anteriores; ese desglose debe capturarse durante la nueva serie de
variantes.

| Corrida | Calidad | Tiempo | TPS | RAM pico | VRAM agregada |
|---|---:|---:|---:|---:|---:|
| DeepSeek original — HE20 actual | 20/20 | 1164,244 s | 9,58 | 92.771 MB | 32.986 MB |
| DeepSeek original — HE20 histórico | 20/20 | 802,656 s | 10,35 | 91.865 MB | 32.785 MB |
| DeepSeek VRAM balance — HE20 histórico | 20/20 | 775,223 s | 10,76 | 91.779 MB | 35.705 MB |
| DeepSeek VRAM balance — repetición HE20 | 20/20 | 860,886 s | 9,02 | 91.893 MB | 35.604 MB |

Durante el BCB activo de DeepSeek, la muestra directa del sistema entre
22:19:43 y 22:20:24 registró GPU0 entre 11.086 y 11.150 MB, GPU1 estable en
21.698 MB y RAM de trabajo del servidor en 93.097 MB. El endpoint `/metrics`
reportó 7,484 TPS de generación promedio al cierre de la muestra. La RAM de
trabajo del proceso no representa toda la memoria mapeada del modelo; para
comparar contra las corridas históricas se usa el pico `ramMb` de LlamaCode.

## 2026-08-17 — DeepSeek: tiers de expertos en GPU0

Se conservaron los perfiles originales y se agregaron dos copias desde la
variante VRAM 0–1:

| Perfil | ID | HE0 | Tiempo | TPS | RAM pico | VRAM agregada | Estado |
|---|---|---:|---:|---:|---:|---:|---|
| DeepSeek original | `4f5cc556-333d-4310-955e-15042cd874d6` | 1/1 | 188,312 s | — | 92.303 MB | 32.736 MB | Válido |
| DeepSeek VRAM 0–1 | `6b3bf7bd-0889-491a-9b6d-b12128478a5f` | 1/1 | 184,200 s | — | 92.375 MB | 35.780 MB | Válido |
| DeepSeek VRAM expertos 0–5 | `f3d000b7-59da-4035-9114-f326515ba95d` | 0/1 | 351,267 s | — | 79.374 MB | 42.586 MB | Harness/watchdog; sin OOM/CUDA |
| DeepSeek VRAM expertos 0–9 | `78929286-486e-43a2-a97b-25f251d34254` | 0/0 | 9,199 s | — | — | — | OOM al cargar GPU0 |

El tier 0–5 también se repitió con `agent-basico`: terminó en 0/1 de
calidad, 161,997 s, 4,119 TPS, 77.334 MB de RAM y 42.621 MB de VRAM; el
modelo no creó `solution_HumanEval_0.py`. La primera ejecución con
`agent-maximo` quedó detenida por el watchdog tras 180 s sin cambios del
workspace, aunque el servidor llegó a decodificar cerca de 9,7 t/s.

El tier 0–9 no es viable con contexto 131k y la configuración actual:
`cudaMalloc` pidió 24.663,67 MiB en GPU0 frente a 24.576 MiB disponibles.
Conclusión: sí es posible mover más expertos a GPU0 hasta el tier 0–5, pero
0–5 todavía no es una candidata válida de calidad y 0–9 requiere reducir
contexto/batch o usar una distribución más conservadora.

## 2026-08-17 — Laguna safe y reparación del harness

- Laguna original fallaba durante la carga CUDA en GPU0, antes del harness.
- Se agregó `BALANCE - Laguna S.2.1 · CUDA safe 64k`: contexto 65k,
  batch/ubatch 256/64, `fit off`, Flash Attention activado, `tensor-split 1,1`
  y 32 expertos en CPU.
- La variante con Flash desactivado fue rechazada porque la V-cache cuantizada
  requiere Flash Attention.
- Tras corregirla, HE0 pasó 1/1 en 150,127 s sin crash CUDA.
- Laguna safe todavía requiere HE20 y BCB.

## 2026-08-17 — Reparaciones DeepSeek y bucles del agente

- `code_tests` ahora conserva el traceback completo y el agente recibe los
  checks locales exactos.
- La reparación BCB exige editar un archivo fallido como primera acción.
- El watchdog cancela después de 180 s sin cambios reales.
- `agent-avanzado` fue el mejor agente probado: 3/8 → 4/8.
- `agent-maximo` obtuvo 1/8 → 1/8.
- Esto corrige la infraestructura de reparación, pero no convierte por sí solo
  un fallo funcional del código generado en un éxito.

## 2026-08-17 — HE20 actual de DeepSeek

- Se inició HE20 con la configuración vigente, `agent-avanzado`, harness LC-H1
  y timeout de 3600 s.
- Resultado final: 20/20, 1164,244 s, `avgTps=9,577`, sin reparaciones,
  `failureKind=none` y sin crash CUDA ni cierre del daemon.
- BCB fue habilitado después de validar la huella HE20 actual y quedó en curso
  con `agent-avanzado` y timeout de 5400 s.

## Diagnósticos BCB conocidos

- DeepSeek 765: rutas almacenadas como claves del diccionario.
- DeepSeek 771: contrato exacto de `os.listdir()` y nombres CSV.
- DeepSeek 1019: comentario mediante `img.info.get("comment")`.
- DeepSeek 583: el test exige claves RSA de 512 bits.
- DeepSeek 139: histogramas separados y ejes independientes.
- DeepSeek 360: cierre correcto de Excel y desviación estándar poblacional.
- Laguna 928: bigramas consecutivos ordenados, no combinaciones con reemplazo.

## Regla de interpretación

`server-load`, `server-crash`, `cuda illegal access`, `Connection closed` y
`failureKind=infrastructure` se investigan como infraestructura. Un
`AssertionError`, `KeyError`, `PermissionError` o contrato de archivo con el
servidor estable se clasifica como fallo funcional del código generado o del
agente/harness.

## 2026-08-18 — BCB DeepSeek, Laguna y tiers 0–2/0–3

Se ejecutaron las acciones pendientes respetando la compuerta HE0:

- **DeepSeek original** (`4f5cc556-333d-4310-955e-15042cd874d6`): se lanzó BCB
  con `agent-avanzado` y timeout de 3600 s. La pasada alcanzó la etapa de
  reparación de los fallos 765/771/1019/583/139/360 y generó temporales de
  trabajo, pero quedó estancada en la reparación 1/2. Se canceló después de
  más de 180 s sin cierre de etapa para no dejar el daemon consumiendo
  recursos. No hay resultado final persistido; se conserva como mejor resultado
  evaluable el **4/8 en 1396,871 s** de la corrida anterior.
- **DeepSeek VRAM 0–1** (`6b3bf7bd-0889-491a-9b6d-b12128478a5f`): repetición
  BCB con `agent-basico`, **2/8 en 928,677 s**. No hubo CUDA ilegal ni crash;
  los seis fallos restantes son funcionales/contractuales del código generado
  o del agente: 765, 771, 1019, 583, 139 y 360.
- **Laguna safe CUDA 65k** (`807c23f8-442c-4303-b96a-e1d0481eaf69`): al
  verificar HE0 sobre el ID real volvió a fallar durante la carga con
  `CUDA error: an illegal memory access` en GPU0, 0/0 en 30,432 s. Por la
  compuerta no se ejecutaron HE20 ni BCB.
- **Laguna CPU-safe 32k** (`318368e6-3fb7-4ef8-a76a-23030c544c49`): el backend
  cargó y no produjo CUDA/OOM, pero HE0 fue 0/1 con `agent-basico` (68,149 s)
  y nuevamente 0/1 con `agent-chat` (74,605 s). En ambos casos faltó
  `solution_HumanEval_0.py`. No se habilitaron HE20 ni BCB porque el fallo es
  anterior a la validación de calidad.
- **DeepSeek VRAM expertos 0–2** (`392ea030-059e-4f69-86c6-81d3fa31acbc`):
  HE0 0/1 en 21,105 s con `agent-basico`; cargó sin CUDA/OOM, pero no creó el
  archivo esperado. No se ejecutaron HE20/BCB.
- **DeepSeek VRAM expertos 0–3** (`6d4b528f-f26d-4500-99cf-c25a36dd6f54`):
  HE0 0/1 en 32,450 s con `agent-chat`; cargó sin CUDA/OOM, pero no creó el
  archivo esperado. No se ejecutaron HE20/BCB.

La conclusión es que 0–2/0–3 no mejoran por ahora a VRAM 0–1: el reparto es
estable a nivel CUDA, pero no supera el smoketest del harness. Laguna tiene dos
problemas distintos: el reparto 65k conserva el acceso ilegal en GPU0 y el
reparto CPU-safe evita el crash pero no logra una salida evaluable con los dos
agentes probados. Por tanto quedan pendientes una combinación de backend/binario
o un agente/harness que produzca el archivo HE0; no corresponde saltar a HE20 ni
BCB.

## 2026-08-18 — Laguna reparada usando las dos RTX 3090

La variante CPU-only se conservó sólo como diagnóstico; no es la solución de
producción porque no utiliza las dos GPU. La variante operativa reparada es:

| Perfil | ID | Configuración | HE0 | HE20 | BCB | Tiempo HE0 | Tiempo HE20 | Tiempo BCB | TPS HE0 | TPS HE20 | TPS BCB | VRAM agregada | RAM pico |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Laguna dual GPU safe 32k | `8dd3325d-8658-45ca-9aad-ad80d301b4e9` | `tensor-split 1,1`, `gpuLayers=999`, ctx 32768, batch/ubatch 128/32, Flash Attention, `predict=512`, agent-maximo | 1/1 | 20/20 | 4/8 | 60,919 s | 392,072 s | 871,561 s | 19,77 | 54,70 | 44,33 | 40.574 MB | 41.759 MB |

La configuración dual GPU no presentó `CUDA illegal memory access`, OOM ni cierre
del daemon. En BCB pasó 928, 765, 906 y 139; falló 771, 1019, 583 y 360 por
contratos funcionales del código generado: archivos CSV, comentario/encoding,
RSA de 512 bits y formato/desviación de Excel. El fallo BCB es de calidad del
modelo/agente, no de infraestructura.

La variante CPU-only `155_BALANCE - Laguna S.2.1 · CPU-only HE/BCB · predict
512` pasó HE0 1/1 en 224,681 s, pero queda descartada como solución de
producción.

## 2026-08-18 — Investigación adicional de DeepSeek 0–2/0–3

Se probaron copias dual-GPU para evitar el crash de las variantes originales:

| Variante | Resultado HE0 | Causa |
|---|---:|---|
| Dual GPU 65k, `tensor-split 1,1` | 0/0 | OOM en GPU1: reserva de 24.641 MiB |
| Dual GPU 32k, `tensor-split 1,1` | 0/0 | OOM en GPU1: reserva de 24.148 MiB |
| Dual GPU 32k, `tensor-split 1.1,0.9` | 0/0 | OOM en GPU1; el tensor sigue superando la capacidad disponible |
| Dual GPU, `gpuLayers=20` | 0/0 | Crash del backend: `ggml-cpu.c:2691 op not implemented` al usar overrides CPU |

Por eso 0–2 y 0–3 continúan bloqueados: no es un fallo del harness ni de la
calidad del modelo, sino una incompatibilidad entre este GGUF/backend y los
repartos que intentan mantener esos expertos en GPU0. No se ejecutaron HE20 ni
BCB. La variante DeepSeek VRAM 0–1 continúa siendo la única de esa familia
validada con HE0/HE20.

# 2026-08-18 — VRAM total obligatoria por perfil

La tabla operativa ahora incluye `VRAM total`. El valor es `vramMb`, el pico
agregado de memoria usada en GPU0 + GPU1 durante la corrida reportada; no es
VRAM libre ni capacidad instalada. Las nuevas corridas también persisten
`vramGpu0Mb` y `vramGpu1Mb`, además de `ramMb`; las corridas anteriores que
sólo guardaron la suma no se desglosan retrospectivamente.
Las corridas históricas sin dato no se completan por inferencia: quedan como
`No medido` y deben repetirse si la comparación de memoria es necesaria.

## 2026-08-18 — Experimentos Qwen3.6: checkpoints, MTP y texto-only en Debug

Los cuatro perfiles experimentales quedan incorporados al conjunto `⚡ BEST`
de la tabla operativa para solicitar una corrida E2E reproducible (HE0 → HE20
→ BCB). Esto sólo habilita su medición: no modifica los perfiles existentes ni
los promueve como ganadores.

Se agregaron cuatro copias opt-in de MAX-Q, sin modificar `sys-maxq` ni el
launch histórico `a03e65f5-2f2c-4d45-b67b-4b1270fa2a6c`. Todas se probaron desde
`build/Debug/LlamaCode.exe`, con llama.cpp b10331, `short`, `agent-maximo`, una
pasada y la misma suite de 7 prompts. Las copias usan `--cache-ram 32768`,
`--ctx-checkpoints 8`, `--checkpoint-min-step 4096`, `--kv-unified` y
`--cache-idle-slots`.

| Perfil | Resultado | Tiempo Corta | VRAM | RAM | Observación |
|---|---:|---:|---:|---:|---|
| Control MAX-Q MTP4 | 5/5 | 86,262 s | 23.849 MB | 26.408 MB | Corrida de control repetida |
| Cache híbrido MTP2 | 5/5 | 147,013 s | 23.576 MB | 25.065 MB | Estable, pero más lento |
| Cache híbrido MTP4 | 5/5 | 111,520 s | 23.867 MB | 25.371 MB | Estable, sin superar al control repetido |
| Cache híbrido MTP6/p-min 0.5 | 5/5 | 86,551 s | 24.159 MB | 25.672 MB | Prometedor en una pasada; requiere repetición |
| Texto-only cache híbrido MTP4 | 5/5 | 91,671 s | 22.975 MB | 24.305 MB | Menos memoria, ~6,3% más lento que el control repetido |

El primer control de la serie tuvo 4/5 en 151,220 s, por lo que no se usa
para declarar ganador frente a MTP2/MTP4/MTP6: la variabilidad del agente es
visible. En los logs de b10331, `cache-reuse` fue desactivado tanto por el
`mmproj` multimodal como por el contexto MTP texto-only; los checkpoints sí se
crearon/restauraron, pero PR #25592 no se presume integrado en b10331. Resultado:
ninguna copia se promueve todavía. MTP6 merece una repetición; texto-only queda
como candidata de menor memoria para coding, no como mejora de velocidad.

## 2026-08-27 — Baseline Qwen3.6 para evaluar carga híbrida de expertos

Con la PC libre se ejecutaron `tests.bat Debug`, `build.bat Debug NOPAUSE`,
corridas directas de `llama-cli` y un smoke test de `llama-server` usando el
Qwen3.6-35B-A3B IQ4_XS de 16,96 GB en dos RTX 3090. El detalle reproducible
queda en [`research/qwen36-expert-streaming-windows-2026-08-27.md`](research/qwen36-expert-streaming-windows-2026-08-27.md).

El A/B directo (`n=128`, prompt corto, `n-cpu-moe=24`) produjo 19,6 t/s de
decode en la primera pasada `load-mode mmap`, 30,1 t/s en su repetición y
35,7 t/s en una pasada `load-mode none`; no se considera un resultado
estadístico por el estado cambiante de las cachés. El barrido frío con `none`
fue descartado tras 337,7 s sin resumen y aproximadamente 20 GB de memoria
privada, por lo que no se agrega a la tabla competitiva.

El servidor local respondió correctamente a `/health` y a
`/v1/chat/completions`, confirmando que LlamaCode podría consumir un backend
especializado vía su interfaz existente. La prueba no implementa ni valida
streaming de expertos: `n-cpu-moe`/`load-mode none` son controles de llama.cpp,
no un caché `pread` con solapamiento de lecturas. No se modificó código de
producción ni se promovió ningún perfil.
# 2026-08-18 — Variantes ngram combinadas con MTP

Se agregaron copias declarativas de los perfiles operativos para medir la
combinación recomendada por llama.cpp: `draft-mtp,ngram-mod`. Las variantes
usan `n-match=24`, `n-min=16` y `n-max=64`, conservando el MTP y el sampling del
perfil base. KAT y Laguna se dejaron como `ngram-mod` solo porque sus perfiles
base no incluyen un drafter MTP. Los perfiles originales no fueron alterados.

## 2026-08-27 — Repetición A/B de Qwen3.6 para carga híbrida

Con la máquina libre se repitió un smoke de inferencia local sobre Qwen3.6-
35B-A3B IQ4_XS, dos RTX 3090, `n-cpu-moe=24`, contexto 4096, `n=96` y
sampling conservador. Ambos modos terminaron correctamente en `DONE`:

| Carga | Tiempo total | Prefill | Decode |
|---|---:|---:|---:|
| `load-mode mmap` | 58,31 s | 5,0 t/s | 11,4 t/s |
| `load-mode none` | 11,24 s | 77,8 t/s | 28,5 t/s |

La diferencia corresponde a esta pasada en frío y no es una medición
estadística ni una promoción de perfil. También se validó temporalmente el
servidor OpenAI-compatible (`/health` y `/v1/chat/completions`) con respuesta
válida, y se cerró el proceso propio dejando libre el puerto 18080. La corrida
completa de perfiles no se lanzó: sigue requiriendo una campaña controlada y no
se mezcla con el ranking HE0/HE20/BCB.

## 2026-08-27 — HumanEval 20 real y preparación de campaña Release

Se ejecutó una corrida auxiliar con el modelo local real, `HumanEval (20
ítems)`, tres pasadas por cada uno de dos perfiles. El artefacto completo y el
`comparison.json` están en
`%LOCALAPPDATA%\LlamaCode\LlamaCode\benchmark-runs\HumanEval_20_tems__20260827_222122`.

| Perfil | Pasadas | Resultado | Tiempo total mediano | TPS mediano | Observación |
|---|---:|---:|---:|---:|---|
| `174_KAT Q4 K_M · sampling A/B 0.30/0.90` | 3/3 | 20/20 en todas | 277,601 s | 84,18 | estable en esta muestra |
| `FAST - KAT2-Coder-7-8-26` | 2/3 | 19/20, 20/20, 20/20 | 214,785 s | 106,30 | primer resultado falló por calidad |

El agregado fue 5/6 corridas aceptadas, sin fallo de transporte ni de
infraestructura. La comparación estadística es auxiliar y no promueve ni
reemplaza los resultados históricos de HE0/HE20/BCB.

El binario Release se compiló con CMake y se desplegó con `windeployqt
--release`; el smoke Release con reinicio y scheduler pasó. No se ejecutó
`build.bat` porque su `taskkill /F /IM LlamaCode.exe` habría terminado un
daemon Debug ajeno que seguía abierto en 8877.

También se inició la campaña oficial post-corrección con Release en 8765. La
campaña detectó 86 perfiles benchmark listos y respeta HE0 → HE20 → BCB; al
momento del registro estaba en el primer perfil, BCB, prompt 1/8. Esta entrada
queda deliberadamente abierta hasta que el runner produzca estados finales o
agote su política de timeout/reintentos.

## 2026-08-28 — Reanudación de campaña oficial

Con la PC libre y sin procesos ajenos activos, se levantó el daemon Release en
`127.0.0.1:8765` y se relanzó `tools/run-benchmark-post-correction.ps1`. La
cobertura previa permitió omitir los perfiles ya completos: en el primer
avance se reconocieron completos los perfiles 1 y 3–6, el perfil 2 quedó
incompleto por HE0 bloqueado y el perfil 7 inició BCB con modelo real.

La campaña seguía abierta en ese corte; estos datos eran seguimiento operativo
y no constituían resultados finales ni una promoción de perfil. El cierre
posterior queda auditado en la entrada siguiente.

## 2026-08-28 — Auditoría del cierre parcial de 86 perfiles

La revisión cruzada del log persistente y de los JSON locales encontró una
campaña iniciada a las 09:32 con 86 perfiles. Los perfiles 1–57 tienen cierre
explícito: 27 terminaron `complete` y 30 `incomplete`; el perfil 58 comenzó
HE20 y se canceló en el prompt 5/20 antes de registrar cierre. `complete` aquí
describe el estado de etapas del runner, no una garantía de BCB 8/8.

El conjunto `complete` fue `1`, `3–6`, `8`, `11–12`, `14–22`, `39–47` y `55`.
El conjunto `incomplete` fue `2`, `7`, `9–10`, `13`, `23–38`, `48–54` y
`56–57`. El corte produjo 42 JSON para 30 nombres de perfil nuevos o
reintentados; los perfiles ya cubiertos reutilizaron evidencia previa.

Los perfiles 13 y 23–38 dejaron 17 intentos HE0 `0/0` con
`failureStage=server-load` (DeepSeek V4-7-8-26 y variantes ULTRA-Q). Se
clasifican como infraestructura, no como calidad cero. El perfil 10
(`VRAM balance`) dejó un BCB 5/8 en un intento, pero el cierre global fue
`infra-timeout` tras tres intentos, por lo que no se promueve.

También faltaba registrar la evidencia completa de tres perfiles: KAT APEX MTP3
obtuvo HE0 1/1 en 46,149 s, HE20 18/20 en 429,338 s y BCB 5/8 en 463,354 s;
KAT APEX sin MTP obtuvo 1/1 en 43,946 s, 19/20 en 702,375 s y 1/8 en
342,839 s; y antirez stress 64k KV q8 obtuvo 1/1 en 156,513 s, 19/20 en
1150,040 s y 3/8 en 2049,730 s. Son mediciones válidas pero parciales y no
alteran las promociones SOL/TERRA/LUNA/METEOR.

La evidencia está bajo
`%LOCALAPPDATA%\LlamaCode\LlamaCode\benchmark-runs`; el log fuente es
`%LOCALAPPDATA%\LlamaCode\LlamaCode\benchmark-campaign-post-correction.log`.

## 2026-08-28 — Retiro de A/B antirez lentos

La comparación durante la campaña oficial mostró que el control
`[bench antirez] 32k · reasoning off · KV q4_0` completó HE0 1/1 en `217,863 s`,
pero HE20 expiró en `1801,3 s` sin score evaluable. Su variante
`reasoning low` pasó HE0 1/1 en `270,169 s`, pero tras unos 14
minutos de HE20 sólo había alcanzado el prompt 5/20. Frente a DeepSeek Fusion,
que completó HE20 en `1216,85–1300,74 s` con 20/20, ambas variantes quedaron
fuera del objetivo operativo; la variante low además no produjo una medición
HE20 de calidad.

Se canceló el test low antes de BCB y se detuvo la campaña serial en forma
controlada. Ambos IDs quedaron con `benchmark=false` y nombre de retirado en
`assets/system_profiles.json`; se conservan sus resultados y metadata locales
para auditoría. La campaña queda cerrada como retiro temprano en el perfil
58/86, no como cobertura completa de la matriz.

## 2026-08-30 — Campaña DeepSeek: matriz local y decisión de promoción

Se hizo una campaña manual con todos los artefactos DeepSeek disponibles en la
PC, sin descargar modelos nuevos: UD-IQ3_S en cuatro shards, la rama LID CUDA y
el GGUF híbrido antirez Q2/Q4. El supuesto UD-IQ2_M no tiene sus tres shards
locales y queda explícitamente sin medir. El hardware fue Ryzen 7 7700, 128 GiB
nominales de RAM configurada a DDR5-4000 y 2× RTX 3090 de 24 GiB, sin NVLink;
las dos placas se observaron en PCIe Gen4 x8.

La matriz nativa usó `llama-server` y `/completion`, build oficial b10331
(`7ba604f1c`) salvo el control b10228, `parallel=1`, sampling conservador,
`--ctx-size` de 131k o 64k, y una petición caliente de 256 tokens. El prompt
real tenía 57 tokens, por lo que estas cifras son diagnóstico de colocación y
decode con contexto corto; no se mezclan con TPS E2E de HE20/BCB ni se presentan
como decode con 128k ya poblados. El detalle reproducible quedó en
`artifacts/deepseek-campaign-20260830/README.md`.

| Familia / configuración | Build | Contexto nominal | Resultado nativo | Resultado de la prueba |
|---|---|---:|---:|---|
| UD-IQ3_S, expertos 29–36 CUDA1, resto CPU, `tensor-split 1,0`, KV q4 | b10331 | 131k | 5,764 tok/s | Cargó y completó 256 tokens |
| UD-IQ3_S, expertos 25–36 CUDA1, resto CPU, `tensor-split 1,0`, KV q4 | b10331 | 131k | **6,171 tok/s** | Mejor colocación observada; +7,1% vs baseline |
| UD-IQ3_S, expertos 21–36 CUDA1, resto CPU, `tensor-split 1,0`, KV q4 | b10331 | 131k | 3,604 tok/s | Más residencia empeora; −41,6% |
| UD-IQ3_S, `tensor-split 1,1`, KV q4 | b10331 | 131k | 5,381 tok/s | Generación funcional; −6,6% vs `1,0` |
| UD-IQ3_S, `tensor-split 1,0`, KV q8 | b10331 | 131k | 6,238 tok/s | Arranque OK; diferencia no concluyente con una pasada |
| UD-IQ3_S, una RTX 3090, `n-gpu-layers 44`, `n-cpu-moe 39`, KV q4 | b10331 | 131k | 6,071 tok/s | La segunda GPU no acelera automáticamente |
| UD-IQ3_S, baseline equivalente | b10228 | 131k | 2,617 tok/s | Arranque OK, pero −54,6% vs b10331 actual |
| antirez Q2/Q4, expertos 37–42 CUDA1, resto CPU, KV q4 | b10331 | 131k | **8,280 tok/s** | Más rápido en este smoke nativo |
| antirez Q2/Q4, misma colocación, KV q8 | b10331 | 64k | 9,066 tok/s | Arranque OK; no reemplaza BCB histórico |

También se probaron controles negativos. `load-mode none` no logró reservar el
buffer CUDA host de `109.117.186.048` bytes; `llama-bench` falló con un error
CUDA genérico durante carga aunque `llama-server` sí pudo cargar el mismo IQ3_S.
Se conservan ambos como fallos de infraestructura/runtime, no como fallos de
calidad del modelo.

### LID y contexto largo

Se auditó el recibo reciente
`D:\Models\llamacpp\deepseek-lid-context-matrix-ultraq-ot-50.json`. Con el
runtime LID CUDA y KV f16, la recuperación exacta pasó a 131k y 262k, con 4,733 y
4,877 tok/s respectivamente. 524k terminó con conexión rechazada y exit
`3221226505`; 1M no llegó a `/health`. La variante 1M con KV q4 terminó en
timeout. Por política, LID queda confirmado hasta 262k; 524k/1M no se
promueven.

### Comparación contra DeepSeek histórico

La evidencia E2E que ya tenía el repositorio sigue siendo la referencia de
calidad: `sys-ultraq-dsv4-0731-iq3s-48gb` completó BCB 8/8 a 9,645 tok/s y
`sys-48-antirez-dsv4-q2q4-0731-131k` completó BCB 8/8 a 10,548 tok/s. Los
controles DeepSeek Fusion quedaron en 2–4/8 BCB según huella. Por eso
`sys-48-dsv4-nospec` queda promovido con marca `BEST` **dentro de la familia
DeepSeek por calidad comprobada**: es el candidato IQ3_S con calidad completa y
supera a Fusion. No se lo declara ganador universal de velocidad: antirez
conserva el mejor TPS BCB histórico, aunque también es más lento en tiempo total
y no reemplaza un perfil práctico automáticamente.

La marca `BEST` es deliberadamente de familia/caso de uso; no convierte una
medición nativa con prompt corto en un nuevo score HE20/BCB. Todas las respuestas,
timings y logs de esta campaña quedan conservados bajo
`artifacts/deepseek-campaign-20260830/`.

## 2026-09-26 — Agention Precision Qwen3.8-27B AP-Q3_K_XL

Se descargaron y verificaron el AP-Q3_K_XL, su mmproj BF16 y el control
UD-Q3_K_XL de Unsloth; ByteShape ya tenía su mmproj local. El corpus público
mixedweb-v1 quedó fijado y verificado. Las corridas aisladas usaron
llama.cpp b29c606e2 / build 10964 y CUDA1; el llama-server de PeritoSoft quedó
intacto en CUDA0.

| Dimensión | Resultado local | Clasificación |
|---|---|---|
| PPL mixedweb-v1 (60 × 2048) | AP 11,0283 ± 0,11911; UD 11,0631; ByteShape IQ4_XS 11,1020 | **SUPERIOR en PPL local** frente a ambos controles de tamaño parecido |
| PPL Wiki del proyecto (40 × 512) | AP 6,0887 ± 0,14585; UD 6,1278; ByteShape 6,2170 | **SUPERIOR en PPL local** frente a ambos controles |
| pp2048 / tg128, llama-bench ×3 | AP 1131,45 / 37,16; UD 1135,74 / 37,62; ByteShape 1108,86 / 36,20 tok/s | **Paridad de velocidad** con UD y ByteShape dentro de la variación |
| Computer Use state-first + adversarial | AP y ByteShape 24/24 + 24/24; casos sensibles 8/8 + 21/21 por modelo | **Paridad** |
| Fixture visual de ajustes | Acción semántica correcta 3/3 para AP y ByteShape | **Paridad**; no ejecuta la acción real del host |
| Coding smoke | 3/3 para ambos después de corregir dos anclas españolas | **Paridad**; no ejecuta código ni equivale a HE20/BCB |
| Ingi-Charla audio | Sin encoder de audio ni prueba ASR/TTS/WER | No aplica; no cambiar perfiles de voz |
| HE0 → HE20 → BCB LC-H1 | Pendiente | Sin promoción agentiva |

PPL indica predicción del siguiente token. El análisis pareado de 60/40 bloques
favorece AP, pero sus intervalos t son descriptivos porque los fragmentos
consecutivos no son independientes. No se equipara PPL con KLD. La ficha del
autor publica KLD contra BF16 y un resultado WikiText-2 desfavorable para AP;
esta corrida no cargó la referencia BF16 y el wiki.test.raw del proyecto tiene
otro hash, por lo que no confirma ni refuta esas cifras. El corpus técnico
interno no se usa como gate.

En throughput bruto AP es inferior a Qwen3.5-9B (37,16 vs 101,36 tok/s), pero
el 9B pesa 5,28 GiB frente a 12,23 GiB y no es control de calidad equivalente.
SOL tampoco se midió con el mismo backend/runtime. El perfil AP se marca
**SUPERIOR sólo en PPL local** y **PARIDAD en los smokes agentivos**; permanece
manualOnly, benchmark y best=false hasta HE20/BCB LC-H1.

La campaña corrigió dos falsos negativos de llamacode_local_coding_smoke: las
anclas atom y validacion no correspondían a las respuestas españolas con
atómica y validación. Se actualizaron las anclas y se reevaluaron las respuestas
guardadas; el score 3/3 posterior no requirió nuevas generaciones. También se
agregó computer_use_vision_settings_v1.json para separar la propuesta visual de
la validación del host (UIA, freshness, política y receipt).

Detalle, comandos, archivos y límites: [informe de benchmark local](qwen38-agention-ap-local-benchmark-20260926.md).
La evaluación inicial del quant queda en [auditoría Agention AP](qwen38-agention-ap-quant-audit-20260926.md).

## 2026-09-26 — Mica v0.1 4B como selector de decisiones

Se registraron dos perfiles de evaluación: `decision-mica-v0.1-4b-q5-systemone`
y `decision-qwen3.5-4b-q4-systemone-control`. El primero fija el checkpoint
Mica Q5_K_M y su contrato TypeSafe `/v1/systemone`; el segundo define un
control Qwen3.5-4B pendiente para un A/B con el mismo readout y protocolo. Son
perfiles de benchmark, no entradas de lanzamiento: Mica no usa la API
OpenAI-compatible que espera el perfil generativo de LlamaCode.

En el Tetris publicado por el autor, con tres semillas, Mica logró 223 líneas
en el scaffold fácil y 25 en el base, frente a 17/4 de Laya y 55/18 de Kev.
La proporción de mejor jugada fue 75%/47% para Mica, 27%/13% para Laya y
49%/30% para Kev. En el scaffold fácil, Mica llegó al final en dos semillas;
los tres runs de Laya y Kev terminaron en top-out. **SUPERIOR** a Laya y Kev
en calidad dentro de este benchmark de elección de Tetris; **INFERIOR a Laya
en latencia** (136–140 ms vs. 37 ms p50). El scaffold base termina en top-out
para los tres jueces, por lo que el resultado no demuestra dominio general.

La validación local reprodujo el motor contra 18 trazas publicadas
(1.500/1.500 movimientos) y comprobó las 231 respuestas del artefacto público.
Después se ejecutó la batería Tetris local completa con el servidor oficial:
Q5_K_M, calibración `1.124473`, `llama.cpp` b11010 CUDA 12.4, contexto 8.192,
8 secuencias, Flash Attention auto y ubatch 512. Mica coincidió exactamente
con el resultado publicado y sus seis trazas coinciden en estado, opciones y
decisión en **797/797 movimientos**. Es una reproducción local, no una
comparación local contra Laya o Kev.

Una corrida exploratoria previa con contexto 2.048/una secuencia y Flash
Attention apagado dio 181 líneas fácil y 21 base; se excluyó por no respetar la
configuración de referencia.

En la misma batería, el baseline `greedy` logró 285 líneas y sobrevivió 250
piezas en cada scaffold; Mica logró 223 líneas en fácil y 25 en base, con
top-out en 1/3 y 3/3 semillas. `random` consiguió 13 y 2 líneas. Así, Mica
queda por encima de random y de Laya/Kev en la tabla publicada, pero **por
debajo del greedy del propio harness**. El p50 local de Mica fue 149 ms fácil
y 153 ms base.

La primera carga CUDA había dado OOM mientras otras corridas usaban la segunda
RTX 3090; no se interrumpieron esos procesos. El reintento posterior funcionó
cuando la GPU quedó disponible. El smoke CPU contestó una decisión sintética,
pero no se usa como score. La comparación contra Qwen3.5-4B sigue pendiente.

No es una mejora demostrada para generación de código, razonamiento largo,
Ingi-Charla (ASR/TTS/diálogo), ni computer-use con grounding visual: el modelo
recibe texto y opciones enumeradas. Puede evaluarse a futuro como selector
advisory después de UIA/OCR, con las protecciones del host como autoridad.
Protocolo, límites y hashes: [auditoría Mica](mica-decision-profile-audit-20260926.md);
resultados estructurados: [artefacto JSON](../artifacts/mica-decision-profile-20260926.json).

## 2026-09-26 — NInfer Huihui Qwen3.8 en 2× RTX 3090

El post de Reddit informa ~175 tok/s y 262K en RTX 5090. El único prefill a
contexto alto que aporta es 1.675 tok/s a 247.802 tokens, medido con
groupwise-int/KV int8; su cifra de 2.500–3.000 tok/s a 150K es estimada. La
variante NVFP4 del post es Blackwell/sm_120, por lo que esta evaluación local
se preparó con el mismo checkpoint Huihui convertido a groupwise-int para el
fork NInfer-3090 compatible con Ampere/sm_86.

Se agregaron tres perfiles históricos: texto MTP3/32K, visión MTP3/32K y
control sin MTP/32K. El archivo de pesos (18.210.531.328 bytes), el SHA-256 del
modelo y el checksum de NInfer v0.6.1 se verificaron. Un primer arranque con
GPU 1 en uso falló por `cudaMalloc` OOM antes de health; no se detuvieron el
proceso local de Mica en GPU 1 ni el `llama-server` ajeno en GPU 0.

Al repetir con ambas GPU libres, los pesos y KV cargaron en tres configuraciones
(MTP3 32K, launcher C1 MTP3 64K y sin MTP 32K), pero el warm-up falló en todas
con `cudaErrorInvalidValue` desde `gqa_attention_prefill.cu:64`. La variante de
visión cargó pesos/proyector y KV, pero tuvo el mismo error antes de aceptar
una imagen. Las cuatro repeticiones se hicieron antes de cualquier request; por
eso son un **fallo de compatibilidad operativa del artefacto/runtime SM86**, no
un score de calidad.

| Dimensión | Resultado |
|---|---|
| Arranque del candidato MTP3 32K | OOM inicial bajo contención; después pesos/KV cargaron y warm-up falló en el kernel CUDA. |
| Launcher C1 de texto 64K | Pesos/KV cargaron; mismo error de warm-up con MTP3 y prefill 1024. |
| Control sin MTP 32K | Pesos/KV cargaron; mismo error. La incompatibilidad no se limita a MTP. |
| Variante visión MTP3 32K | Pesos/proyector/KV cargaron; mismo error antes de imagen. |
| HE0 → HE20 → BCB/8 LC-H1 | No ejecutado; servidor nunca alcanzó health. |
| Decode/prefill, aceptación MTP | No medido; no hubo generación. |
| Computer Use con imagen y schema `desktop_*` | No evaluado; el profile de visión no llegó a recibir imagen ni emitió tool-call. |
| Ingi Charla | No ejecutado. El post no reporta STT/TTS ni latencia acústica. |

La referencia histórica de NInfer Qwen3.8 normal es BCB 3/8 y ~73–75 tok/s a
8K; SOL conserva BCB 8/8. Frente a ese perfil que sí atendió requests, Huihui
resulta **INFERIOR en compatibilidad operativa en el runtime SM86 probado**.
No hay veredicto de calidad ni velocidad para Huihui. Ninguna cifra del post
justifica cambiar defaults, harness, Computer Use o ruta de voz. No se incorpora
la estrategia del post de redactar consultas para evadir guardrails de un
proveedor cloud. La evidencia queda como registro histórico, sin promoción. A pedido del usuario, el 2026-09-26 se eliminó el archivo local de pesos de 18.210.531.328 bytes y se retiraron las tres entradas Huihui del catálogo; el ZIP del runtime se conservó.

Artefacto y configuración exacta:
[`ninfer-huihui-qwen38-3090-20260926.json`](../artifacts/ninfer-huihui-qwen38-3090-20260926.json).
Detalle y fuentes: [auditoría Huihui/NInfer](ninfer-huihui-qwen38-3090-audit-20260926.md).
