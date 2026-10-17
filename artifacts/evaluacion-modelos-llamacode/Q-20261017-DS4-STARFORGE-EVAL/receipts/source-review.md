# Revisión de fuentes — StarForge / sf-q3-8flash

Consulta: 2026-10-17 UTC. Se revisaron páginas públicas primarias de los
repositorios mantenedores y las secciones relevantes de la documentación local.
Las declaraciones de rendimiento y paridad son del proyecto, no mediciones
independientes de LlamaCode.

## Identidad y plataforma

- [StarForge README](https://github.com/Chida82/StarForge/blob/main/README.md):
  define un motor hijo por modelo, forks reducidos de `antirez/ds4`, GPU Metal
  solamente y desarrollo/pruebas en Apple M5 Max. Declara que el hijo
  `sf-q3-8flash` es Qwen3.8 Flash Next, servidor puerto 8004. El árbol padre
  contiene procedimientos de sync y paridad; no contiene el código de inferencia.
- [`sf-q3-8flash` README](https://github.com/Chida82/sf-q3-8flash/blob/main/README.md):
  model/backend productivo único Qwen3.8 (`qwen4exp`) sobre Apple Metal; el
  camino CPU se reserva para referencia y tests. Exige Apple Silicon, macOS,
  Xcode command-line tools y suficiente memoria. Q2: ~137,10 GiB en disco y
  41,73 GiB residentes; Q4: ~165,11 GiB en disco y 69,74 GiB residentes,
  además de buffers/contexto. El servidor expone OpenAI chat/completions y
  Responses, Anthropic Messages, streaming, batching y tool calls; no incluye
  `ds4-agent`, así que requiere un cliente externo.
- [Qwen3.8 Flash Next guide](https://github.com/Chida82/sf-q3-8flash/blob/main/docs/QWEN38_FLASH_NEXT.md):
  documenta arquitectura `qwen4exp`, MTP, visión Qwen3-VL, contexto nativo
  262.144 y YaRN opcional más allá del límite nativo, con advertencia de posible
  costo de calidad.

## Rendimiento y pruebas declaradas

- El README reporta mediciones únicamente en un Apple M5 Max de 128 GB. Compara
  el hijo contra `ds4` en el merge-base y fija misma GGUF, prompts y comandos.
  Para Q2 publica +4,9–11,8% prefill y +9,1–12,6% generación entre contextos
  2K–64K; CLI MTP +14,4%. Para Q4 publica +2,2–11,5% prefill, +0,5–8,1%
  generación y CLI MTP +10,4%. Los métodos descritos son dos corridas por
  build en orden ds4, hijo, hijo, ds4; el README no aporta muestras crudas de
  los datos de esa tabla en la página revisada.
- El README documenta paridad de tokens greedily contra upstream al merge-base,
  pruebas de identidad de MTP, verificaciones de logits byte-a-byte con
  `--bitwise`, A/A, pares ABBA, preheat de 210 s, control de frecuencia,
  intervalos bootstrap 95% y muestras con frecuencia, temperatura, potencia y
  token hash. El documento de velocidad describe el piso de ruido A/A y los
  criterios de pares válidos. Son afirmaciones/documentación del mantenedor.
- [`docs/upstream-prs.md`](https://github.com/Chida82/sf-q3-8flash/blob/main/docs/upstream-prs.md)
  registra optimizaciones de kernel/MTP/SSD seleccionadas y cambios descartados
  al medirlos, incluidos rechazos por regresión de velocidad o deriva numérica.
  Esto apoya que el incremento publicado se atribuye a optimizaciones para
  Metal/Qwen, no sólo a quitar backends; no demuestra portabilidad a CUDA.

## Encaje con LlamaCode

- [`docs/server-speed-benchmark.md`](../../../../docs/server-speed-benchmark.md)
  ya documenta A/A y comparación intercalada AB/BA, misma carga y seed, deltas
  pareados con IC 95%, perfil/hardware/flags con hash, PP/TG/TTFT/ITL,
  cold/warm, prefill y concurrencia.
- [`docs/kv-cache-qa.md`](../../../../docs/kv-cache-qa.md) ya permite
  configurar un `serverExe` distinto por brazo, parar/reiniciar runtimes,
  incluir A/A y retener comandos/logs/deltas para medir recuperación larga.
- StarForge añade dos controles más cercanos a verificación de motor: igualdad
  bitwise de logits y filtro de pares por frecuencia/térmica. El runner HTTP
  normal de LlamaCode no observa logits internos del servidor. Serían ideas
  condicionales para un benchmark de runtime con backend que exponga logits y
  telemetría por muestra, no una razón para cambiar ahora el harness general.

## Veredicto de fuentes

Hay evidencia técnica interesante para Qwen3.8 Flash Next en Apple Metal. La
especialización de modelo/kernel y el procedimiento de paridad son útiles como
referencia. El candidato no tiene backend Metal utilizable en el host Linux
RTX 3090, y las cifras no son transferibles como predicción de rendimiento ni
calidad para Strata/CUDA, vLLM o llama.cpp. No se encontró una brecha local que
justifique modificar perfiles o el benchmark existente.
