# Auditoría Vellium v1.2.0 — voz local — 2026-09-18

## Veredicto

Vellium aporta buenas decisiones de producto para voz local: procesos STT/TTS
residentes, TTS por streaming, detección de backends locales y una interfaz de
voz unificada. No aporta un modelo de lenguaje superior ni métricas comparables
con SOL, por lo que no cambia la tabla de perfiles LLM.

Fuente revisada: [repositorio oficial de Vellium](https://github.com/tg-prplx/vellium).

## Protocolo reproducible de comparación

Para no confundir una prueba de integración con una medición de calidad de
audio, cada comparación futura debe conservar el mismo corpus, configuración y
estado del proceso:

| Área | Métrica | Procedimiento y unidad |
| --- | --- | --- |
| STT | Primer parcial, transcripción final | Desde fin de habla hasta el primer parcial y hasta el resultado final, en ms; informar p50/p90/p95. |
| STT | RTF | `tiempo_wall_STT / duración_audio`; menor que 1 significa tiempo real. Informar p50/p90/p95. |
| STT | WER/CER | 30 audios fijos en español, texto de referencia versionado, normalización documentada; informar promedio y por clase (comando/conversación). |
| TTS | Primer audio, audio completo | Desde solicitud hasta primer PCM reproducible y hasta fin de síntesis, en ms; informar p50/p90/p95. |
| TTS | RTF | `tiempo_wall_TTS / duración_audio_generado`; medir en frío, residente y por oración. |
| E2E | Fin de habla → primer audio | Incluye STT, primer texto útil del LLM, solicitud TTS, generación y playback; informar p50/p90/p95 y tasa de turnos completos. |
| Streaming | Huecos y underruns | Máximo hueco entre oraciones/chunks, cantidad de underruns y turnos abortados. |
| Barge-in | Tiempo de corte | Desde voz detectada durante playback hasta que deja de salir audio y hasta que se cancela la generación, en ms; incluir falsos positivos. |
| Residente | Arranque y estabilidad | Arranque frío, primer turno caliente, 30 turnos consecutivos, reinicios, procesos huérfanos y errores de health-check. |
| Recursos | RAM/VRAM/CPU | Pico y reposo del STT/TTS, por separado y junto al LLM; registrar modelo, backend, driver y contexto. |

Condiciones mínimas: tres calentamientos descartados, 30 repeticiones medidas,
misma máquina, mismo idioma (`es`), mismo sample rate, mismo texto de prueba,
misma temperatura del LLM y sin cambiar de backend durante la corrida. La
comparación de calidad sólo se promueve si conserva el corpus y los artefactos
de referencia; una cifra publicada sin esos datos queda como referencia
externa, no como métrica local.

## Qué ya existe en LlamaCode

| Idea de Vellium | Implementación actual | Estado |
| --- | --- | --- |
| STT local o compatible con Whisper | `http_batch`, Parakeet `process_batch` y `stream_process` NDJSON | Ya cubierto |
| TTS residente | Piper `--json-input`, Pocket TTS como sidecar residente y procesos HTTP externos administrados | Ya cubierto |
| TTS incremental | PCM chunked y generación/reproducción por oraciones | Ya cubierto |
| Interrupción de voz | Barge-in por VAD o PTT, cancela TTS y generación del turno | Ya cubierto |
| Backend local persistente | `ttsManagedCommand`, `sttManagedCommand`, health/lifecycle y Job Object | Ya cubierto |
| Métricas | fin de habla → primer texto/audio, p50/p90/p95 y registro local | Ya cubierto |
| Qwen3-TTS CLI residente | El CLI actual se ejecuta por turno | No cambiar sin protocolo residente validado |

La observación más importante del post —evitar recargar el TTS en cada
respuesta— ya está aplicada a Piper, Pocket TTS y endpoints administrados. El
modo HTTP también permite usar un servidor persistente como `audio.cpp` sin
agregar otra ruta al cliente.

## Validación local ejecutada

- Build Linux nativo reproducible con Qt 6.8.3/GCC, `ctest -R '^test_voice$'`:
  **1/1 PASS**.
- Ejecución directa de `test_voice -txt`: **41/41 PASS en 4 ms**, sin skips ni
  fallos.
- Se validaron round-trip de configuración, STT multipart y streaming, Parakeet,
  argumentos Piper/Qwen/Pocket, VAD, turn-taking, TTS por oraciones, streaming,
  barge-in, métricas y políticas de capacidad.
- En este entorno no existen muestras reales en `voice/latency.jsonl`, ni están
  instalados como comandos globales `parakeet-cli`, `whisper-server`, `piper` o
  `qwen3-tts-cli`; tampoco está instalado el módulo Python `pocket_tts`. Por lo
  tanto no hay una corrida acústica válida para reportar WER/CER, RTF, RAM/VRAM
  o p50/p90/p95 de producción.

## Resultado comparable

| Capacidad o métrica | LlamaCode productivo | Vellium / evidencia revisada | Resultado |
| --- | --- | --- | --- |
| STT residente y persistente | Whisper/Parakeet administrados, batch y NDJSON streaming; builders y parser pasan | El repositorio describe STT compatible con Whisper | **Empate funcional; sin WER comparable** |
| TTS residente | Piper JSON, Pocket TTS sidecar y endpoints HTTP administrados | El repositorio describe TTS streaming | **Empate funcional** |
| Streaming por oraciones/chunks | Implementado y cubierto por `test_voice` | Declarado como capacidad de voz en vivo | **Empate funcional** |
| Barge-in | VAD/PTT detiene playback y cancela el turno; lógica cubierta, hardware E2E pendiente | Declarado como parte de voz en vivo, sin latencia publicada | **LlamaCode tiene implementación; falta medir ms reales** |
| Métrica total de latencia | JSONL local hasta 500 muestras; p50/p90/p95 del fin de habla al primer audio | No se encontró corpus ni formato de benchmark equivalente | **LlamaCode tiene instrumentación más concreta** |
| Métricas por etapa | STT/LLM/útil/TTS: actualmente p50; faltan p90/p95 por etapa | No comparable | **Brecha pendiente de instrumentación** |
| WER/CER en español | No medido en esta máquina por falta de runtime/corpus | No publicado en la fuente revisada | **Pendiente para ambos** |
| RTF y recursos | No medidos en esta corrida | No publicados de forma reproducible | **Pendiente para ambos** |
| Qwen3-TTS residente | CLI por turno; no se cambia sin protocolo estable | No aporta un protocolo local reproducible que justifique migrarlo | **Mantener por turno** |

El repositorio oficial de Vellium se presenta como una aplicación local-first
con voz en vivo, STT compatible con Whisper y TTS en streaming, pero su README no
ofrece un corpus ni números reproducibles de WER, RTF, latencia o memoria que
permitan declararlo superior en el equipo local. Esto es una inferencia de la
documentación pública revisada, no una prueba negativa del software.

## Decisión

No se agrega Vellium como backend, no se descarga otro modelo y no se cambia el
default de Charla. Se conserva la arquitectura actual: Pocket TTS/Piper para
voz residente y de bajo consumo, Qwen3-TTS cuando hay margen, Parakeet/Whisper
para STT y endpoints HTTP persistentes cuando el usuario los configura.

La próxima medición válida debe instalar al menos un backend local gestionado,
crear el corpus español versionado y ejecutar 30 turnos fríos/calientes. Antes
de eso, los valores de WER/RTF/RAM/VRAM y las cifras acústicas quedan marcados
como **N/D**, no como cero.
