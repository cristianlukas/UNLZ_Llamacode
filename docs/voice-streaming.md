# STT streaming y Parakeet

LlamaCode conserva dos transportes de STT:

- `http_batch`: el contrato OpenAI-compatible existente. Es la ruta estable para
  whisper.cpp, servicios cloud y cualquier endpoint `/v1/audio/transcriptions`.
- `stream_process`: una sesión persistente administrada por la app. El audio se
  envía como PCM16 mono 16 kHz por stdin y el sidecar responde mensajes NDJSON
  por stdout.

## Protocolo NDJSON v1

La app envía una línea de configuración por sesión:

```json
{"type":"config","sample_rate":16000,"language":"es","model":"..."}
```

Después envía bloques de audio. `sequence` es monotónico por sesión y sirve para
diagnóstico; el sidecar no debe asumir que los números son un reloj de audio:

```json
{"type":"audio","sequence":1,"pcm16_base64":"..."}
```

El sidecar puede emitir el prefijo completo revisado varias veces:

```json
{"type":"partial","text":"quiero abrir"}
{"type":"partial","text":"quiero abrir el navegador"}
```

Al terminar, la app envía `{"type":"end"}` y espera:

```json
{"type":"final","text":"quiero abrir el navegador"}
```

`{"type":"cancel"}` invalida la sesión actual. Los resultados que lleguen
después de una cancelación se descartan. El proceso se lanza sin shell, recibe
las variables `LLAMACODE_STT_*`, hereda la máscara CUDA de voz y queda dentro del
Job Object de LlamaCode.

## Parakeet experimental

El catálogo incluye `parakeet-tdt-0.6b-v3`. No se descarga automáticamente porque
el modelo necesita un runtime neuronal externo y una conversión/instalación que
depende del entorno. El adapter incluido en
`tools/parakeet_stt_sidecar.py` usa NeMo sobre el audio acumulado para producir
parciales rolling. Es una integración experimental de calidad y latencia; no es
un decoder TDT stateful de streaming.

Instalación orientativa en un entorno Python separado:

```powershell
python -m pip install numpy "nemo_toolkit[asr]"
```

Luego seleccionar en Charla el motor Parakeet y configurar:

```text
Comando: python
Argumentos: ["tools/parakeet_stt_sidecar.py", "--model", "nvidia/parakeet-tdt-0.6b-v3"]
```

También se puede usar un `.nemo` local:

```text
["tools/parakeet_stt_sidecar.py", "--model-path", "C:/models/parakeet.nemo", "--device", "cuda"]
```

El modelo oficial Parakeet TDT v3 anuncia soporte multilingüe, incluido español.
Antes de convertirlo en default hay que comparar WER/CER, p50/p90 y VRAM contra
Whisper base con el mismo corpus y hardware.

## Diagnóstico

Las métricas locales conservan `endpointReason`, el primer texto del LLM, el
primer texto útil y el primer audio enviado al dispositivo. `firstAudioQueued` es
un proxy de reproducción; no equivale a una medición acústica del parlante.
Para comparar motores se debe mirar fin de habla → primer audio útil, no sólo
TTFT o tokens por segundo.

El transporte batch sigue siendo el fallback recomendado si el sidecar no está
instalado, si NeMo no arranca o si se necesita una ruta cloud.
