# Hilo LocalLLaMA "Just bought a second 3090" — auditoría y A/B local · 2026-09-27

## Veredicto

| Idea del hilo | Resultado local | Clasificación |
|---|---|---|
| `-sm tensor` en llama.cpp para modelos densos | Con b10964, Qwen3.8-27B ByteShape IQ4_XS, MTP3 y visión: **+43% TG en código, +31% en narrativa, +41% de decode tras 26K de prompt y +25% de prefill a 26K** frente a `layer`. Calidad en paridad. | **SUPERIOR** → perfil `sys-bench-qwen38-byteshape-tensor-q8-mtp3-131k` |
| "Dejá Q4, usá Q6/Q8" | UD-Q6_K_XL: más lento (65 vs 84 TG en código con split layer), mismo BCB8 directo (1/8, mismo ítem) y no entra con split tensor ni con visión a 65K en esta PC | **INFERIOR** → perfil `sys-bench-qwen38-27b-q6kxl-layer-mtp3-32k` (historial, `manualOnly`) |
| vLLM TP2 + Qwen3.8-27B-FP8 + DFlash2 W4A16 (config de Diegam) | No se repitió: Windows sin P2P ni vLLM nativo. DFlash2 ya se probó en SOL/Linux y crasheó con `device-side assert` al primer prefill de 512 ([`vllm-qwen38-p2p-sol-20260908.md`](vllm-qwen38-p2p-sol-20260908.md)). La única diferencia es el plugin FA2 FP8-KV para SM86, que queda como hipótesis Linux pendiente. | Pendiente en Linux; sin cambios |
| Flash-Next con el repo de DominikBucko (50-80 tok/s) | Ya auditado ayer: pide 128 GiB de RAM; esta PC tiene 61,7 GiB ([`qwen38-flash-next-albucino-w4a16-audit-20260926.md`](qwen38-flash-next-albucino-w4a16-audit-20260926.md)) | Sin cambios |
| Subagente dedicado en la 2.ª GPU / dos sesiones concurrentes | `SubAgentRunner` siempre usa el `serverBaseUrl` del agente principal. Choca con `-sm tensor`, que ocupa las dos placas. | Idea de harness abierta (tarea aparte) |
| mmproj en CPU para ahorrar VRAM | Ya existe (`--no-mmproj-offload` en perfiles) | Ya cubierto |
| Router litellm | Ya cubierto por el LLM Gateway | Ya cubierto |

## Entorno

- Windows 11, 2× RTX 3090 (PCIe x8/x8, **sin P2P en WDDM**), 61,7 GiB de RAM
  y **sin pagefile** (límite de commit = 61,7 GiB).
- Binario oficial `b10964` (`D:\Models\llamacpp\bench-runtime\b10964`). Control
  de `llama-bench` también con `b10182`.
- Modelo: `byteshape/Qwen3.8-27B-GGUF` `Qwen3.8-27B-IQ4_XS-3.84bpw.gguf` + `mmproj-bf16.gguf`,
  MTP embebido (`--spec-type draft-mtp --spec-draft-n-max 3`), template
  `qwen38-tools-fixed.jinja`, `--reasoning off`, B512/U128.
- Modelo Q6: `unsloth/Qwen3.8-27B-GGUF` `Qwen3.8-27B-UD-Q6_K_XL.gguf` (25,3 GB; trae MTP embebido, `nextn_predict_layers=1`).

## Hallazgo operativo: commit de Windows

WDDM reserva commit del sistema por cada asignación de VRAM. Sin pagefile, el
techo real de las dos placas lo pone el commit libre, no los 48 GB de VRAM.
Síntomas medidos:

- `GGML_ASSERT(ctx->mem_buffer != NULL)` o `cudaMalloc failed: out of memory`
  con `--list-devices` informando 23 GB libres por placa.
- El servidor muere **sin mensaje** en el primer request que no reutiliza la
  caché después de un prompt largo: restaurar la caché de prompt en RAM
  (`--cache-ram`, default 8 GB) agota el commit. `--cache-ram 1024` lo evita.
- El perfil ShapeLearn `layer` a 262K también cae por esto en esta PC.

Otro llama-server (PeritoSoft, 7,9 GB en GPU1) también reducía el margen; se
detuvo para medir. Un pagefile o Linux subirían el techo de contexto; no se
cambió la configuración del sistema.

## A/B de servidor (MTP3 + visión, mismo GGUF)

`server_ab/srvbench.py`: código (512 tokens), narrativa (512), tool call,
visión (OCR de "GUARDAR 4821"), needle a 26.493 tokens, decode tras el prompt
largo y un request corto posterior para comprobar estabilidad. Greedy.

| Configuración | TG código | TG narrativa | PP @26K | TG tras 26K | Tools / visión / needle | VRAM GPU0+GPU1 |
|---|---:|---:|---:|---:|---|---:|
| layer · KV q8 · 65K (control) | 83,7 | 60,7 | 858 | 46,8 | OK / OK / OK | 8,9 + 10,3 GB |
| layer · KV f16 · 65K | 84,9 | 56,4 | 873 | 52,4 | OK / OK / OK | 9,6 + 11,0 GB |
| tensor · KV f16 · 65K | 104,2 | 70,1 | 969 | 63,7 | OK / OK / OK | 10,5 + 10,2 GB |
| tensor · KV f16 · 98K | 101,4 | 68,5 | 985 | 63,7 | OK / OK / OK | 11,6 + 11,1 GB |
| **tensor · KV q8 · 65K** | **119,8** | **79,8** | **1.074** | **66,3** | OK / OK / OK | 9,8 + 9,3 GB |
| **tensor · KV q8 · 131K · `--cache-ram 1024`** | **119,8** | **79,7** | **1.070** | **66,0** | OK / OK / OK · estable | 11,3 + 10,8 GB |
| tensor · KV q8 · 131K · cache-ram default | 119,3 | 79,5 | 1.070 | 66,1 | cae en el request posterior | — |
| tensor · KV q8 · 196K · `--cache-ram 1024` | 118,9 | 79,2 | — | — | cae en el prompt largo (commit) | 12,8 + 12,3 GB |
| tensor · KV q8 · 262K | — | — | — | — | OOM al cargar (commit) | — |
| layer · KV q8 · 262K (perfil actual) | 87,6 | 59,9 | — | — | cae en el tool call (commit) | 13,1 + 15,4 GB |

Sin MTP, el patrón se mantiene: tensor f16 51,9/51,6/48,5 contra layer q8
42,7/42,5/35,9 (+22% / +21% / +35%).

Aceptación de MTP: 83% en código y 45% en narrativa con tensor, frente a 81% y
48% con layer. La ganancia no se debe a un draft más eficiente.

## llama-bench (sin MTP, 2 repeticiones)

| KV | Profundidad | layer PP2048 / TG128 | tensor PP2048 / TG128 | Δ TG | Δ PP |
|---|---:|---:|---:|---:|---:|
| q8 | 0 | 1.755 / 46,5 | 1.524 / 58,6 | **+26%** | −13% |
| q8 | 32K | 1.286 / 38,0 | 1.247 / 50,1 | **+32%** | −3% |
| f16 | 0 | 1.561 / 39,9 | 1.335 / 46,1 | +16% | −14% |
| f16 | 32K | 1.158 / 35,2 | 1.101 / 43,4 | +23% | −5% |
| f16 | 64K | 913 / 31,9 | 929 / 39,4 | +24% | +2% |

Con b10182 el resultado es igual (+6% TG a profundidad 0, +25% a 32K), así que
no depende de la build. El único costo de tensor es el prefill de prompts cortos
sin caché.

## Calidad (paridad)

| Prueba | layer q8 | tensor q8 131K | tensor f16 65K | Q6_K_XL layer 32K |
|---|---|---|---|---|
| BCB8 directo (corpus `bigcodebench-hard-ubuntu-8`, protocolo 2026-09-15) | 1/8 (870) · 34,6 s | 1/8 (870) · **27,3 s** | 1/8 (870) · 32,1 s | 1/8 (870) · 55,1 s |
| Computer Use prompt order v1 + hard | 48/48 · seguridad 29/29 | 48/48 · 29/29 | 48/48 · 29/29 | — |
| Coding smoke LlamaCode | 3/3 | 3/3 | 3/3 | — |
| Visión + tool call `desktop_control_action` | 3/3 · 0,63 s | 3/3 · **0,51 s** | 3/3 · 0,50 s | sin visión |

El grader BCB en Windows reproduce la corrida Linux del 2026-09-15: con las
salidas guardadas de CyberTiel vuelve a dar 1/8 en el mismo ítem.

BCB8 directo no es LC-H1. Los HE20/BCB agentivos quedan pendientes y por eso el
perfil superior sigue con `best=false`.

## Charla (Ingi)

Turnos de voz cortos con un system prompt de ~1,5K ya cacheado, streaming y
80 tokens de salida (`server_ab/ttft.py`, 10 turnos):

| Split | TTFT mediana | TTFT p90 | Respuesta total mediana |
|---|---:|---:|---:|
| layer q8 131K | 181 ms | 195 ms | 0,94 s |
| tensor q8 131K | 217 ms | 224 ms | **0,81 s** |

Con tensor, el TTFT sube 36 ms por la sincronización entre placas en el
prefill corto. La respuesta completa baja 14%. Para Charla es paridad
práctica: los 36 ms son chicos frente a la latencia de STT y TTS.

## Q6_K_XL: por qué quedó INFERIOR

- Con split layer, KV q8 y 32K sin mmproj: 65,1 TG en código, 45,3 en narrativa
  y 46,6 tras 12K. Es más lento que IQ4_XS con layer (83,7/60,7) y mucho más
  lento que IQ4_XS con tensor (119,8/79,7).
- En BCB8 directo empata con IQ4_XS: 1/8, en el mismo ítem, pero tarda 55 s.
  Esta muestra no confirma la mejora de calidad que se afirma en el hilo.
- Con split tensor, con o sin MTP, falla la reserva de host del contexto de
  draft MTP o cae en el prompt largo. Con mmproj a 65K tampoco entra, siempre
  por commit.
- Sólo arranca estable con `--cache-ram 1024`: el default crashea al
  restaurar la caché.

Conviene reevaluarlo con pagefile o en Linux, y con HE20/BCB LC-H1, porque
BCB8 directo es una muestra chica.

## Perfiles agregados

- `sys-bench-qwen38-byteshape-tensor-q8-mtp3-131k`: **SUPERIOR** en TG y PP
  con dos GPU, con paridad de calidad. Está en la cola de benchmark
  (`benchmark=true`) para correr LC-H1. Requiere b10964 o posterior.
- `sys-bench-qwen38-27b-q6kxl-layer-mtp3-32k`: **INFERIOR**. Es `manualOnly` y
  queda como historial.

El test que fija las invariantes es
`bundle_tensorSplitProfilesAreDualGpuAndMemoryCapped` en
`tests/test_system_profiles.cpp`. Exige 48 GB, KV q8 o f16 igual al de runtime,
`--cache-ram` ≤ 2048 y build ≥ 10964.

## Artefactos

[`artifacts/reddit-dual3090-tensor-20260927`](../artifacts/reddit-dual3090-tensor-20260927/):
JSON por configuración (`server_ab/`), salidas y resultados de BCB8 (`bcb8/`),
tablas de `llama-bench` (`llama_bench/`) y el harness de visión, Computer Use y
coding con sus JSON.

## Próximos pasos

1. Correr LC-H1 (HE0 → HE20 → BCB) del perfil tensor desde la cola de benchmark.
2. Repetir en Linux con P2P: tensor debería ganar más y permitir 262K.
3. Con pagefile activo en Windows, repetir 196K/262K con tensor y el Q6 con tensor.
4. Harness: endpoint de subagente configurable para un modelo auxiliar
   dedicado. Sólo tiene sentido con split layer o con un modelo por GPU.
