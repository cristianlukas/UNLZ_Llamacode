# Ingi Charla: revisión del sheet (computer use, web, voz realtime, LLM) y normalización de texto para el TTS — 2026-11-05

Revisión de todas las filas del sheet "Listado" (pestañas Accionables, IA local,
Recursos, Sin evaluar y Enlaces revisados) que tocan computer use, web usage,
voz en tiempo real o el LLM que convive con las dos cosas. Se cruzó cada una
con lo que ya tiene LlamaCode y con lo que ya se midió (Q191, Q-20261102).
Recibos, corpus y scripts: `artifacts/evaluacion-modelos-llamacode/Q-20261105-INGI-CHARLA-SHEET/`.

Todo se corrió en CPU: Q206 tenía el lock de `WORK_QUEUE` con GPU, y no se tocó.

## Listado: qué se probó y qué quedó

| # | Fila del sheet | Estado en LlamaCode antes | Qué se hizo | Resultado |
|---|---|---|---|---|
| 1 | Recursos 100 · NeMo Text Processing (normalizar números/abreviaturas para TTS) + Q191 Piper WER 14,5% | El texto del agente iba crudo al TTS; sólo se quitaba `<think>` | A/B Piper → Parakeet, 20 respuestas típicas del agente | **Integrado**: `SpeechTextNormalizer`, WER 26,8% → 7,3% |
| 2 | Accionables 57 / IA local 38 · STT (Whistle, Parakeet, Whisper) | Perfiles JARVIS usan whisper-small en CUDA; Parakeet ya existe como motor `process_batch` | WER/latencia en los 20 clips FLEURS es_419 de Q191 | Parakeet más preciso que whisper-small, pero en CPU; **no se cambia el default** (ver abajo) |
| 3 | Accionables 61 · Smart Turn v3.2 | `TurnDetector` (endpointing por texto) activo | — | Gate de Q202 ya falló (FPR natural 0,224 > 0,05). No integrar |
| 4 | Accionables 57 · barge-in | Barge-in con voz sostenida ~400 ms | — | Q191: 5/5 con onset normalizado; no hay cambio justificado |
| 5 | Recursos 120 · Lightpanda | `web_fetch` ya orquesta proveedores (`direct` → playwright/camofox) | — | Q191: 34/40 vs Chrome 35/40, 16× menos RAM. Queda como posible proveedor extra, no default |
| 6 | IA local 80 · Unsloth Browser Use | `browser_*` + `web_fetch` | — | Q191: planificador 6/6 en ambos motores; nada que copiar |
| 7 | Accionables 66/80 · agent-desktop (Vercel) | Linux usa AT-SPI2 + xdotool + Tesseract | — | Pendiente: no hay Rust/Node en la máquina; requiere instalar toolchain |
| 8 | IA local 98 / Accionables 71 · LFM3-Omni-2B | — | — | Pendiente: WebGPU en navegador, sin español medido |
| 9 | IA local 95 · Gemma 4 12B Unified (audio nativo) | — | — | Pendiente: requiere GPU (lock Q206) y su audio de entrada es ≤30 s |
| 10 | IA local 10 / Accionables 83 · Ming-3.0 TTS, Kitten-TTS2, Kokoro+OpenVoice | Piper / Qwen3-TTS / Pocket | — | Kitten medido en Q191: RTF 1,15 en CPU, no apto para conversación. Ming/OpenVoice sin correr |
| 11 | El LLM que entra con voz + PC + web | `sys-charla-jarvis-deepseek-maya-xs` y `sys-charla-jarvis-qwen38-27b` | Revisión de evidencia (no hay candidatos nuevos con visión en el sheet) | Sin cambio: DeepSeek V4.1 Flash Maya-XS (Q172 84,67, visión, 2×3090) sigue siendo el más capaz; Qwen3.8-27B UD-Q4 la alternativa de una GPU |

## 1. Normalización del texto para el TTS (integrado)

El prompt de modo voz ya pide "nada de markdown ni URLs", pero el modelo igual
devuelve negritas, URLs copiadas de `web_search`, "24 °C", "12 × 37",
"$1.245,50" o "05/11/2026". Además, el troceo en oraciones cortaba en cualquier
punto, así que "$1.245,50" llegaba al TTS como "El dólar cerró a $1." y "245,50."
por separado, y las URLs se partían en cada punto.

**Método.** 20 frases típicas de respuesta del agente (`tts-corpus.tsv`, con lo
que una persona espera oír). Brazo A: texto crudo, como hoy. Brazo B: texto por
`SpeechTextNormalizer` (el C++ real, compilado aparte con
`scripts/normalizer_driver.cpp`). Ambos por Piper `es_ES-davefx-medium` (la voz
de los perfiles JARVIS) y transcriptos con Parakeet TDT v3 q4 en CPU. WER contra
la referencia hablada, con los dígitos del ASR pasados a palabras
(`scripts/score_tts_ab.py`).

| Brazo | WER | Frases con error |
|---|---:|---:|
| Texto crudo (antes) | 26,8% (48/179) | 17/20 |
| Normalizado | **7,3%** (13/179) | **7/20** |

Lo que Piper leía antes: "asterisco asterisco la calculadora", "almohadilla",
"https barra barra www…", "15 km barra H", "05 barra 11 barra 2026", "grados C",
"dólar 1245" (en Argentina "$" son pesos) y "12.37 igual 444" (se comía el "×").
Las 7 frases que quedan con error son casi todas del ASR escribiendo "km", "GB"
o "config.json" en vez de palabras, y "smn" oído como "cmn".

**Qué hace.** Por oración y justo antes del motor (`VoiceController::pumpTts`),
así vale igual para Piper, Qwen3-TTS, Pocket o un endpoint HTTP:
- markdown: negritas, código inline, encabezados, viñetas, links `[texto](url)`,
  tablas; emojis fuera; bloques ``` se quitan en `sanitizeForSpeech`.
- URLs → sólo el dominio ("smn punto gob punto ar"); emails con "arroba";
  archivos con extensión conocida ("config punto json").
- en español: fechas (dd/mm/aaaa e ISO), horas, monedas ($ = pesos, USD, €),
  °C, %, unidades (GB, km/h, ms…), aritmética (×, =, +, rangos) y números a
  palabras con género y apócope ("una ventana", "veintiún grados",
  "doscientas personas"). En inglés sólo la parte estructural.
- el troceo sólo corta en un punto seguido de espacio; en streaming, un punto
  al final del texto recibido espera al próximo delta (puede ser "$1." de
  "$1.245").

Tests: `speechNormalizerAgentReplies` (el corpus entero), `speechNormalizerNumbersEs`,
`speechNormalizerOtherLanguages`, `ttsSplitKeepsUrlsAndDecimals` y el de
integración `ttsReceivesNormalizedText` (stub de `/v1/audio/speech`: verifica el
`input` que recibe el TTS), en `tests/test_voice.cpp`.

## 2. STT: whisper-small vs Parakeet (medido, sin cambio de default)

20 clips FLEURS es_419 de Q191 (`~/.cache/q191-fleurs-es419/selected`), mismo
normalizador/WER que Q191, CPU 16 hilos, proceso por clip (incluye carga del
modelo), una pasada (`scripts/run_stt_fleurs.py`, `runs/stt-fleurs-summary.json`).

| STT | WER | CER | Mediana por clip | p95 |
|---|---:|---:|---:|---:|
| whisper-small (default JARVIS) | 6,37% | 2,06% | 1,01 s | 1,19 s |
| whisper-large-v3-turbo q8 | **3,39%** | 1,26% | 2,41 s | 2,69 s |
| Parakeet TDT v3 q4 | 4,18% | 1,66% | **0,25 s** | 0,30 s |

En los perfiles JARVIS whisper-small no corre en CPU sino en CUDA, a ~35 ms por
frase (`charla-balance-2x3090-20261101.md`). Parakeet (`-ng`, como lo lanza
`SttEngine`) es más preciso pero agregaría ~0,2 s al segmento final. Como la
latencia es el objetivo de esos perfiles, el default no cambia. Si se prefiere
precisión, elegir "Parakeet TDT v3" en Charla → STT: ya está integrado y su
binario viene en el paquete de whisper.cpp. Pendiente: medir parakeet-cli en
CUDA cuando la GPU esté libre, porque si baja a decenas de ms conviene como default.

## Qué no se probó

- E2E acústico (micrófono → parlante) con el LLM cargado: necesita GPU (lock
  Q206) y suena por el parlante mientras se usa la PC. El benchmark sintético de
  Charla (`charlaSimulateUtterance`) es el camino cuando se libere.
- La calidad percibida (MOS) de la voz; el proxy es la inteligibilidad por ASR.
- agent-desktop, LFM3-Omni, Gemma 4 Unified, Ming-3.0 TTS: ver el listado.
