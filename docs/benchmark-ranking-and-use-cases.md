# Benchmarking: ranking, perfiles y casos de uso

Este documento consolida las mejoras de observabilidad, ranking y benchmarking
incorporadas al flujo de LlamaCode, junto con la lectura operativa de los
resultados disponibles. Es una guía de decisión, no reemplaza los JSON brutos ni
la matriz histórica.

**Corte de esta revisión:** 2026-08-21.  
**Hardware de referencia:** 2 × RTX 3090 de 24 GB, 48 GB de VRAM agregada.  
**Suites canónicas:** HumanEval/0, HumanEval/20 y BigCodeBench/8.  
**Ejecución:** un perfil por vez, HE0 → HE20 → BCB, con la misma huella efectiva
para comparar.

## Fuentes y regla de confianza

- Resultados y logs: `%LOCALAPPDATA%\LlamaCode\LlamaCode\benchmark-runs`.
- Tabla de candidatos y configuraciones: [`benchmark-profile-matrix.md`](benchmark-profile-matrix.md).
- Procedimiento: [`benchmark-manual.md`](benchmark-manual.md).
- Dashboard web: [`../tools/benchmark-dashboard.html`](../tools/benchmark-dashboard.html).
- Ranking nativo: [`../qml/pages/RankingPage.qml`](../qml/pages/RankingPage.qml).

Un resultado `0/0`, una conexión cerrada, un crash, `server-load`, timeout sin
progreso o transporte roto es infraestructura: no representa inteligencia ni
debe ordenarse como score cero. Un score parcial con grader y transporte sanos
sí es un resultado de calidad, aunque sea bajo.

No se mezclan resultados con distinto modelo, runtime, configuración efectiva,
harness o perfil de agente. Cuando el mismo perfil aparece con varios harnesses,
la tabla los conserva en filas/grupos separados.

## Mejoras de interfaz y observabilidad

### Dashboard web de corridas

El dashboard permite observar el daemon en tiempo real sin detener las corridas:

- estado del benchmark, perfil/etapa activa, progreso y última actualización;
- agrupación de HE0, HE20 y BCB en una fila por perfil + huella + harness;
- scores separados por etapa (`Score HE0`, `Score HE20`, `Score BCB`);
- tiempos separados (`Secs HE0`, `Secs HE20`, `Secs BCB`);
- `failureKind`, `timedOut`, `avgTps`, `avgTtftMs`, `elapsedSec`, `runDir`, agente,
  thinking, harness y specs;
- columnas visibles configurables, con preferencias persistentes del navegador;
- reordenamiento de columnas mediante controles de posición y redimensionado;
- filtros por columna con selección de valores y limpieza global;
- orden ascendente/descendente con claves numéricas reales;
- autodetección del puerto ControlApi local mediante `benchmark-api.json`, con
  validación de `/health` y `/methods`; `?api=...` sigue disponible como override;
- score tratado como fracción, por lo que `5/8` queda por encima de `0/0`;
- máximo de dos decimales en valores decimales;
- `HE0`, `HE20` y `BCB` separados por salto de línea dentro de una misma celda;
- ancho flexible para aprovechar toda la página, con ajuste de texto en columnas
  largas;
- columna `Thinking` y columna `SPECS`.

`SPECS` resume, cuando la configuración lo permite, visión, drafter, nivel MTP o
DFlash2, contexto, KV, modelo, runtime y huellas. Si el resultado histórico no
contiene una propiedad confiable, muestra `—`; no infiere visión sólo porque el
mmproj esté en RAM.

### Ranking nativo de la aplicación

La vista **Ranking** comparte el modelo de datos del dashboard y conserva en los
settings locales:

- columna y dirección de orden;
- filtro de modo y filtro de completitud;
- filtros por columna;
- columnas visibles y su orden;
- anchos de columna.

Incluye las columnas de calidad, tiempo, TPS, TTFT, RAM, VRAM, thinking, harness,
specs y fecha. Los headers permiten ordenar; el indicador de filtro muestra qué
columnas tienen restricciones activas. Las columnas recomendadas priorizan
perfil, HE0/HE20/BCB, tiempos, failureKind, TPS, nivel de agente, thinking,
harness y specs.

### Inicio y rendimiento de la aplicación

La aplicación inicia con splash mientras realiza el escaneo pesado y precarga
los datos necesarios para que la interfaz no espere ese trabajo al cambiar de
sección. El modo normal prioriza baja latencia visual y pocos logs. El modo
desarrollador agrega snapshot de rendimiento, memoria, carga y ruta del log
JSONL, visible desde Configuración. El modo se guarda como preferencia y puede
forzarse al iniciar para diagnóstico.

## Control confiable de corridas

La automatización diaria construye la cola a partir de la API viva y no ejecuta
IDs históricos que ya no existen. Verifica `/health`, `/methods`, suites,
perfiles, modelo, runtime, binario y huella efectiva antes de lanzar.

Cada etapa se controla con estas señales:

1. `benchmarkRunning` y `benchmarkStatus`.
2. `serverReady` y `activeLaunchId`.
3. proceso backend real (`llama-server`/`vllm`).
4. log del servidor y, si hay dudas, VRAM, CPU y utilización de GPU.

La política vigente es:

- más de 30 minutos: cancelar y registrar `failureKind=infrastructure` +
  `timedOut=true` con evidencia;
- después de 30 segundos sin `serverReady` y sin backend real: cancelar temprano
  como backend roto, sin esperar 30 minutos;
- un backend que sí genera permanece en observación aunque una tarea tarde,
  hasta que termine, muestre idle real o alcance el límite duro;
- sólo se detiene el daemon iniciado por la automatización; nunca una GUI o
  proceso ajeno.

Esto evita confundir “servidor iniciado” con “modelo cargado y trabajando”.

## Familias de perfiles incorporadas

### Qwen3.8 y variantes locales

| Familia | Variantes documentadas | Uso principal |
|---|---|---|
| UD-Q4 vision | control 131k, MTP4, MTP2/MTP3, batch, KV q8, 262k, mmproj RAM, prefix-cache, ngram, reasoning y Browser Agent | agente general con visión y buen equilibrio |
| Q4_K_M / Q5_K_M | controles 24/48 GB, MTP, KV q8, contexto largo y diagnósticos | comparar calidad, memoria y estabilidad |
| Dynamic V3 | DSH medium, 160/192k, KV q8, MTP2, MTP embebido y sin MTP | medir contexto largo y velocidad efectiva |
| INT8 W8A16 | vLLM MTP3, autoregresivo y DFlash2 | comparar runtime vLLM; depende de endpoint/binario real |
| Q6/Q8 | perfiles de 96k/196k, tensor split, cache warm y mmproj RAM | calidad alta y contexto largo; varios siguen no listos |

IDs de referencia de la familia Qwen3.8:

- control UD-Q4: `sys-qwen38-27b-udq4-131k`;
- variantes benchmark: `sys-bench-qwen38-udq4-mtp2-64k`,
  `sys-bench-qwen38-udq4-mtp3-kv8`, `sys-bench-qwen38-udq4-mtp3-b1024`,
  `sys-bench-qwen38-udq4-24gb-lookup-64k` y
  `sys-bench-qwen38-udq4-24gb-prefix-cache-64k`;
- artefactos: `sys-bench-qwen38-udq4-artifact-local` y
  `sys-bench-qwen38-udq4-artifact-publisher`;
- controles Q4/Q5: `sys-bench-qwen38-q4km-mtp4`,
  `sys-bench-qwen38-q5km-mtp3-64k-kv8`,
  `sys-qwen38-27b-q4km-24gb-32k`,
  `sys-bench-qwen38-q4km-24gb-tg128`,
  `sys-bench-qwen38-q4km-24gb-ngram-diagnostic` y
  `sys-bench-qwen38-q4km-24gb-prefix-warm`.

### Dynamic V3

Los perfiles Dynamic V3 se conservan como experimentos separados porque el
nombre puede ocultar diferencias importantes de thinking, contexto, KV, MTP y
harness:

- `8797a8cf-fea9-46cb-934a-0d62f3ee8ca7`: Qwen3.8 DSH medium, 160k, MTP2;
- `abc1df7a-2af1-4957-9d12-dbe2d01988aa`: Qwen3.8 DSH medium, 192k, KV q8,
  MTP2, mmproj en RAM;
- `ec212f51-730e-4456-a673-0aba1d1818a8`: UD-Q4, MTP embebido, 131k;
- `71098365-b598-401d-abe1-db1cad5de4f4`: UD-Q4, sin MTP, 131k;
- `37269d11-26db-4fd0-ade3-3c595f70e4cd`: MTP embebido, 64k;
- `334f06f9-74e9-42c9-bf5a-9763933746c8` y
  `03902781-b147-4f36-9c0e-975154be9ca1`: DFlash2 Q4, n7, 32k/64k;
- `2f493452-267b-4d55-9632-cf0a575d8f40`,
  `966d9a6b-50de-4def-b2d8-e5cf0c5d9aac`,
  `542de8b1-f751-4543-8155-b1e0355f81dd` y
  `a6dfde09-d3ef-45ed-99f4-52a13fe41e01`: variantes DFlash2 reparadas o
  alternativas, conservadas para diagnóstico.

### DFlash2

Se probaron dos rutas distintas y no deben confundirse:

- **DFlash2 local llama.cpp:** los perfiles Dynamic Q4 fallan al cargar con
  `wrong number of tensors; expected 81, got 58` y `FGDN_AR`; quedan bloqueados
  por infraestructura, no por calidad.
- **DFlash2 vLLM:**
  `sys-bench-qwen38-dflash2-vllm-262k` y
  `sys-bench-qwen38-dflash2-vllm-ar-262k` requieren endpoint/binario vLLM real.
  En la medición disponible no hubo backend listo; el autoregresivo además
  registró `No binary selected`.

Por lo tanto DFlash2 es una línea de investigación prometedora, pero todavía no
es una recomendación de calidad ni velocidad en este checkout.

### Ling, RVN y otros candidatos

- Ling: `sys-ling30-tiny-q6-131k`, `sys-bench-ling30-tiny-q6-64k`,
  `sys-bench-ling30-tiny-q6-thinking-131k`,
  `sys-bench-ling30-tiny-q6-kv4-131k` y
  `sys-bench-ling30-tiny-udq4-64k` están no listos por GGUF/runtime ausente.
- Híbrido: `sys-hybrid-ling30-qwen38` sí arranca, pero su BCB terminó `0/0`
  por timeout/idle; no se promociona.
- RVN: `sys-bench-16-qwen38-rvn-iq3xxs-ngram-131k`,
  `sys-bench-16-qwen38-rvn-iq3xxs-dflash2-ngram-105k` y
  `sys-bench-16-qwen38-rvn-iq3xxs-mtp-ngram-105k` requieren GGUF/build
  específicos; quedan no listos.
- NInfer: `sys-ninfer3090-qwen27`, `sys-ninfer3090-qwen35` y
  `sys-ninfer3090-qwen38` requieren artefactos y runtime NInfer ausentes.
- Laguna, DeepSeek, BigBang y KAT se conservan como controles comparativos,
  pero los fallos de `connection closed`, CUDA, carga o timeout no entran en el
  ranking de calidad.

## Auditoría por GGUF y cola operativa — 2026-08-21

La fuente de verdad de esta revisión fue la combinación de `assets/system_profiles.json`,
los GGUF presentes bajo `D:\Models` y los artefactos de
`%LOCALAPPDATA%\LlamaCode\LlamaCode\benchmark-runs`. Se contó cada variante expandida
por separado, pero la comparación se hizo por GGUF + configuración efectiva + harness.

El catálogo tenía 81 candidatos `benchmark=true`. Después de la auditoría quedan 45
en la cola operativa: se agregaron dos variantes nuevas para 48 GB y se retiraron 38
perfiles sin GGUF/runtime/binario local, con fallas de carga repetidas o con una
configuración que ya excedió el límite operativo de 30 minutos. Retirar significa
`benchmark=false` y conservar el ID, comentario e historial; no se borró ningún
modelo ni resultado.

| GGUF/familia | Perfil de referencia | Estado | Caso de uso/ranking |
|---|---|---|---|
| Qwen3.8 UD-Q4_K_XL + mmproj | `sys-qwen38-27b-udq4-131k` | Activo; 1/1, 20/20, 7/8 BCB | Mejor control general con visión y 131k |
| Qwen3.8 UD-Q4_K_XL + mmproj | `abc1df7a-2af1-4957-9d12-dbe2d01988aa` | Mejor resultado local observado: 8/8 BCB, 192k; harness distinto documentado | Calidad/contexto largo |
| Qwen3.8 Q5_K_M + mmproj | `sys-qwen38-27b-q5km-131k` | Activo; HE0 1/1, HE20 20/20, BCB 3/8 calidad | Calidad potencial superior manteniendo visión; mejor control Q5 disponible |
| Qwen3.8 Q4_K_M + mmproj | `sys-bench-qwen38-q4km-24gb-tg128` | Diagnóstico activo; el control 32k fue retirado por timeout BCB | Velocidad cold/tg128, no calidad E2E |
| Qwen3.8 Dynamic V3 UD-Q4 + MTP | `abc1df7a-2af1-4957-9d12-dbe2d01988aa` / `37269d11-26db-4fd0-ade3-3c595f70e4cd` | Activos como perfiles de usuario; ambos con BCB 8/8 en sus huellas | Mejor frontera calidad/velocidad conocida |
| Qwen3.8 UD-Q4 48GB + mmproj RAM | `sys-bench-qwen38-udq4-48gb-196k-mtp2-kv8-mmproj-ram` | HE0 1/1 (34,12 s), HE20 20/20 (370,38 s), BCB 8/8 (537,39 s), sin fallo | Mejor contexto largo con visión en el catálogo operativo |
| ThinkingCap Qwen3.6 Q4 + mmproj | `a03e65f5-2f2c-4d45-b67b-4b1270fa2a6c` | 6/8 BCB de calidad, rápido; harness separado | Coding rápido con thinking |
| Qwen3.6 Fable Fusion Q6 + mmproj | `sys-48-fablefusion-q6-mtp` | HE0 1/1 válido, visión; no hay BCB E2E comparable en la matriz | Candidato de visión/contexto, sin promoción de calidad |
| KAT-Coder Q4 | `sys-48-katcoder-262k` | Muy rápido en medición nativa, pero BCB quedó en infraestructura | Speed-first/text-only; no ranking de calidad |
| BigBang Q4 + mmproj | `sys-repair-48-bigbang-mtp-balance` | Reparación carga; calidad histórica parcial | Candidato de bajo contexto; mantener experimental |
| DeepSeek V4 / Laguna / antirez | `sys-ultraq-dsv4-0731-iq3s-48gb`, `sys-laguna-s-2-1-q2-48gb-safe` | Cargan en algunas huellas, pero sin resultado E2E comparable completo | Investigación de contexto/tamaño; no promover |
| Qwen3.8 DFlash2 local/vLLM | perfiles `334f06f9-...`, `03902781-...`, `sys-bench-qwen38-dflash2-vllm-*` | Loader/backend no disponible o incompatibilidad de tensores | Investigación; no rankear |
| Ling, RVN y NInfer | `sys-ling*`, `sys-bench-16-*`, `sys-ninfer*` | GGUF/runtime/binario ausente en este checkout | No listos; fuera de la cola |

### Mejoras creadas para 48 GB

Se agregaron al catálogo, ambas con `benchmark=true` y una sola ID por ejecución:

- `sys-bench-qwen38-udq4-48gb-196k-mtp2-kv8-mmproj-ram`: UD-Q4, visión, 196k,
  MTP2, KV q8, B512/U64 y mmproj en RAM. Cerró HE0 1/1, HE20 20/20 y BCB
  8/8, por lo que queda promovida como referencia 48GB de contexto largo.
- `sys-bench-qwen38-q5km-48gb-196k-mtp2-kv8-mmproj-ram`: Q5_K_M, visión, 196k,
  MTP2, KV q8, B512/U64 y mmproj en RAM; fue retirada después de un crash de
  CUDA durante HE0, sin score de calidad.

La razón de ambas variantes es aislar una mejora concreta para el equipo dual:
196k de contexto sin perder visión, menor profundidad MTP para liberar margen de
VRAM y KV q8 para estabilidad. No se las considera mejores hasta completar HE0,
HE20 y BCB con la misma configuración efectiva.

### Validación de variantes 48GB — 2026-08-21

La variante UD-Q4 mejorada completó las tres etapas con la misma huella efectiva:

| ID | Etapa | Resultado | Tiempo | failureKind | timedOut | runDir |
|---|---|---:|---:|---|---|---|
| `sys-bench-qwen38-udq4-48gb-196k-mtp2-kv8-mmproj-ram` | HE0 | 1/1 | 34,12 s | `none` | `false` | `HumanEval_1_tems__20260821_104636` |
| `sys-bench-qwen38-udq4-48gb-196k-mtp2-kv8-mmproj-ram` | HE20 | 20/20 | 370,38 s | `none` | `false` | `HumanEval_20_tems__20260821_104812` |
| `sys-bench-qwen38-udq4-48gb-196k-mtp2-kv8-mmproj-ram` | BCB | 8/8 | 537,39 s | `none` | `false` | `BigCodeBench-Hard_8_tems__20260821_110803` |

El primer BCB de la misma variante se estancó durante el transporte sin producir
JSON (`BigCodeBench-Hard_8_tems__20260821_105517`); se conservó como evidencia de
infraestructura y se repitió. La repetición fue válida, con `avgTps=43,71` y
`avgTtftMs=4.966,56`. El primer HE0 también tuvo un crash CUDA con la receta
heredada (batch alto/MTP duplicado), antes de la corrección de la variante; no se
usó como score.

La variante Q5 196k/MTP2/KV q8 falló durante HE0 al cargar el modelo, con acceso
ilegal de CUDA en `HumanEval_1_tems__20260821_110312`; quedó marcada como
infraestructura/no promotable y fuera de la cola. La referencia Q5 131k sigue
activa con HE0 1/1, HE20 20/20 y BCB 3/8 (`failureKind=quality`).

### IDs retirados de la cola

Se conservan en catálogo/matriz, pero no se relanzan automáticamente:

- NInfer: `sys-ninfer3090-qwen27`, `sys-ninfer3090-qwen35`, `sys-ninfer3090-qwen38`.
- KAT3 sin GGUF local: `sys-kat3-mtp-262k`.
- Qwen Q6/Q8 sin archivo local: `sys-48-qwen38-27b-q6-96k`,
  `sys-48-qwen38-27b-q8-196k`, `sys-qwen38-27b-q6k-24gb-32k` y sus variantes.
- RVN: `sys-bench-16-qwen38-rvn-iq3xxs-ngram-131k`,
  `sys-bench-16-qwen38-rvn-iq3xxs-dflash2-ngram-105k`,
  `sys-bench-16-qwen38-rvn-iq3xxs-mtp-ngram-105k`.
- DFlash2/vLLM sin endpoint: `sys-bench-qwen38-dflash2-vllm-262k`,
  `sys-bench-qwen38-dflash2-vllm-ar-262k`.
- Variante Q5 48GB que falló durante la carga: `sys-bench-qwen38-q5km-48gb-196k-mtp2-kv8-mmproj-ram`.
- Ling/híbrido sin runtime o GGUF: `sys-ling30-tiny-q6-131k`,
  `sys-bench-ling30-tiny-q6-64k`, `sys-bench-ling30-tiny-q6-thinking-131k`,
  `sys-bench-ling30-tiny-q6-kv4-131k`, `sys-bench-ling30-tiny-udq4-64k`,
  `sys-hybrid-ling30-qwen38`.
- Qwen3.8 de 24 GB con BCB de 6.936,9 s y lookup roto:
  `sys-qwen38-27b-q4km-24gb-32k`, `sys-bench-qwen38-udq4-24gb-lookup-64k`.

Los diagnósticos Q4/Q5 de ngram y prefix-cache que sí tienen un GGUF local se
mantienen activos sólo para sus casos específicos; nunca se mezclan con cold-cache
ni se promocionan por un `0/0`.

## Ranking por caso de uso

Este ranking es una recomendación documental basada sólo en resultados válidos y
en la configuración declarada. No es un leaderboard universal. Las filas con
otro harness, cache warm, suite distinta o reparación de infraestructura deben
compararse en su propio grupo.

### 1. Mejor calidad ejecutable comprobada

1. **Qwen3.8 Dynamic V3 DSH medium 192k / MTP2** — `abc1df7a-2af1-4957-9d12-dbe2d01988aa`:
   HE0 1/1, HE20 20/20, BCB 8/8; BCB 403,59 s. Es el mejor punto de partida
   para agente general de alta calidad y contexto largo.
2. **Qwen3.8 Dynamic V3 DSH medium 160k / MTP2** —
   `8797a8cf-fea9-46cb-934a-0d62f3ee8ca7`: BCB 8/8, 661,67 s. Menor contexto,
   buen control para comparar contra 192k.
3. **Qwen3.8 Dynamic MTP embebido 64k** — `37269d11-26db-4fd0-ade3-3c595f70e4cd`:
   BCB 8/8, 625,48 s. Útil cuando 64k alcanza y se prioriza una receta local
   más simple.

El control UD-Q4 visión `sys-qwen38-27b-udq4-131k` obtuvo 7/8 en BCB y sigue
siendo una referencia sólida, pero queda debajo de las tres filas anteriores en
calidad BCB medida.

### 2. Mejor equilibrio calidad/velocidad

1. `abc1df7a-2af1-4957-9d12-dbe2d01988aa` — 8/8 BCB, 403,59 s, contexto 192k.
2. `37269d11-26db-4fd0-ade3-3c595f70e4cd` — 8/8 BCB, 625,48 s, contexto 64k.
3. `sys-qwen38-27b-udq4-131k` — 7/8 BCB, 736,07 s, visión y perfil de control
   más directo.

`ThinkingCap Qwen3.6-27B MTP4` llegó a 6/8 BCB en unos 306 s, pero el score fue
de calidad y la comparación pertenece a otro harness/configuración. Es una
alternativa rápida, no un reemplazo automático del Qwen3.8 192k.

### 3. Agente con visión

Recomendación inicial: `sys-qwen38-27b-udq4-131k` o la variante Dynamic V3 que
conserve mmproj. Confirmar siempre `Visión: sí` en SPECS y no inferirlo desde
`mmproj RAM`. Las variantes texto-only, Q8 no descargado y perfiles sin mmproj
no deben aparecer en este caso de uso.

### 4. Contexto largo

- **192k:** `abc1df7a-2af1-4957-9d12-dbe2d01988aa`, validado hasta 192k y con
  8/8 BCB.
- **160k:** `8797a8cf-fea9-46cb-934a-0d62f3ee8ca7`, control de menor presión.
- **131k:** `sys-qwen38-27b-udq4-131k`, referencia estable con visión.
- **262k:** mantener como línea experimental hasta tener HE0/HE20/BCB válidos
  bajo la misma huella; no usar un timeout de BCB como evidencia de calidad.

### 5. Memoria/VRAM limitada

Para una sola RTX 3090/24 GB, priorizar UD-Q4 con contexto 64k y MTP. La variante
`sys-bench-qwen38-udq4-24gb-prefix-cache-64k` obtuvo BCB 8/8, 627,65 s, pero es
un escenario warm-cache y no debe compararse directamente contra decode cold.
`sys-bench-qwen38-udq4-24gb-lookup-64k` quedó en infraestructura y no se rankea.

### 6. Prefijos repetidos / documentación larga

Usar `sys-bench-qwen38-udq4-24gb-prefix-cache-64k` como candidato de warm-cache.
Para una conversación nueva o prompt sin prefijo, usar el control UD-Q4 o
Dynamic V3; una mejora de cache no demuestra por sí sola mayor calidad.

### 7. Artefactos y publicación segura

`sys-bench-qwen38-udq4-artifact-local` y
`sys-bench-qwen38-udq4-artifact-publisher` se comparan con la suite
`artifact_lifecycle_v1`, no con BCB. El perfil local obtuvo 6/8 antes de un
fallo de infraestructura; el publisher terminó en timeout. Ninguno se promueve
hasta validar creación, manifiesto privado y ausencia de publicación no aprobada.

## Promoción, archivo y deprecación documental

### Mantener como referencias activas

- `abc1df7a-2af1-4957-9d12-dbe2d01988aa` — calidad/contexto largo;
- `8797a8cf-fea9-46cb-934a-0d62f3ee8ca7` — control 160k;
- `37269d11-26db-4fd0-ade3-3c595f70e4cd` — control MTP local 64k;
- `sys-qwen38-27b-udq4-131k` — control con visión;
- `sys-bench-qwen38-udq4-24gb-prefix-cache-64k` — warm-cache separado.

### Mantener sólo como diagnóstico

Q4/Q5 `tg128`, ngram, prefix-warm, lookup, DFlash2, vLLM, Ling híbrido, RVN,
NInfer y las variantes de batch/tensor split quedan para investigación o
repetición. No deben ganar por aparecer con `0/0`, timeout o artefacto parcial.

### Candidatos a deprecación operativa

Los perfiles CPU-only, los perfiles que no tienen modelo/runtime/binario local y
los duplicados cuyo único resultado sea una falla de carga pueden ocultarse del
ranking operativo, pero conservarse en la matriz histórica. Deprecarlos no
significa borrar JSON, logs ni el ID: significa `benchmark=false` o exclusión
explícita de la próxima cola, con motivo y fecha. En esta revisión sí se aplicó
esa política al catálogo: 38 perfiles quedaron con `benchmark=false`, y la
variante UD-Q4 48GB validada quedó como referencia operativa.

## Cómo leer una fila

1. Verificar primero HE0 y su huella.
2. Confirmar HE20 válido antes de usar BCB para calidad.
3. Separar `score`, `failureKind`, `timedOut` y `elapsedSec`.
4. Comparar sólo dentro del mismo harness, agente, runtime, quant, contexto,
   thinking, KV y modalidad.
5. Para velocidad, preferir TPS nativo del backend; para experiencia de agente,
   mirar además TTFT, tiempo total, reparaciones y estabilidad.
6. Para contexto largo, registrar el contexto real y la capacidad de KV, no sólo
   el valor nominal del perfil.

La decisión final debe ser una frontera de Pareto: un perfil puede ganar en
calidad, otro en latencia, otro en visión y otro en warm-cache. No hay que
forzar una sola fila como ganadora universal.
