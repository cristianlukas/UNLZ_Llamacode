# Auditoría de la receta de voz local para Ingi Charla

Fecha: 2026-09-18  
Fuente revisada: publicación sobre un asistente local con Qwen3.5-9B, Qwen3
ASR 1.7B y Pocket TTS.

## Conclusión

La publicación no aporta un modelo de lenguaje superior a los perfiles de
LlamaCode. Sí confirma una arquitectura útil para **Ingi Charla**: STT local,
LLM pequeño con respuestas acotadas, TTS local residente y procesamiento por
oraciones. Esa arquitectura ya está implementada en LlamaCode, con algunas
ventajas adicionales: Parakeet administrado, VAD adaptativo, barge-in, PTT,
streaming NDJSON y métricas p50/p90/p95.

No se cambió el perfil principal ni se descargaron modelos nuevos.

## Comparación con lo que ya tenemos

| Componente de la publicación | LlamaCode actual | Decisión |
|---|---|---|
| Qwen3.5-9B Q4 para el diálogo | Perfil `[agente/visión] 8GB · Qwen3.5 9B MTP` con MTP3, visión y 32K | Mantener; ya está validado localmente |
| Qwen3 1.7B ASR | No está integrado como backend de STT | No agregarlo sin corpus A/B; el tamaño del modelo no demuestra menor latencia ni mejor WER |
| Pocket TTS | Sidecar local persistente, CPU, español y streaming WAV PCM16 | Ya integrado; mantener opt-in hasta medir en el equipo |
| Parakeet TDT v3 | Modelo GGUF Q4 de ~356 MB, `parakeet-cli` administrado y ruta `process_batch` | Mantener como STT local experimental y fallback de baja memoria |
| Chunking de audio | Captura PCM16 16 kHz, segmentos incrementales y protocolo `stream_process` NDJSON v1 | Ya implementado |
| TTS por oraciones superpuestas | Separación de oraciones y generación/reproducción incremental | Ya implementado |

## Validaciones realizadas

La prueba nativa de Charla disponible en el build Linux pasó completa:

- `TestVoice`: **41/41 aprobadas**.
- Configuración y round-trip JSON.
- STT multipart, parser de transcripción y protocolo streaming.
- Parser y argumentos de Parakeet.
- Selección de TTS Qwen3, Pocket TTS, Piper e Inflect.
- VAD adaptativo, histéresis, hangover y detector de turnos.
- Barge-in, separación de oraciones y streaming de TTS.
- Métricas de latencia y percentiles.
- Política de capacidad del agente para Qwen3.5-2B, 9B y MoE.

El perfil Qwen3.5-9B ya tiene estas referencias locales:

- 106,1 tok/s sin MTP y 166,1 tok/s con MTP.
- Visión funcional.
- Perfil Q4_K_M de aproximadamente 5,5–5,7 GB.
- Contexto de Charla deliberadamente limitado a 32K para preservar latencia y
  memoria del diálogo de voz.

## Estado de los runtimes en esta máquina

En la sesión de validación no están instalados como comandos globales
`parakeet-cli`, `whisper-server`, `piper` ni `qwen3-tts-cli`; tampoco está
instalado el módulo Python `pocket_tts` en el intérprete del sistema. Esto no es
un fallo de LlamaCode: son componentes gestionados que se instalan desde la
pantalla de Charla y quedan aislados bajo los datos locales de la aplicación.

La prueba de código valida los builders y políticas, no la calidad acústica de
un audio real. Para promover un motor de voz falta una comparación controlada
con el mismo corpus en español, midiendo WER/CER, fin de habla → primera
transcripción, fin de habla → primer audio, p50/p90 y uso de CPU/RAM/VRAM.

## Mejoras que sí se conservan

1. **Qwen3.5-9B** queda como LLM recomendado para Charla cuando se prioriza
   calidad agentiva y visión con recursos moderados.
2. **Pocket TTS** se mantiene como opción CPU residente para no quitar VRAM al
   LLM; `pocketAutoEnable` permanece desactivado hasta disponer de una medición
   acústica local.
3. **Parakeet** permanece seleccionable para STT local compacto; Whisper sigue
   como fallback estable.
4. La reproducción por oraciones, el barge-in y las métricas de latencia no se
   reemplazan por la receta externa porque ya cubren el mismo objetivo con más
   control.

## No promovido

No se agrega Qwen3-ASR 1.7B como perfil ni como default: la publicación no
incluye WER, latencia reproducible ni consumo comparable contra el Parakeet y
Whisper que LlamaCode ya administra. Incorporarlo ahora duplicaría runtimes sin
evidencia de mejora.

