# Qwen3.8: peso del modelo frente a cuantización KV — 2026-09-07

## Resultado para LlamaCode

La discusión propone comparar Q4/Q5 con KV F16/Q8 para contextos cercanos a
200K. La idea es pertinente como experimento de contexto largo, pero no es una
mejora automática del perfil diario: al subir de Q4 a Q5 se gana margen de
calidad potencial y se pierde memoria para KV, MTP y visión.

El catálogo local ya contiene:

- Qwen3.8-27B Q5_K_M con MTP y visión a 131K.
- Variantes Q5 con K/V `q8_0`, MTP2/3/4 y batches distintos.
- Una variante experimental Q5/KV8 a 262K inspirada en la receta publicada.

Se intentó iniciar `sys-bench-qwen38-q5km-post-262k-kv8` en Ubuntu. El perfil
fue rechazado antes de cargar porque quedó sin binario seleccionado; por lo
tanto no existe una medición nueva de TPS ni una base para promoverlo. La
variante permanece fuera de la cola diaria. TERRA se restauró después y quedó
operativo con su configuración validada.

## Decisión

No se cambia ASTRA, SOL, TERRA, LUNA ni METEOR. Tampoco se reemplaza el Qwen
28B diario por Q5: las campañas anteriores de Q5 fueron más lentas y tuvieron
BCB parcial, mientras que SOL/TERRA conservan BCB 8/8 con mayor velocidad.

Para una futura campaña específica de contexto largo, el orden razonable es:

1. Q4/KV Q8 como referencia de capacidad y velocidad.
2. Q5/KV Q8 a 131K o 196K, con MTP conservador, si el binario compatible está
   seleccionado y la carga deja margen para la visión.
3. Q5/KV F16 sólo como control de calidad, no como configuración por defecto.

El resultado debe cerrarse con la misma cadena HE0 → HE20 → BCB y con TTFT,
prefill, decode, VRAM, RAM y estabilidad registrados. Un arranque exitoso a
200K por sí solo no demuestra que sea mejor para el harness.
