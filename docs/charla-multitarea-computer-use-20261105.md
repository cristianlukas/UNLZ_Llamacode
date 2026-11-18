# Ingi Charla: voz en tiempo real + varios agentes en paralelo, agent-desktop y más voces — 2026-11-05

Segunda vuelta sobre el sheet "Listado" (Q207, con las GPU liberadas por el usuario;
Q206 de Codex quedó suspendido y su lock en `WORK_QUEUE.stale-20261105T164312Z.lock`).
Sigue a [charla-tts-normalizacion-20261105.md](charla-tts-normalizacion-20261105.md).
Recibos, scripts y salidas: `artifacts/evaluacion-modelos-llamacode/Q-20261105-INGI-CHARLA-SHEET/`.

## Resumen

| Pregunta | Respuesta medida | Qué cambió en LlamaCode |
|---|---|---|
| ¿La Charla puede hablar en tiempo real mientras varios agentes trabajan? | Con 1 slot, no: la voz tardó **46,9 s** hasta su primera oración con 3 agentes generando. Con 4 slots y los prompts precalentados, **1,09 s** (TTFT 0,38 s). | Charla multitarea + perfil `sys-charla-jarvis-qwen38-27b-multi` |
| ¿Cuál es la mejor IA que entra junto a voz + PC + web + agentes en paralelo? | **Qwen3.8-27B UD-Q4** en una 3090, 4 slots de 32k. DeepSeek Maya-XS es más inteligente (Q172 84,67) pero Project Maya atiende **una secuencia por vez** (FIFO): con agentes en paralelo la voz queda en cola. | Maya sigue siendo el perfil para una tarea a la vez |
| ¿agent-desktop (Vercel) sirve? | Sí. Calculadora GTK4 en Xvfb: **5/5**, 3×3=9 sin mover el mouse, ~70 ms por comando. El AT-SPI propio de LlamaCode encontró **0 controles** en 8 s. | Backend `AgentDesktopCli` en Linux (AT-SPI queda de fallback) |
| ¿Kokoro o Ming-3.0-tts mejoran la voz? | Kokoro ≈ Piper en inteligibilidad y 0,33–0,35 s al primer audio (Piper 0,42 s); Ming empata pero tarda 0,97 s (sin streaming) y usa 2,9 GB de GPU. | Ninguno cambia el default |

## 1. Voz + agentes en paralelo sobre el mismo llama-server

**Montaje.** Qwen3.8-27B UD-Q4_K_XL + mmproj, binario `cuda-flashnext-2x3090`, GPU1
(la RTX 3090 que no usa la voz), KV q4_0, batch 2048/512, `--reasoning off`. Script
`scripts/bench.py` + `scripts/arm.sh`: una petición de voz (system de ~1,7K tokens,
pregunta corta, 120 tokens) sola ("idle") y luego **mientras 3 agentes** (system de ~9K
tokens, informe de 700 palabras, 900 tokens) generan en paralelo ("loaded"). 4
repeticiones por brazo; se mide TTFT, tiempo a la primera oración (lo que importa
para empezar a hablar) y tokens/s agregados de los agentes.

| Brazo | Slots / ctx | VRAM GPU1 | Voz sola: 1ª oración | **Voz con 3 agentes: 1ª oración** | TTFT con agentes | Agentes tok/s |
|---|---|---:|---:|---:|---:|---:|
| A · perfil actual | 1 / 32k, MTP3 | 19,0 GB | 0,54 s | **46,9 s** | 46,6 s | 35,8 |
| B | 4 / 128k, MTP3 | 23,3 GB | 0,71 s | 1,07 s (pico frío 19,1 s) | 0,38 s | 44,0 |
| C | 4 / 128k, `--kv-unified`, MTP3 | 23,5 GB | 0,75 s | 0,97 s (pico frío 20,5 s) | 0,46 s | 48,3 |
| D | B + `id_slot` fijo + precalentado | 23,3 GB | 0,56 s | 15,7 s | 10,6 s | 31,1 |
| **E** | B + precalentado concurrente | 23,3 GB | 0,59 s | **1,09 s** (peor 2,3 s) | 0,38 s | 44,8 |
| **F (perfil)** | E sin MTP | **20,5 GB** | 0,57 s | **1,25 s** (peor 1,5 s) | 0,33 s | 41,6 |

Lecturas:
- Con 1 slot la voz espera a que terminen los agentes: inservible para "hablar mientras trabaja".
- El pico de ~20 s de B/C es el prefill en frío de los prompts de agente (3×9K tokens)
  la primera vez. Precalentarlos en paralelo al iniciar la Charla (E/F) lo elimina.
- Fijar el slot con `id_slot` en este build empeora todo (D): no se usa.
- MTP con 4 slots gana poco (1,09 contra 1,25 s; 44,8 contra 41,6 tok/s) y ocupa 2,8 GB
  más: 23,3 de 24 GB no deja lugar para la torre de visión cuando el agente mira la
  pantalla. El perfil multitarea va **sin MTP** (F).

**E2E con el modelo real y el código real** (`charlaParallelTaskAgainstRealServer`,
`LC_CHARLA_E2E_SERVER`): con el agente principal ocupado, "calculá cuánto es treinta y
siete por doce" se resolvió en un agente de fondo en 7,9 s en frío y la Charla anunció
"Listo lo de calculá cuánto es treinta y siete…: 37 por 12 es 444."

### Qué hace ahora la Charla

- Si el agente principal está trabajando y el server tiene slots libres
  (`CharlaMultitask::backgroundCapacity`: uno siempre queda para la voz), un pedido
  nuevo arranca **ya** en otro agente ("Dale, lo hago en paralelo.") en vez de
  "Anotado, sigo con eso después". Sin slots libres, la cola de siempre.
- Los agentes de fondo (`SubAgentRunner` con prompt propio) usan web, archivos y shell
  en `AppLocalData/charla-tareas/<id>`, **sin `desktop_*`** (el mouse y el teclado son
  del agente principal: dos agentes tecleando se pisan), sin `<think>` y sin acciones
  destructivas (nadie las aprueba).
- Al terminar, el resultado se anuncia en 1–2 frases ("Listo lo de …: …") **cuando el
  usuario no está hablando** (`VoiceController::announce`; si está a mitad de una
  frase, se reintenta cada 700 ms).
- "¿Cómo van las tareas?" / "¿qué estás haciendo?" se contesta sin el LLM.
- Los slots de fondo se precalientan una vez por arranque del agente.
- `CharlaTuning` ya no baja a 1 slot ni a 32k totales un server multitarea: el tope de
  contexto es 32k **por slot**.
- Los perfiles de sistema ahora pasan `runtime.parallelSlots` al agente (antes se
  ignoraba y el agente creía tener 1 slot aunque el server tuviera más).

Perfil: **`sys-charla-jarvis-qwen38-27b-multi`** (4×32k, sin MTP). El de baja latencia
para una tarea a la vez (`sys-charla-jarvis-qwen38-27b`) y el más inteligente
(`sys-charla-jarvis-deepseek-maya-xs`) no cambian.

## 2. Computer use: agent-desktop (Vercel Labs)

agent-desktop 1.2.0 (release del 05/11, binario Linux precompilado, SHA-256 contra
`checksums.txt` de la release). CLI sobre AT-SPI (Linux), UI Automation (Windows) y AX
(macOS) con refs estables, acciones semánticas sin mover el puntero y sesiones
multi-agente (`--session` + `--agent-id`).

Montaje aislado para no tocar el escritorio del usuario: Xvfb `:97` + Openbox + bus
D-Bus y AT-SPI propios + `gnome-calculator` (GTK4). Sin gestor de ventanas agent-desktop
se niega (`native_window_unproven`): necesita las propiedades EWMH.

| Camino | Controles vistos | 3×3=9 sin mover el mouse | Tiempo de la tarea |
|---|---:|---:|---:|
| agent-desktop CLI directo (`scripts/e2e.py`) | 36 refs en 62 ms | **5/5** | 1,71–1,76 s (4 esperas de 300 ms incluidas) |
| LlamaCode `qa_background_calc`, AT-SPI propio | **0** en 8 s | 0/1 | — |
| LlamaCode `qa_background_calc` con `AgentDesktopCli` | 30 controles | **5/5** (9/9 chequeos cada vez) | 1,85 s |

Por qué fallaba el AT-SPI propio: lanza un `gdbus` por cada propiedad de cada nodo y
descarta nodos sin coordenadas de pantalla; GTK4 en X11 no publica coordenadas
absolutas, así que en apps GTK4 (Calculadora, Texto, Archivos de GNOME) no veía nada.

Integración (`src/core/automation/AgentDesktopCli.*`): si el binario está instalado
(`$LLAMACODE_AGENT_DESKTOP`, `AppLocalData/tools/agent-desktop/` o el PATH),
`desktop_controls`, `desktop_click_element` y `desktop_control_action` en Linux van por
agent-desktop (ventana X11 → `_NET_WM_PID` → ventana de agent-desktop → snapshot con
refs, ids `ad:@snap:eN`); si no ve la ventana, sigue el AT-SPI de antes. Instalar:
`scripts/install-agent-desktop.sh` (verifica el SHA-256). En el escritorio MATE real
`status` da accesibilidad concedida y `list-apps` ve las apps de la sesión.
`qa_background_calc` ahora también corre en Linux.

## 3. Más voces (TTS) — mismo corpus de 20 respuestas normalizadas, ASR Parakeet

| TTS | Dónde | Primer audio (mediana / p95) | RTF | WER | Frases con error |
|---|---|---:|---:|---:|---:|
| Piper es_ES davefx (default) | CPU | 0,42 s / 0,54 s (Q191, residente) | 0,053 | 7,3% | 7/20 |
| Kokoro-82M `ef_dora` | CPU 8 hilos | **0,35 s** / 0,55 s | 0,12 | 6,1% | 7/20 |
| Kokoro-82M `em_alex` | CPU 8 hilos | **0,33 s** / 0,50 s | 0,11 | 6,1% | 6/20 |
| Ming-3.0-tts-0.5B (ref. sintética de Piper) | RTX 3090 | 0,97 s / 1,78 s (WAV completo) | 0,36 | 6,1% | 6/20 |

Con n=20 las diferencias de WER son ruido. Kokoro es la mejor alternativa a Piper (un
poco más rápido al primer audio; LlamaCode ya lo acepta por HTTP con PCM en streaming,
`ttsMode` "http"/"kokoro" + `ttsStreamAudio`), pero no tiene servidor administrado por
la app: queda como opción, sin cambio de default. Ming no hace streaming y ocupa GPU:
sólo tiene sentido para clonar voz, no para conversación.

## 4. Lo que quedó sin probar y por qué

- **LFM3-Omni-2B**: corre en WebGPU dentro del navegador; no hay runtime de servidor
  para enchufarlo a la Charla.
- **Gemma 4 12B Unified / Ming-3.0-audio-tiny (speech-to-speech)**: reemplazan el
  pipeline STT→LLM→TTS entero y su audio de entrada es ≤30 s; no conviven con un 27B
  que además tiene que operar la PC. Requieren otra arquitectura.
- **E2E acústico real** (micrófono → parlante con la app abierta): suena por el
  parlante mientras se usa la PC. Las piezas están medidas por separado y el flujo de
  multitarea pasó con el modelo real por el código real.
- **Visión bajo carga** en el perfil multitarea: quedan 3,5 GB libres en GPU1 sin MTP;
  no se midió una captura con 3 agentes generando.
