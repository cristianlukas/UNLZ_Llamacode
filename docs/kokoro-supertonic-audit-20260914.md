# Auditoría Kokoro + Supertonic para LlamaCode — 2026-09-14

## Resultado

El post describe una solución de texto-a-voz para lectura de documentos, no un
modelo LLM ni un perfil comparable con SOL, TERRA, GALACTA, MINI o los demás
perfiles de inferencia. No hay una mejora que deba entrar en la tabla de modelos
ni cambiar el default de lanzamiento.

## Soporte que ya existe en LlamaCode

LlamaCode ya contempla el caso de uso de voz en el modo Charla:

- TTS HTTP compatible con `/v1/audio/speech`.
- Modo `kokoro` a través de ese endpoint, con streaming PCM incremental.
- Piper local como fallback administrado.
- Pocket TTS local sobre CPU.
- Qwen3-TTS e Inflect como motores locales opcionales.
- Métricas de latencia de voz y fallback automático si cae el endpoint.

Por lo tanto, Kokoro no requiere un nuevo perfil de LLM para ser usado: puede
configurarse como proveedor HTTP local. Supertonic no tiene todavía una ruta de
integración administrada en la aplicación.

## Verificación local

| Verificación | Resultado |
|---|---|
| Modelos Kokoro en `/media/cristian/7CFE1E0FFE1DC1F6/models` | No encontrados |
| Modelos Supertonic en los discos de modelos | No encontrados |
| Servidor Kokoro/Supertonic activo | No encontrado |
| `ttsMode=kokoro` en el cliente | Ya soportado como endpoint HTTP |
| Audio PCM incremental | Ya soportado por `TtsEngine`/`VoiceController` |
| Suite local `test_voice` | **41/41 aprobadas** |
| Piper administrado | Soportado y usado como fallback |
| Pocket TTS | Soportado, con auto-enable conservador |

La instalación de `kokoro_onnx` observada en una ruta de AppData corresponde a
un entorno Windows; no contiene el modelo ni es un runtime Linux utilizable por
esta instancia.

## Comparación conceptual

| Motor | Ventaja probable | Limitación para promoverlo ahora |
|---|---|---|
| Kokoro | Muy buena calidad/velocidad en inglés; bajo tamaño | El post no mide español ni nuestro hardware; falta modelo/endpoint local |
| Supertonic | Alternativa multilingüe y posiblemente mejor fallback que Piper | No integrado, sin artefacto local ni medición de latencia/calidad |
| Piper actual | Bajo consumo, fallback robusto y administrado | Calidad más sintética que Kokoro en inglés |
| Pocket TTS | CPU, multilingüe, no consume VRAM del LLM | Calidad/latencia deben evaluarse por voz y texto |
| Qwen3-TTS | Calidad y control de estilo superiores cuando hay VRAM | Consume GPU compartida con el LLM |

El post tampoco aporta una prueba objetiva contra Piper/Pocket/Qwen3-TTS: las
afirmaciones son auditivas y dependen de idioma, voz, texto y configuración.

## Decisión

No se descargaron modelos ni se cambió el default. Descargar Kokoro o instalar
Supertonic sólo tendría sentido como una campaña separada de Charla, midiendo:

1. tiempo hasta primer audio y tiempo real total;
2. calidad de pronunciación en español e inglés;
3. consumo de RAM/VRAM mientras SOL está activo;
4. cancelación/barge-in y streaming PCM;
5. fallback al detener el servidor.

La aplicación ya está preparada para aceptar Kokoro mediante HTTP. Si más
adelante se dispone de un servidor local Kokoro estable y se demuestra menor
latencia/mejor calidad que el motor seleccionado por `auto`, se puede agregar
una recomendación específica de TTS sin tocar el ranking de perfiles LLM.
