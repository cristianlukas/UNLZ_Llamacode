# Whallm/Qwen3.8 Flash-Next — auditoría de streaming SSD

Fecha: 2026-09-14  
Equipo LlamaCode: Ubuntu, 2× RTX 3090, P2P disponible y ~123 GiB de RAM

## Evaluación

Whallm es una aplicación nativa para macOS/Apple Silicon que transmite un
checkpoint de Qwen3.8-Flash-Next de aproximadamente 125 GB desde SSD. El autor
reporta cerca de 60 tok/s de prefill y 8 tok/s de decode usando unos 20 GB de
memoria unificada, con chat, thinking, tool calls, prompt cache y API
compatible con OpenAI.

La solución es valiosa para demostrar que el modelo puede ejecutarse con poca
memoria mediante streaming, pero no es transferible directamente a nuestro
entorno: usa Metal, memoria unificada, kernels Apple y un empaquetado propio.
No es una configuración CUDA para SM86 ni aporta un artefacto GGUF/runner que
podamos integrar en LlamaCode.

## Comparación con nuestras pruebas

| Variante | Prefill/decode | Contexto | Calidad/estabilidad | Decisión |
|---|---:|---:|---|---|
| Whallm publicado | ~60 / 8 tok/s | No detallado en el extracto | Tool calls declarados, sin BCB comparable | No transferible |
| ASTRA local, control | ~16–41 tok/s de decode según contexto | 196K | Calidad agéntica no validada | Experimental |
| ASTRA `lazy on` | TPS bruto mayor | 32K probado | Salida corrupta `////` | Rechazado |
| ASTRA `lazy on-direct` | ~7,54 tok/s | 32K | Salida válida, pero más lento | No promover |
| BeeLlama KVarN5 | ~36 tok/s a 131K | 131K probado | JSON, Python, tool-call y needle válidos | Mejor alternativa Flash-Next local |
| SOL | 74 narrativo / 102 código | 262K validado | BCB 8/8 y tool-use OK | Default |

## Ideas reutilizables

- El prompt cache es importante para sesiones agenticas largas, pero el efecto
  debe medirse dentro del backend CUDA que usamos.
- MTP puede mejorar el decode; nuestras variantes MTP de Flash-Next todavía no
  obtuvieron una combinación estable de drafter, caché de expertos y salida.
- El streaming SSD es una solución de capacidad, no una mejora de velocidad
  frente a modelos que ya caben mejor en VRAM/RAM.

No se descargó el checkpoint de ~125 GB: no hay artefacto CUDA compatible y el
espacio disponible para modelos es limitado. No se cambia SOL, ASTRA ni
BeeLlama KVarN5.

