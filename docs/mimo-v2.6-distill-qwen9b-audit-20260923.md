# MiMo-V2.6-Distill-Qwen-9B — auditoría local

Fecha: 2026-09-23.

Se descargó y probó temporalmente `MiMo-V2.6-Distill-Qwen-9B-Q4_K_M.gguf`
junto con su `mmproj` BF16. Después de la comparación, ambos artefactos fueron
eliminados y no se integró un perfil nuevo en LlamaCode.

## Configuración

- Runtime: llama.cpp adaptive build `c28d538`.
- Hardware: una RTX 3090 de 24 GB, CUDA; se usó la misma GPU para el A/B.
- Cuantización: Q4_K_M; KV `q4_0`; Flash Attention; `n_gpu_layers=-1`.
- Contexto: 32K; batch/ubatch 512; `parallel=1`; reasoning off.
- Muestreo de calidad: temperatura 0.6, top-p 0.95.
- Sin speculative decoding/MTP para mantener comparable el A/B directo.

## Resultados

| Modelo | Prefill | Decode | HumanEval-20 |
|---|---:|---:|---:|
| Qwen3.5-9B Q4_K_M | 3355 tok/s | 99.8 tok/s | **19/20** |
| MiMo-V2.6-Distill-Qwen-9B Q4_K_M | 3374 tok/s | 102.9 tok/s | **16/20** |

Como referencia de velocidad auxiliar, Qwen3.5-4B midió aproximadamente 171.3
tok/s de decode. El perfil Qwen3.5-9B con MTP documentado para LlamaCode ronda
166.1 tok/s, por lo que MiMo no supera la configuración productiva existente.

También se ejecutó un smoke directo de BigCodeBench Hard de 8 tareas: MiMo dio
2/8 y Qwen 1/8. Esa cifra no se considera decisiva porque varias tareas
dependieron de un entorno local con incompatibilidad NumPy 1.x/2.x y
Pandas/NumExpr; no fue una corrida LC-H1 completa.

## Decisión

MiMo mostró sólo una ventaja marginal de aproximadamente 3% en decode frente al
Qwen3.5-9B base, pero perdió calidad en HumanEval y quedó por debajo del perfil
Qwen con MTP. No se recomienda reemplazar Qwen ni conservar los pesos locales.

Fuentes del modelo: [model card oficial](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Distill-Qwen-9B) y [GGUF usado](https://huggingface.co/bartowski/MiMo-V2.6-Distill-Qwen-9B-GGUF).
