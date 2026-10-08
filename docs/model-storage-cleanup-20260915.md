# Limpieza de modelos — 2026-09-15

## Resultado

Se revisaron los modelos descargados en las particiones montadas:

- `/media/cristian/Disco local`
- `/media/cristian/7CFE1E0FFE1DC1F6`
- `/media/cristian/HDD extra`

No había procesos `llama-server`, `vLLM` ni `NInfer` activos durante la operación.

La eliminación permanente estuvo bloqueada por la protección del entorno contra `rm -rf`. Para no perder artefactos recuperables, los candidatos se retiraron de sus carpetas activas y se movieron a:

`/media/cristian/HDD extra/LlamaCode-removed-models-20260915`

El traslado liberó aproximadamente **282 GB** en las particiones de modelos. La cuarentena contiene los archivos completos y puede eliminarse más adelante si se confirma que no hacen falta.

## Retirados

| Artefacto | Tamaño aprox. | Motivo |
|---|---:|---|
| `LlamaCode-quarantine-deepseek` | 138 GB | Fragmentos corruptos/incompletos; no forman un modelo utilizable. |
| `Qwen3.8-Flash-Next-REAP320-Q3` | 65 GB | BCB 1/8, sin MTP funcional, no promovido; ASTRA/IQ1 cubren la línea de contexto largo. |
| `Swift-Qwen3.8-27B-GGUF` (dos copias) | 36 GB | BCB 1/8; no está en el catálogo activo y SOL lo supera como agente. |
| `Qwen3.8-27B-ATX-IQ4_XS-M` | 15 GB | BCB 1/8; experimental, no promovido y sin ventaja operativa suficiente. |
| `K2-Horizon-7B-GGUF` | 15 GB | BCB 0–2/8; inferior a MINI/Qwen3.5 para tareas auxiliares. |
| `Qwen3.8-27B-EXL3-SC-3.00bpw-H4-V4` | 13 GB | BCB 1/8; backend experimental y no usado por los perfiles activos. |
| `Ling-3.0-tiny-abliterated-APEX-GGUF` | 3,8 GB | Variante histórica; LUNA usa `ling-3.0-tiny-test`. |

## Conservados deliberadamente

- SOL / AutoRound INT4.
- GALACTA y DeepSeek Fusion.
- ASTRA Qwen3.8 Flash-Next Q4.
- QWEN35-A3B, QWEN38-Q8, TERRA, LUNA y MINI.
- NINFER-QWEN38, incluyendo el artefacto histórico requerido por Linux.
- Qwen3.8 Q4 con `mmproj`, usado por perfiles experimentales de visión/fallback.
- CyberTiel, porque conserva una ruta experimental única de visión y concurrencia.
- IQ1_S, porque es el candidato experimental de bajo peso/contexto largo más reciente.
- Qwen3.5-9B/4B/2B, porque siguen presentes en perfiles generales del catálogo.

## Espacio posterior

Después de retirar los orígenes, el espacio libre quedó aproximadamente en:

| Partición | Libre |
|---|---:|
| `Disco local` | 259 GB |
| `7CFE1E0FFE1DC1F6` | 195 GB |
| `HDD extra` | 52 GB |

La cuarentena ocupa el espacio del HDD extra; no se borró permanentemente para conservar una vía de recuperación.
