# Qwen3.8 Flash-Next: benchmark MLX frente a LlamaCode/CUDA — 2026-09-07

## Qué aporta la publicación

Los resultados de 25–45 tok/s son una referencia válida para Apple Silicon,
pero no son comparables directamente con las dos RTX 3090 de esta PC. El
artefacto enlazado es una conversión **MLX safetensors** con un bloque MTP
nativo de `qwen4_exp`; su propia ficha indica que requiere un runtime MLX/oMLX
que construya ese módulo y que no debe recibir un drafter Qwen3.8-27B ajeno.

Por lo tanto no se puede instalar ese repositorio como un perfil CUDA/GGUF de
LlamaCode ni reutilizarlo como el head MTP de ASTRA.

## Estado local

- ASTRA conserva el GGUF Flash-Next UD-Q4_K_XL, cache experto 188, expertos en
  RAM y contexto 196K.
- El head GGUF local de 2,79 GB está presente, pero la prueba previa de
  `ASTRA + MTP` no llegó a iniciar de forma estable en el backend actual.
- ASTRA + NGRAM tampoco obtuvo una carga práctica ni calidad BCB válida.
- ASTRA queda sin drafter activo, como perfil experimental de capacidad y
  contexto; no se cambia SOL/TERRA/LUNA/METEOR.

## Decisión de implementación

No se descarga la conversión MLX ni se agrega un perfil falso. El catálogo ya
mantiene ASTRA y sus variantes de benchmark separadas, y el código conserva la
distinción entre plataforma Linux/CUDA y cualquier futura integración MLX.

Si en el futuro se quiere explotar esa conversión, debe hacerse mediante un
backend MLX/oMLX independiente, con su propio modelo, runtime, métricas y
perfil de plataforma; no mezclando pesos o drafter con llama.cpp.

El agregador utilizado por la publicación declara que mide velocidad y calidad
en escenarios de código, razonamiento y uso real, pero sus corridas siguen
siendo evidencia externa: para promover un perfil en LlamaCode se exige la
cadena local HE0 → HE20 → BCB y una medición de TTFT/prefill/decode.

Referencia: [conversión MLX Qwen3.8 Flash-Next oQ6-MTP](https://huggingface.co/Vontra/Qwen3.8-Flash-Next-MLX-oQ6-MTP),
[llm-bench.io](https://llm-bench.io/).
