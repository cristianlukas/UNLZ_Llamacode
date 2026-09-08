# Evaluación de LayerStoRm en Ubuntu — 2026-09-08

## Resultado

LayerStoRm no es compatible con el hardware actual de LlamaCode y no se
implementó como perfil. El repositorio declara soporte de GPU únicamente para
NVIDIA RTX 50xx con arquitectura SM120; esta PC tiene dos RTX 3090 con compute
capability 8.6. La matriz publicada tampoco incluye Qwen3.8 Flash-Next como
modelo soportado.

Fuente revisada: [repositorio oficial de LayerStoRm](https://github.com/kkontosis/LayerStoRm).

## Verificaciones locales

| Verificación | Resultado |
|---|---|
| GPU 0 | RTX 3090, SM8.6, 24 GiB |
| GPU 1 | RTX 3090, SM8.6, 24 GiB |
| CUDA toolkit visible en Ubuntu | 12.0 |
| LayerStoRm instalado localmente | No |
| Artefactos o binarios LayerStoRm locales | No encontrados |
| Compatibilidad con la arquitectura requerida | No; el proyecto apunta a SM120/RTX 50xx |
| Modelo compatible disponible localmente | No |
| Benchmark de TPS/VRAM/BCB | No ejecutable de forma válida |

## Qué aporta el proyecto

La idea sí es relevante para el problema de Qwen/GLM grande: mantiene expertos
en RAM fijada, usa la VRAM como caché, hace streaming por PCIe, soporta KV
tiering y ofrece una API OpenAI-compatible. La publicación oficial reporta
GLM-5.3-Flash UD-Q4_K_XL a 24,5 tok/s a 8K y 1M de contexto, pero esos números
son de una configuración con 2× RTX 5090 + 2× RTX 5080, 512 GiB de RAM y
hardware SM120; no son extrapolables a nuestras 3090.

El propio repositorio lista como modelos soportados GLM-5.3-Flash, GLM-5.2 y
DeepSeek-V4-Flash. No ofrece una ruta lista para el Qwen3.8 Flash-Next que
usamos en ASTRA.

## Decisión para LlamaCode

- No se descargó el repositorio ni modelos de casi 200 GiB.
- No se cambió ningún perfil de LlamaCode.
- No se modificó Windows.
- ASTRA, SOL, TERRA, LUNA, METEOR y DEEPSEEK siguen usando sus backends
  validados.
- La idea queda registrada como referencia para una eventual máquina RTX 50xx,
  no como tarea de optimización para esta PC.

Para esta máquina conviene seguir optimizando llama.cpp/ExLlamaV3 y sus rutas de
expert cache, MTP, n-gram y CPU offload, que sí tienen soporte para Ampere.
