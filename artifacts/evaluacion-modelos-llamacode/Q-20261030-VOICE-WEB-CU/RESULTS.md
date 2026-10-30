# Q191 — resultados de componentes y pruebas pendientes

**Estado:** Lightpanda/Chrome A/B, STT/TTS local y regresiones Linux cerrados. Quedan bloqueados por condiciones externas el pipeline Hugging Face full-duplex (servidor LlamaCode usando ambas 3090) y el holdout Computer-Usage multi-tenant (sin principal autenticado/policy server-side verificable).

## Web-Usage: Lightpanda frente a Chrome

Preregistro en `PLAN.md`. Se usó el mismo cliente Playwright 1.57.0 por CDP, una sesión/contexto nuevo por brazo, Chrome 156.0.8078.47 y Lightpanda `1.1.0-nightly.11275+78bbb64db` (SHA-256 `73c6594300deeb8f20b30f96842655775ccc72f77af0a9085bbcae40b90759f1`). Lightpanda se ejecutó con telemetría deshabilitada. Los procesos, perfiles temporales y puertos propios se cerraron tras cada réplica.

| Brazo | Fixture E2E local | 20 sitios públicos, dos pasadas | Mediana por visita pública | Tiempo por pasada pública | Pico RSS árbol de procesos |
|---|---:|---:|---:|---:|---:|
| Chrome | 9/9 | 35/40 | 0.412 s | 11.293 s promedio | 1701.7 MB |
| Lightpanda | 9/9 | 34/40 | 0.210 s | 8.088 s promedio | 108.9 MB |

En el fixture local, las medianas por flujo fueron 0.149 s (Chrome) y 0.050 s (Lightpanda); ambos verificaron el estado final exacto en los tres sitios y tres réplicas. Las muestras RSS se tomaron cada 100 ms y son un pico observado, no una medición de memoria estabilizada ni energía.

Las fallas públicas fueron respuestas HTTP de sitio, no errores de conexión CDP: Chrome recibió 403 en `npmjs.com` y `stackoverflow.com` en la primera pasada, y 403/429 en `npmjs.com`, `stackoverflow.com` y `gnu.org` en la segunda. Lightpanda recibió 403 en `arxiv.org`/`stackoverflow.com` y 503 en `news.ycombinator.com` en ambas pasadas. El orden alternado redujo el sesgo temporal, pero los WAF y límites de tasa impiden atribuir toda diferencia al motor. La tasa por sitio fue 18/20 y 17/20 para Chrome, 17/20 en ambas pasadas para Lightpanda.

**Decisión provisional:** Lightpanda es técnicamente compatible con el fixture CDP y muestra menor latencia/memoria en esta muestra; mantener Chrome como default porque su éxito público fue ligeramente mayor y los sitios con 403/503 requieren fallback. No se midió aún la calidad del planificador de Unsloth Browser Use ni se integró Lightpanda en LlamaCode. Tampoco se tocó Computer-Usage. Evidencia cruda: `runs/web-fixture-summary.json`, `runs/web-sites-summary.json`, recibos y logs por brazo.

El A/B separado del planificador usa Qwen3.5-4B Q4 con 2 hilos CPU en ambos motores porque un servidor LlamaCode activo ya ocupaba las dos 3090. Modelo y runtime quedaron fijados por SHA; dos réplicas, tres flujos, prompt/schema iguales y seed 191. Resultado combinado: Chrome **6/6**, Lightpanda **6/6**, 18 decisiones por brazo, cero selecciones inválidas o inseguras. Mediana de llamada al modelo: **12.872 s** Chrome y **12.340 s** Lightpanda; suma de inferencia: **228.144 s** y **226.860 s**. Tiempo pared por pasada: Chrome 114.432/114.780 s, Lightpanda 114.953/112.581 s. No hay diferencia E2E útil; dominó la inferencia. Evidencia: `runs/planner-summary.json` y recibos por réplica. El runner usa una copia del fixture de cancelación y restringe los clics a los controles sintéticos autorizados; no es la app Unsloth Desktop Browser Use.

## INGI-Charla: STT y TTS local

Corpus fijado antes de inferencia: 20 clips FLEURS `es_419` dev, dos pasadas por motor, 237 s de audio en total por pasada. La selección y hashes están en `receipts/fleurs-corpus-manifest.json`. Las métricas WER/CER son sobre la primera pasada y texto normalizado; latencia y RTF usan ambas pasadas. `es_419` no demuestra rendimiento específico en el habla del usuario.

| STT CPU | WER micro | CER micro | Mediana por clip | p95 por clip | Pico RSS observado |
|---|---:|---:|---:|---:|---:|
| Whistle 2.0, residente | 10.56% | 3.89% | 0.359 s | 0.545 s | 103.8 MB |
| Whisper base, CLI por turno | 9.36% | 2.83% | 0.370 s | 0.421 s | 301.4 MB |
| Parakeet TDT v3 Q4, CLI por turno | **4.18%** | **1.66%** | **0.276 s** | **0.337 s** | 524.4 MB |

Whistle usa menos memoria, pero no superó al Parakeet local en exactitud ni latencia de esta cohorte. Las rutas no tienen el mismo ciclo de vida: Whistle permanece cargado y los controles arrancan un proceso por clip, como la ruta `process_batch` de Charla; los tiempos no aíslan la velocidad del modelo. Ninguno de los tres resultados mide parciales o barge-in. Evidencia: `runs/whistle-asr.json`, `runs/whisper-base-asr.json`, `runs/parakeet-q4-asr.json` y logs por clip.

Piper `es_AR Daniela high`, CPU, diez frases fijadas × dos pasadas: primer `AudioChunk` mediano **0.417 s**, p95 **0.536 s**, RTF mediano **0.053** y RSS máximo observado **505 MB**. Es un control de síntesis residente, no latencia acústica micrófono→parlante. WAVs de la primera pasada en `runs/piper-wav/`; evidencia `runs/piper-tts.json`.

Kitten-TTS2 `SpanishTango`, CPU 16 hilos, diez frases × dos pasadas: WAV completo mediano **15.29 s**, p95 **18.10 s**, RTF mediano **1.147** y RSS observado **2027 MB**. El tiempo de carga con pesos ya en caché fue 0.83 s; no es inicio cold. El binding entrega el WAV terminado, así que no hay métrica de primer audio ni prueba de streaming. Evidencia: `runs/kitten-tts.json`, `runs/kitten-wav/` y hashes del bundle en `PLAN.md`.

El proxy preregistrado de inteligibilidad transcribió los diez WAV de la primera pasada con el mismo Parakeet Q4: Piper **WER 14.50%, CER 6.04%**; Kitten **WER 8.40%, CER 5.34%**. Esto mide recuperabilidad por ese ASR, no naturalidad, acento ni MOS. Kitten sugiere utilidad para síntesis batch, pero la ruta CPU medida no conviene como default de conversación de baja latencia: tardó unas 34 veces más que el WAV completo de Piper en medianas de estas frases. Mantener Piper para INGI-Charla y evaluar Kitten por escucha humana sólo si interesa narración offline. Evidencia: `runs/tts-intelligibility.json`.

La documentación oficial de Hugging Face Speech-to-Speech describe un pipeline realtime con VAD, STT parcial opcional, LLM con streaming/tool calls y TTS en streaming, y un servidor WebSocket/WebRTC compatible con eventos Realtime. El default Linux/NVIDIA incluye Qwen3.5-4B vía Transformers y Parakeet/Qwen3-TTS; el README advierte que la ruta CPU responde lento. Es un candidato directo para comparar el pipeline completo y barge-in contra INGI-Charla, pero no se instaló ni midió mientras el servidor LlamaCode existente ocupaba ambas GPU. Reanudación: cuando ambas 3090 estén libres, comparar con los controles locales usando FLEURS y un holdout rioplatense autorizado; medir fin de voz→primer audio, parciales, interrupciones y errores de turno. Fuente primaria: https://github.com/huggingface/speech-to-speech.

VoiceStudio se documenta como catálogo/interfaz para motores ASR/TTS independientes, con requisitos y medidas por motor. No hay un único “modelo VoiceStudio” que pueda compararse con un perfil; Parakeet, Piper y Kitten ya se midieron directamente. No se instaló la app adicional sin un motor/conector concreto que aporte una capacidad ausente. Fuente primaria: https://github.com/debpalash/VoiceStudio/blob/main/docs/engines/README.md.

La suite `test_voice` cubre flujo parcial/cancelación de habla sostenida en su controlador simulado; pasó en CTest. No simula audio acústico en vivo ni mide micrófono→parlante. VoiceStudio/HF S2S y barge-in acústico E2E siguen pendientes. `IA local!L30/L55` y el inventario local se actualizaron para Kitten/Whistle.

## Computer-Usage

El build Linux Release actual pasó **99/99** casos de CTest, incluidos `test_voice`, `test_automation`, `test_automation_store`, `test_desktop_backend`, `test_visual_matcher`, `test_tool_execution_safety` y `test_agent_tools`. La última suite tardó 256.38 s; no fue un timeout. Es evidencia de regresión de componentes y contratos, no la certificación E2E de 20 casos del ejecutable Windows SHA `AE85A276…`.

El probe visual opcional en Xvfb 1280×900 con Openbox y el binario `qa_visual_automation` SHA-256 `16d0c2872a76252204d01b977aa5943e1a03363c3bf38bb8cd1e1db6f8d38908` obtuvo **4/4**: dos targets × temas claro/oscuro. Cada caso encontró un target único (`found=true`, `ambiguous=false`), realizó el clic y validó el contador de su botón. La primera ejecución en Xvfb sin gestor de ventanas falló 4/4 porque `_NET_CLIENT_LIST` estaba vacío; se conserva en `logs/cu-visual-probe.log` y se corrigió el entorno aislado, no el matcher. Corrida válida: `logs/cu-visual-probe-wm.log`. Este fixture sólo prueba una ventana Qt sintética en Linux; no mide recuperación autónoma ni precisión en aplicaciones arbitrarias.

La suite Windows CU01–CU20 y el A/B MUSE requieren su entorno y fixture exactos para comparación válida; los resultados históricos no se atribuyen a este build. El gate de tenant sigue pendiente de un principal autenticado y autorización server-side; no se promovió autonomía. Las regresiones de `stale`, ambigüedad, aserciones y receipts pasaron en el gate Linux, pero falta un holdout E2E pareado sobre el flujo actual. La condición de reanudación es disponer de un agente/modelo y de un entorno de escritorio aislado con principal tenant verificable para ejecutar los casos con postcondiciones.
