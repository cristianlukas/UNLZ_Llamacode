# Auditoría del NInfer Windows para RTX 5090 — 2026-09-18

## Resumen

Se revisó el reporte de `Qwen3.8 27B NInfer Windows Edition x 5090` y se lo
comparó con las mediciones locales de LlamaCode sobre 2× RTX 3090 en Ubuntu.
El resultado externo no es trasladable ni supera a `SOL` en nuestra máquina:

- El reporte externo declara aproximadamente **162,1 tok/s de decode**,
  **4,26k tok/s de prefill** y **200K de contexto Q8**.
- Esas cifras corresponden a un port nativo de NInfer para **una RTX 5090
  `sm_120a`**, con artefactos Qwen3.8 NVFP4 y kernels específicos de
  Blackwell.
- El NInfer local que sí fue probado está adaptado a **SM86/RTX 3090**, usa
  otro artefacto histórico, una GPU por proceso, MTP3 e INT8 KV.
- El artefacto `.ninfer` local actual no está disponible: sólo queda un archivo
  `.lock` de una descarga incompleta. El artefacto histórico fue retirado a la
  papelera durante la limpieza de modelos.

## Comparación de evidencia

| Ruta | Hardware/runtime | Resultado medido | Calidad/alcance | Decisión |
|---|---|---:|---|---|
| NInfer Windows externo | 1× RTX 5090, `sm_120a`, NVFP4, Windows | ~162,1 TG / ~4,26k PP; 200K Q8 declarado | Cifra del autor; no reproducida aquí | No promover ni descargar |
| NInfer-3090 local | RTX 3090, SM86, Linux, MTP3, INT8 KV | 73–75 TG a 8K; 50,1 TG/745,3 PP a 80K; 62,9 TG/660,7 PP a 120K | BCB 3/8; tool-use smoke OK; sin visión compatible | Experimental histórico |
| SOL local | 2× RTX 3090, vLLM TP2/P2P, AutoRound INT4, MTP4, FP8 KV | 74 narrativo / 102 código | BCB 8/8; tool-use estable; 262K validado; visión 4/4 | Default |

Los números de NInfer Windows no deben compararse directamente con los de SOL:
el primero es una medición de una GPU Blackwell con un motor y un artefacto
especializados; SOL es una medición agentiva local sobre dos GPUs Ampere.

## Qué ideas del post sí son relevantes

### Concurrencia y subagentes

El comentario externo menciona unos 300 tok/s agregados con dos solicitudes
concurrentes y contexto dividido. Eso describe batching en la implementación
de 5090, no una mejora de P2P ni una propiedad que NInfer-3090 pueda heredar.
En nuestra configuración, la estrategia equivalente ya es ejecutar sesiones
paralelas de `SOL` con límites de contexto por perfil. No se cambia el backend
porque NInfer-3090 no implementa ejecución multi-GPU.

### MTP

El post y el repositorio 5090 usan MTP5/DFlash2, `lm-head-draft` y parámetros
de aceptación propios de NVFP4/Blackwell. Nuestro NInfer-3090 ya tiene MTP3
funcional en la variante histórica, pero el BCB local es 3/8. No hay evidencia
de que copiar `draft-tokens 4/5`, DFlash2 o `lm-head-draft` a SM86 mejore la
calidad o arranque con el artefacto local; por eso no se modificó el perfil.

### KV K8V4 y visión

`k8v4` y la visión del repositorio 5090 son rutas del port Blackwell. El NInfer
SM86 local usa INT8 KV y no tiene un `mmproj` compatible validado. Agregar el
proyector o cambiar el tipo de KV por configuración no convierte el artefacto
ni sus kernels en la variante 5090, así que no se hizo una combinación
experimental ciega.

## Verificaciones realizadas

- Se revisó el README y los launchers del port Windows: exigen RTX 5090
  `sm_120a`, CUDA 13.1+ y artefacto `qwen3_8_27b_nvfp4.ninfer`.
- Se buscó el artefacto local en las particiones de modelos: no hay un
  `.ninfer` completo disponible para repetir la prueba; sólo existe
  `qwen3_8_27b.ninfer.lock`.
- Se contrastaron las mediciones locales documentadas de 8K, 80K y 120K; no se
  repitió una corrida idéntica sin pesos porque no produciría evidencia nueva.
- Se verificó que no quedaran procesos `vllm`, `llama-server` o `ninfer`
  ejecutándose al finalizar.

## Decisión para LlamaCode

No se actualiza ningún perfil ni se reemplaza `SOL`.

`NINFER-QWEN38` queda documentado como backend histórico experimental para
investigación SM86, con 120K probado, 131K operativo y BCB 3/8. El reporte de
5090 sirve como referencia de que un NInfer especializado puede rendir mucho
más con Blackwell, pero no demuestra una mejora disponible para nuestras
RTX 3090.

### Fuentes externas

- [Reporte original de la prueba en Reddit](https://www.reddit.com/r/LocalLLM/comments/1wifdot/qwen38_27b_ninfer_windows_edition_x_5090/)
- [Port NInfer Windows para RTX 5090](https://github.com/headpiece747/ninfer-5090-windows)
- [Evaluación local de NInfer-3090](./ninfer-3090-linux-evaluation-20260908.md)
