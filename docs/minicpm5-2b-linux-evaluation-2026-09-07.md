# Evaluación de MiniCPM5-2B en Ubuntu — 2026-09-07

## Resultado

Se descargó el GGUF oficial `MiniCPM5-2B-Q4_K_M.gguf` en:

`/media/cristian/Disco local/Models/llamacpp/MiniCPM5-2B-GGUF/`

El modelo inicia correctamente con el `llama-server` CUDA administrado por LlamaCode y quedó disponible como perfil opcional:

- **MINI — MiniCPM5-2B · auxiliar rápido · 131K**
- Q4_K_M, contexto configurado de 131072 tokens, F16/Q8 KV según el backend, Flash Attention y dos RTX 3090.
- Perfil Linux; no modifica ni reemplaza perfiles Windows.

## Pruebas

| Prueba | Resultado |
| --- | ---: |
| Smoke test por LlamaCode | Correcto |
| Server Speed de LlamaCode | ~250,45 tok/s decode medio |
| HumanEval inicial | 1/1 |
| HumanEval completo | 20/20; 18/20 en primer intento, 2 reparados |
| BigCodeBench-Hard | 1/8; no pasa tras dos reparaciones |
| VRAM usada | ~7,3 GiB totales; reparto balanceado |

Como control directo con el mismo prompt corto, `Qwen3.5-2B-Q4_K_M` obtuvo aproximadamente 297 tok/s, por lo que MiniCPM5-2B no es la opción más rápida entre los modelos 2B instalados. Su ventaja práctica es el bajo consumo y la latencia muy baja frente a los modelos grandes, no una mejora de calidad para coding.

## Decisión

Se conserva como perfil auxiliar para chat breve, clasificación, resúmenes, tareas livianas y subagentes de bajo costo. No se promueve a ASTRA, SOL, TERRA, LUNA ni METEOR, y no se recomienda como agente principal de coding: el resultado BCB de 1/8 queda muy por debajo de los perfiles principales.

La configuración sigue la compatibilidad oficial de MiniCPM5-2B con GGUF y llama.cpp:

- https://huggingface.co/openbmb/MiniCPM5-2B-GGUF
- https://github.com/OpenBMB/MiniCPM/blob/main/docs/deployment/llama_cpp.md
