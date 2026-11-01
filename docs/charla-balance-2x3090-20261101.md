# Ingi Charla en 2× RTX 3090: STT/TTS en tiempo real + agente con PC y web

Fecha: 2026-11-01. Máquina: 2× RTX 3090 24 GB (GPU0 ASUS con cuarentena de
VRAM en el driver, también dibuja el escritorio; GPU1 PNY sana), Ryzen 9 9950X3D
16c/32t, 123 GB RAM, Ubuntu. LlamaCode build Linux, agente `agent-jarvis`,
llama-server `cuda-flashnext-2x3090` (el que elige el perfil de sistema).

## Recomendación

| Pieza | Dónde | Por qué |
|---|---|---|
| LLM: **Qwen3.8-27B UD-Q4_K_XL + mmproj BF16**, MTP3, KV q4_0/q4_0, ctx 32k, ubatch 512 | **GPU1 entera** (~18,5–20,5 GB) | El modelo más capaz que entra en una sola placa con visión. Contesta corto y bien por voz y no usa tools de más (el 9B abrió computer use para multiplicar). |
| STT: **whisper-small** (whisper.cpp con CUDA, `-ac 640`) | GPU0 (~1 GB) | 31–41 ms por frase con el mismo WER que en CPU (322 ms). |
| TTS: **piper** `es_ES-davefx-medium`, residente | CPU | 150–230 ms al primer audio; no compite por VRAM. |
| Escritorio + mmproj/contexto CUDA del server | GPU0 (~3,3 GB total con whisper) | Quedan ~20 GB libres en GPU0 para StudIA u otros auxiliares. |

Resultado medido (entrada sintética, turnos tibios): **fin de habla → primer
audio 0,74–1,08 s** con el 27B y 0,57–0,73 s con el 9B. Antes de los arreglos
de abajo, el 9B daba 1,8–2,7 s.

Se aplica como el perfil de sistema **`sys-charla-jarvis-qwen38-27b`**
("[Charla JARVIS] Qwen3.8-27B UD-Q4 · voz + PC + web · 32k"): trae el agente
JARVIS, el bloque de voz (whisper-small + piper) y los args ya ajustados para
voz, así que entrar a Charla no relanza el server por el tune.

## Problemas encontrados y corregidos (los tres pesaban más que el modelo)

1. **KV cache a medias.** El runtime emitía sólo `--cache-type-k`; V quedaba en
   f16. K cuantizado + V f16 no tiene kernel fused de flash-attention en CUDA.
   Probe directo, 9B en una 3090, prompt de 17,3k tokens:

   | KV | Prefill tok/s | Decode tok/s | Turno corto sobre el prompt |
   |---|---:|---:|---:|
   | sólo K q4_0 (lo que mandaba la app) | 381 | 29 | 300 ms |
   | K+V q4_0 | 3057 | ~97 | 115 ms |
   | K+V q8_0 | 3046 | ~113 | 116 ms |
   | f16 | 3061 | ~96 | 117 ms |

   Arreglo: `EffectiveProfileBuilder::applyRuntime` pone V igual que K cuando
   hay flash-attention; un `-ctv` explícito del perfil sigue ganando.
2. **Charla razonaba en cada turno.** `sendToAgent` re-aplica el perfil de
   agente y eso volvía a prender el thinking que Charla apaga: ~40 tokens de
   `<think>` antes de cada respuesta hablada. Arreglo en
   `applyAgentProfileCaps`: con Charla activa el thinking queda apagado.
3. **Reparto multi-GPU de Charla.** Repartía cualquier modelo entre las dos
   placas, con `--split-mode tensor` si hay P2P. Con MTP eso aborta
   llama-server (`GGML_ASSERT(ret.axis != GGML_BACKEND_SPLIT_AXIS_UNKNOWN)`,
   exit 6, tres reintentos y Charla sin LLM). Ahora, si el modelo entra en la GPU
   que no es la de voz con 1 GB de margen, va entero ahí (`--split-mode layer
   --tensor-split 0,1 --main-gpu 1`); si hay que repartir, con MTP nunca usa
   tensor. Al implementarlo apareció una oscilación (el re-plan con el server
   vivo atribuía el modelo a medias y cambiaba la GPU de voz cada pocos
   segundos); `modelByGpu` ahora deja en 0 la parte de la GPU de voz.
4. **El tune de Charla se perdía.** Era "sólo para el próximo launch" y el
   relanzamiento del reparto multi-GPU que viene después volvía a 131k/ubatch 64.
   Ahora vale para toda la sesión de Charla de ese perfil.

## STT (6 frases en español generadas con piper oficial, 3 pasadas)

| Motor | Dispositivo | Mediana | p90 | WER | Nota |
|---|---|---:|---:|---:|---|
| whisper-small, 8 hilos, `-ac 640` | CPU | 322 ms | 358 ms | 2,4% | default actual de la app en Linux (binario CPU) |
| whisper-small | GPU0 | 33 ms | 42 ms | 2,4% | **elegido** |
| whisper-small | GPU1 | 31 ms | 40 ms | 2,4% | |
| whisper-small, `-ac 1500` | GPU0 | 41 ms | 51 ms | 2,4% | |
| whisper-base | CPU | 90 ms | 102 ms | 26,2% | "3x3", "12x37": no sirve para órdenes |
| large-v3-turbo q8, `-ac 640` | GPU0 | 49 ms | 66 ms | (21%) | repite el segmento: no usar con contexto corto |
| large-v3-turbo q8, `-ac 1500` | GPU0 | 89 ms | 94 ms | ~0%* | el mejor texto (conserva "Abrí"), +55 ms y +0,9 GB |
| large-v3-turbo q8 | CPU | 1489 ms | 1560 ms | — | |
| parakeet-tdt-0.6b-v3 q4, proceso por turno | CPU | 461 ms | 509 ms | 2,4% | |

\* el WER de turbo con `-ac 1500` sale 7% sólo por escribir "3x3".
whisper-small ocupa ~1,0 GB en GPU. Su costo de CPU con CUDA es 0,05–0,1
CPU-s por turno, así que no le roba CPU a piper (el problema medido en Windows
con 12 hilos en CPU).

## LLM: probe directo (una 3090, prompt de 17,3k tokens ≈ system + tools de JARVIS)

| Modelo | ctx / ubatch | VRAM | Prefill tok/s | Decode tok/s (MTP3) | Turno corto |
|---|---|---:|---:|---:|---:|
| Qwen3.5-9B Q4_K_M + mmproj, KV q4/q4 | 32k / 512 | 7,3 GB | 3057 | 96–97 | 115 ms |
| Qwen3.8-27B UD-Q4_K_XL + mmproj, KV q4/q4 | 32k / 64 | 18,9 GB | 728 | 32–64 | 240 ms |
| Qwen3.8-27B UD-Q4_K_XL + mmproj, KV q4/q4 | 32k / 512 | 19,1 GB | 1028 | 40–48 | 242 ms |
| Qwen3.8-27B UD-Q4_K_XL + mmproj, KV q4/q4 | 131k / 512 | 21,7 GB | 1023 | 38–42 | 257 ms |

ubatch 512 sólo mejora el prefill frío (+41%); los turnos cortos no cambian.
131k cuesta 2,6 GB más sin ganar velocidad, así que Charla usa 32k.

## Charla de punta a punta (ControlApi, entrada sintética, conversación nueva)

Fin de habla → primer audio (`endToFirstAudioMs`) y desglose por etapa. El
STT no aparece en `latency.jsonl` (`sttMs` = 0 con entrada sintética); el log
de Charla lo da aparte: 38–52 ms.

| Configuración | 1.er turno (frío) | Turnos tibios | LLM al 1.er texto | TTS | VRAM GPU0 / GPU1 |
|---|---:|---:|---:|---:|---:|
| 9B, args de antes (repartido en 2 GPU, K-only, thinking) | 1,80 s | 2,29–2,67 s | 1,28–2,11 s | 0,25–0,33 s | 6,3 / 4,4 GB |
| 9B con los arreglos | 0,73 s | 0,57–0,73 s | 0,33–0,39 s | 0,16–0,21 s | 3,3 / 6,7 GB |
| 27B 131k/ub 64 (tune perdido) | 16,0 s | 0,85–1,08 s | 0,54–0,62 s | 0,19–0,21 s | 3,4 / 20,6 GB |
| **27B 32k/ub 512 (recomendado)** | 6,5 s | **0,74–1,08 s** | 0,50–0,55 s | 0,15–0,17 s | 3,3 / 18,5 GB |
| Perfil `sys-charla-jarvis-qwen38-27b` (whisper y piper lanzados por la app) + StudIA bge-m3 indexando sin parar en CPU | 6,6 s | 0,80–1,11 s | 0,52–0,57 s | 0,18–0,27 s | 3,7 / 18,7 GB |

Con StudIA cargando el servidor de embeddings (bge-m3, `--n-gpu-layers 0`, los
hilos por defecto de llama.cpp) y una carga continua de lotes de 8 textos, el
turno tibio sube ~0,05–0,1 s y el TTS hasta 0,27 s: piper comparte la CPU con el
indexado pero sigue en tiempo real. El servidor de StudIA igual reserva ~0,4 GB
en GPU0 y ~0,26 GB en GPU1 por el contexto CUDA, aunque no descargue capas.

El primer turno paga el prefill de ~15k tokens de system + tools justo después
del relanzamiento que hace Charla; el warmup de Charla lo adelanta si el
usuario tarda unos segundos en hablar.

### Tools (misma consigna, conversación nueva por modelo)

| Pedido | 27B | 9B |
|---|---|---|
| "¿Cuánto es doce por treinta y siete?" | "444." directo | abrió computer use (launch → windows → observe) para multiplicar, 23 s |
| "Buscá en internet qué temperatura va a hacer mañana en Buenos Aires" | web_search → web_fetch → "algo nublado, máxima 26, mínima 16, 21% de lluvia", 23,5 s | web_search → web_fetch, respuesta correcta y más corta, 19 s |
| "Abrí la calculadora y calculá tres por tres" | desktop_launch → desktop_windows → desktop_observe (timeout) → cierra el turno, 52 s | se enreda en launch/windows/observe y no termina en 180 s |

Las fallas de computer use son del backend Linux, no del modelo: ver
"Pendiente".

## Qué se descartó

- **Modelos que usan las dos 3090 enteras** (ASTRA DeepSeek DSX, SOL NInfer,
  Flash-Next): no dejan GPU para la voz y su primer token no es de tiempo real.
- **Qwen3.5-9B**: más rápido (0,57–0,73 s), pero usa tools de más y no cierra
  bien una tarea de escritorio fallida. Sigue siendo la opción para una sola GPU
  de 8–12 GB.
- **Gemma 4 12B QAT**: no hay perfil con visión ni medición de tools en esta
  máquina; con los 27B disponibles no aporta.
- **whisper-large-v3-turbo**: mejor texto pero +55 ms, +0,9 GB y necesita
  `-ac 1500`, mientras la app fija 640 para todos los modelos.
- **Parakeet**: mismo WER que whisper-small en este corpus, pero lanza un
  proceso por turno (461 ms en CPU).

## Pendiente

- **Linux computer use**: `desktop_launch` resuelve los alias a nombres de
  Windows (`calc`, `notepad`…) y en Ubuntu no existen (`gnome-calculator`).
  `desktop_observe` con tres monitores (2560 + 2×1920) supera el timeout de
  30 s del worker. Las dos cosas hicieron fallar la prueba de la Calculadora con
  los dos modelos.
- **whisper-server con CUDA en Linux**: la descarga gestionada de la app baja el
  binario CPU de whisper.cpp (322 ms por frase). Para esta medición se compiló
  whisper.cpp con CUDA (`-DGGML_CUDA=ON`, arch 86) y se lo dejó en
  `voice/bin/whisper-server/`. La app ya lo usa si está ahí.
- **Charla relanza el server al entrar** para aplicar el reparto multi-GPU; si se
  arrancara directo con el reparto, el primer turno no pagaría ~6 s.
