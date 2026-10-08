# Auditoría `audio.cpp` — 2026-09-18

## Veredicto

`audio.cpp` es útil para LlamaCode como backend local de audio para Ingi Charla:
ofrece servidores OpenAI-compatibles para TTS (`/v1/audio/speech`) y STT
(`/v1/audio/transcriptions`). No es un perfil LLM y no aporta métricas PP/TG,
BCB o HE para SOL, por lo que no cambia la tabla de modelos ni el default SOL.

Referencia: [repositorio oficial de audio.cpp](https://github.com/0xShug0/audio.cpp).

## Validación local

Se auditó el commit `518550862785bc46d482517643001a6165170135` y se compiló una
build CUDA real con:

- CUDA habilitado, arquitectura `SM86` y CUDA Graphs.
- Modelos seleccionados: `qwen3_tts`, `qwen3_asr`, `pocket_tts` y
  `parakeet_tdt`; el runtime también enlazó `qwen3_forced_aligner`.
- `audiocpp_cli` y `audiocpp_server` compilados correctamente: **434/434 pasos
  Ninja** en la build CUDA SM86 reproducida.
- `audiocpp_cli --help`: correcto.
- `audiocpp_server --help`: correcto.
- `audiocpp_cli --list-devices`: detectó las dos RTX 3090 de 24 GB y el Ryzen
  9 9950X3D.

La primera pasada no descargó pesos; la comparación posterior sí descargó en
Disco D los paquetes Q8 de Qwen3 TTS (1,99 GB), Qwen3 ASR (1,15 GB), Parakeet
TDT (0,92 GB) y Pocket TTS español (0,13 GB). El checkout y los artefactos de
prueba ocupan aproximadamente 6,7 GB.

## Resultados reproducibles en las RTX 3090

Equipo: Ubuntu, dos RTX 3090, CUDA SM86, commit `5185508`, texto/voz de prueba
fijos, tres consultas calientes cuando se indica. `RTF` es `tiempo de pared /
duración del audio`.

### STT

| Backend | Ruta | Audio | Tiempo / RTF | Resultado de calidad |
| --- | --- | ---: | ---: | --- |
| Qwen3 ASR Q8 | CLI CUDA, proceso nuevo | 14,2 s | 1,03–1,25 s; **RTF 0,073–0,088** | Texto exacto en 2/2 muestras |
| Qwen3 ASR Q8 | servidor residente | 14,2 s | 0,30–0,32 s; **RTF 0,021–0,024** | Igual, sin errores en 2/2 muestras |
| Parakeet TDT Q8 | CLI CUDA, proceso nuevo | 14,2 s | 1,10–1,12 s | Igual, sin errores en 2/2 muestras |
| Parakeet TDT Q8 | servidor residente | 14,2 s | 0,040–0,044 s; **RTF 0,0028–0,0031** | Igual, sin errores en 2/2 muestras |

El corpus fue inglés limpio, por lo que esto **no equivale a WER/CER en
español**. En las dos muestras la normalización alfanumérica dio 0/2 errores
para ambos modelos. Falta el corpus español versionado para promover una
decisión de calidad lingüística.

### TTS

| Backend | Ruta | Duración generada | Tiempo | RTF | Observación |
| --- | --- | ---: | ---: | ---: | --- |
| Qwen3 TTS Base Q8 | CLI CUDA, proceso nuevo | 11,52 s | 4,86 s | **0,42** | Clonación inglesa funcional; la variante 0,6B rechaza `es` explícito |
| Qwen3 TTS Base Q8 | servidor residente | 3,20–4,08 s | 0,63–0,73 s caliente | **0,18–0,23** | Compatible con `/v1/audio/speech`; carga fría 5,70 s |
| Pocket TTS español Q8 | CLI CUDA con WAV de referencia | 6,40 s | 0,72 s | **0,11** | Síntesis española funcional |
| Pocket TTS español Q8 | servidor residente | 5,76–6,48 s | 0,11 s caliente | **0,017–0,019** | Muy rápido, pero consume GPU en esta ruta |

El paquete Pocket TTS español descargado no contiene el embedding `alba` que
su metadata sugiere; `--voice-id alba` falla. La síntesis funciona con
`--voice-ref`, por lo que no se debe activar esa voz incorporada en Charla sin
corregir el paquete o descargar un embedding compatible.

### Memoria observada

Con el servidor y `max_loaded_models: 1`, el proceso llegó aproximadamente a
**2,0 GB RSS / 844 MiB VRAM** con Pocket TTS, **3,68 GB RSS / 4,21 GB VRAM**
con Qwen3 TTS y **2,29 GB RSS / 1,81 GB VRAM** con Qwen3 ASR. El límite de un
modelo residente evita mantener simultáneamente todas esas reservas.

## Compatibilidad con LlamaCode

La integración no necesita código nuevo: Charla ya tiene un modo HTTP genérico
que envía el contrato OpenAI-compatible de audio para TTS y multipart para STT.
La configuración experimental recomendada es:

```text
TTS mode: http
TTS base URL: http://127.0.0.1:8080
TTS model: <modelo cargado por audio.cpp>
TTS format: wav

STT provider: local
STT base URL: http://127.0.0.1:8080
STT endpoint: /v1/audio/transcriptions
STT model: <modelo cargado por audio.cpp>
```

El servidor debe iniciarse sólo cuando Charla lo necesite. Para evitar acumular
modelos en las dos GPU conviene usar carga diferida y limitar a un modelo
residente (`lazy_load` y `max_loaded_models: 1`, según la configuración del
servidor). No se agregó un autostart permanente.

## Candidatos y estado

| Función | Candidato | Resultado | Decisión |
| --- | --- | --- | --- |
| TTS | `qwen3_tts` | Clonación funcional, servidor residente y RTF 0,18–0,23 | Mantener como backend experimental HTTP; no default todavía |
| TTS | `pocket_tts` | RTF 0,017–0,019 caliente en GPU; metadata española incompleta | No reemplaza aún el Pocket TTS residente actual; corregir paquete/voz |
| STT | `qwen3_asr` | RTF 0,021–0,024 residente; exacto en 2/2 muestras inglesas | Candidato HTTP, calidad española pendiente |
| STT | `parakeet_tdt` | RTF 0,0028–0,0031 residente; exacto en 2/2 muestras | Mejor candidato de baja latencia; confirmar corpus español |
| Alineación | `qwen3_forced_aligner` | Enlazado, no medido con pesos | No promover hasta medir utilidad real |

No se modificaron SOL, GALACTA ni los demás perfiles LLM. Tampoco se reemplazó
Pocket TTS, Piper, Kokoro o Parakeet: faltan pruebas con pesos reales.

## Qué queda pendiente

La comparación base ya fue ejecutada. Para cerrar promoción productiva falta
comparar contra los runtimes administrados reales de Charla —Piper, Pocket TTS,
Whisper y Parakeet— usando:

1. tiempo hasta el primer audio y RTF en español e inglés;
2. p50/p90 de latencia y consumo pico de VRAM/RAM;
3. WER/CER de STT sobre el mismo conjunto de grabaciones;
4. naturalidad, pronunciación y estabilidad de TTS;
5. cancelación, interrupción y liberación de memoria al cambiar de modelo.

Sólo si conserva esta ventaja con 30 repeticiones, corpus español y barge-in
real se agregará como opción visible o default de Charla. Por ahora no se
modifica SOL, la tabla de modelos LLM ni el default de Ingi Charla.
