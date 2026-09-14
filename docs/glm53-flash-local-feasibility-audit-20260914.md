# Auditoría de factibilidad local de GLM-5.3-Flash — 2026-09-14

## Resultado

GLM-5.3-Flash es un candidato interesante para una futura máquina o backend,
pero no es incorporable hoy a los perfiles locales de LlamaCode.

La ficha oficial lo describe como un modelo multimodal de aproximadamente
320B parámetros totales y 18B activos, con despliegue documentado para
SGLang, vLLM, TokenSpeed, Transformers, KTransformers y Unsloth. La publicación
de Reddit no aporta una medición reproducible en nuestras dos RTX 3090.

## Verificaciones en esta PC

| Verificación | Resultado |
| --- | --- |
| GPUs | 2 × RTX 3090, SM 8.6, 24 GiB cada una |
| VRAM combinada | 48 GiB |
| RAM disponible para inferencia | aproximadamente 128 GiB |
| Pesos GLM-5.3-Flash locales | No encontrados |
| Cuantización GLM local | No encontrada |
| Perfil LlamaCode existente | No |
| Imagen vLLM local `0.27.1` | No contiene implementación GLM5/GLM5Next |
| LayerStoRm | No compatible: requiere SM120/RTX 50xx |

El inventario sólo contiene fuentes y conversiones relacionadas con GLM-5.2,
no un artefacto GLM-5.3-Flash listo para cargar. Los GGUF publicados para este
modelo aparecen como variantes de más de 300B parámetros; no se descargó ninguno
porque no hay una ruta validada para ejecutarlo en SM86 y el espacio local es
limitado.

## Comparación con nuestros perfiles

| Perfil local | Evidencia actual | Decisión |
| --- | --- | --- |
| SOL | Qwen3.8 TP2/P2P + MTP4, 74 tok/s narrativo / 102 código, BCB 8/8, tool-use OK | Mantener default |
| GALACTA | DeepSeek V4 Flash, BCB 8/8, ~9,65 tok/s | Mantener como calidad máxima local |
| TERRA/LUNA/METEOR | Perfiles locales ya probados con otros modelos | No reemplazar sin benchmark comparable |
| GLM-5.3-Flash | Sin pesos, backend local compatible ni BCB | No agregar |

## Qué sí vale conservar como idea

- Evaluar la arquitectura híbrida sparse/linear para contexto largo.
- Probarlo en el futuro mediante el backend oficial más reciente, no con la
  imagen vLLM Qwen fijada actualmente.
- Exigir antes de promoverlo: artefacto por debajo del presupuesto de memoria,
  soporte CUDA SM86, smoke de texto, visión, tool-use, HE0/HE20/BCB y medición
  de cold/warm prefill.

No se descargaron pesos, no se modificó ningún perfil, no se cambió el default
y no se dejó ningún servicio ejecutándose.

Referencias:

- [Ficha oficial GLM-5.3-Flash](https://huggingface.co/zai-org/GLM-5.3-Flash)
- [Ficha oficial GLM-5.3-Flash-BF16](https://huggingface.co/zai-org/GLM-5.3-Flash-BF16)
- [Auditoría previa de LayerStoRm](layerstorm-linux-evaluation-20260908.md)
