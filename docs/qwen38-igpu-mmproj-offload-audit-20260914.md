# Auditoría: descargar el mmproj al iGPU del Ryzen 9 9950X3D — 2026-09-14

## Resultado

La idea del post es técnicamente aplicable a una configuración híbrida, pero no
es una mejora inmediata para los perfiles actuales de LlamaCode. El iGPU del
9950X3D sí está visible en Linux mediante Vulkan, pero los binarios CUDA que
usa hoy LlamaCode no exponen Vulkan ni pueden enviarles el `mmproj`.

No se modificó ningún perfil ni el default.

## Verificación local

| Prueba | Resultado |
| --- | --- |
| iGPU del Ryzen 9 9950X3D visible en Vulkan | **Sí**, RADV `RAPHAEL_MENDOCINO` |
| RTX 3090 visibles en Vulkan | Sí |
| `llama-server` CUDA actual con `--list-devices` | Sólo CUDA0 y CUDA1 |
| `llama-server` actual con backend Vulkan | No hay un binario Vulkan+CUDA listo en la caché de LlamaCode |
| Flash-Next + mmproj disponible | No compatible: `n_embd 2560` frente a `5120` |
| Visión BeeLlama/KVarN | No validada |

La detección de Vulkan confirma que el hardware podría servir para un futuro
perfil multimodal. No demuestra por sí sola que el iGPU sea más rápido: el
beneficio depende del tamaño del proyector, del enlace de memoria compartida y
de que CUDA y Vulkan puedan coexistir correctamente en el mismo proceso.

## Comparación con nuestros perfiles

| Perfil | Situación actual | Qué cambiaría con iGPU |
| --- | --- | --- |
| **SOL** | Qwen3.8-27B, BCB 8/8, 262K, tool-use válido | Podría liberar VRAM para visión/contexto, pero SOL hoy no tiene visión validada como el perfil principal |
| **QWEN35-A3B** | Visión validada 4/4 y 262K | Es el candidato más lógico para probar mmproj en Vulkan; no hay medición local aún |
| **ASTRA** | Flash-Next experimental, salida inestable en varias recetas | No se puede arreglar sólo moviendo el mmproj; el problema principal es runtime/prefill |
| **BeeLlama KVarN5** | ~36 tok/s a 131K, texto/tool-use válido | Sigue siendo texto-only hasta disponer del mmproj correcto y backend compatible |

## Por qué no se implementa ahora

1. La build CUDA actual enlaza `libggml-cuda`, pero no `libggml-vulkan`.
2. El `mmproj` local probado pertenece a otra variante y no coincide con
   Flash-Next; usarlo produciría un perfil que falla al cargar.
3. Agregar `--mmproj-device Vulkan` sin un binario que lo soporte dejaría una
   configuración no arrancable.
4. La mejora del post es de memoria/latencia multimodal, no una mejora de
   calidad ni de decode del modelo principal; no puede justificar reemplazar
   SOL sin una medición A/B.

## Plan de prueba si se habilita una build Vulkan+CUDA

La prueba correcta sería crear un binario aislado, sin reemplazar el runtime
CUDA estable, y comparar el mismo modelo Qwen3.6/Qwen3.8 con:

1. `mmproj` en CUDA;
2. `mmproj` en el iGPU Vulkan;
3. `mmproj` en CPU/RAM como control.

En cada variante se medirían carga, VRAM de ambas RTX, RAM compartida, TTFT,
prefill, decode, una imagen simple, tres imágenes, contexto 64K/131K y
tool-use. Sólo se promovería si arranca de forma repetible y mejora la
latencia sin degradar la lectura visual.

## Decisión

La idea queda registrada como una optimización futura para **QWEN35-A3B** y
otros perfiles multimodales. No es superior a nuestros perfiles actuales en
la evidencia disponible y no se activa en el dropdown. **SOL permanece como
default.**

Referencias locales:

- `docs/qwen38-flash-next-3090-kvarn5-vision-audit-20260914.md`
- `docs/qwen38-flash-next-amd-tuning-audit-20260914.md`
- `assets/system_profiles.json`
