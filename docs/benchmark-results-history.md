# Historia, descubrimientos y anotaciones de benchmarking

Este archivo es el espejo histórico de [`benchmark-results.md`](benchmark-results.md).

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
