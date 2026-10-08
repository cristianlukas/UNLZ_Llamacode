# Auditoría DeepSeek-V4.1-Flash — 2026-09-14

## Resultado ejecutivo

DeepSeek-V4.1-Flash no es ejecutable en nuestra configuración actual y no supera a ningún perfil local validado. No se descargaron pesos ni se modificó el perfil predeterminado.

## Compatibilidad comprobada

| Elemento | Estado |
|---|---|
| RAM disponible | 123 GiB instalados; 113 GiB disponibles en la medición |
| VRAM | 2 × 24 GiB RTX 3090 |
| Espacio libre en la partición de modelos | ~40 GB |
| GGUF Q2 mínimo localizado | ~246 GB; 7 shards |
| GGUF Q3 localizado | ~323 GB |
| GGUF Q4 localizado | ~445 GB |
| Runtime llama.cpp CUDA actual | Sin arquitectura `deepseek41`, DSpark o Engram |
| vLLM Python local | No instalado |
| Imagen vLLM disponible | `vllm/vllm-openai:v0.27.1`, sin soporte dedicado V4.1 |
| Imagen dedicada requerida | `vllm/vllm-openai:deepseekv41-flash-0909` |

El Q2 de ~246 GB ya supera por sí solo la memoria combinada de RAM y VRAM, sin contar runtime, buffers, sistema operativo ni KV. Con los ~40 GB libres tampoco es posible descargarlo para una prueba parcial. Por seguridad no se inició una descarga incompleta.

## Qué sí aporta la propuesta

- Arquitectura Causal Encoder-Decoder para reducir el coste de prefill.
- 8B activos por token de entrada y 16B durante decode.
- Contexto declarado de 1M tokens.
- KV especializado FP4 de aproximadamente 890 bytes por token.
- Visión nativa y DSpark como speculative decoding.

Estas ventajas requieren soporte específico del modelo. No se pueden obtener activando `--cache-type-k q8_0` en los perfiles actuales: el FP4 KV de V4.1 no es el KV Q8 de llama.cpp y la arquitectura tampoco coincide con DeepSeek V4 anterior.

## Comparación con LlamaCode

| Perfil | Evidencia local | Decisión |
|---|---|---|
| SOL | BCB 8/8, tool-use OK, 74 narrativo / 102 código | Mantener como default |
| GALACTA | DeepSeek V4 anterior, BCB 8/8, ~9,65 tok/s | Mantener como calidad local validada |
| CyberTiel | MTP3, visión, ~183 tok/s código smoke, contexto largo probado | Experimental; todavía sin BCB |
| DeepSeek-V4.1-Flash | Sin ejecución local posible | No agregar |

La comparación publicada de benchmarks no sustituye HE/BCB en nuestra máquina: el propio recipe oficial apunta a hardware H200/GB200/GB300/MI350X y a una imagen vLLM específica, no a dual RTX 3090. El soporte local alternativo encontrado usa un fork experimental de llama.cpp y un GGUF de ~502 GB, también fuera de nuestro almacenamiento y memoria.

## Decisión

No se agrega perfil, no se cambia SOL y no se modifica el dropdown. Se deja registrado como candidato futuro sólo si aparece una variante realmente comprimida por debajo de la memoria disponible y soporte `deepseek41` estable para CUDA/RTX 3090.
