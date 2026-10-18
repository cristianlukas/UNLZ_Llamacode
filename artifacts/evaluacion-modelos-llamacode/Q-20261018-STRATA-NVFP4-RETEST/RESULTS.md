# Resultados — Q-20261018-STRATA-NVFP4-RETEST

- **Estado:** bloqueada antes de build, descarga e inferencia; sin nueva huella.
- **Fecha de cierre:** 2026-10-18T16:51:12Z.
- **Lock:** `6feaf312-50c5-44ec-b372-b32d4035f27c`.
- **Objetivo:** por pedido del usuario, ejecutar el gate de prefill/HE0 que faltó en la auditoría del post. El plan está en [`PLAN.md`](PLAN.md).

## Preflight ejecutado

Sólo se hicieron inspecciones read-only: `df -h / /media/cristian/7CFE1E0FFE1DC1F6`, `free -h`, `nvidia-smi`, `nvidia-smi topo -m`, consulta de procesos CUDA, inspección de los directorios locales conocidos del modelo/pack, versión del compilador y metadatos del checkout/build antiguos. Recibos: [`local-preflight.json`](receipts/local-preflight.json) y [`source-review.md`](receipts/source-review.md).

La caché de Hugging Face del checkpoint sólo contiene `refs`; no contiene snapshot ni los pesos. Tampoco están en las rutas locales revisadas el modelo/pack usado anteriormente; las rutas de almacenamiento anteriores ya no existen en este host. El build/binario local encontrado pertenece al checkout viejo, commit `992195498c16ea2b26c08bf1ba2402291553136f`, no al runtime objetivo. La release actual revisada es `v0.1.44.1-nvfp4.2`, commit `257727d`, build de engine `3dc869fb`; no hay un binario nuevo instalado.

El volumen de datos da 121 GiB libres y la raíz 5,1 GiB. La ficha primaria del checkpoint exacto declara 126 GiB para el modelo fuente, por lo que el origen por sí solo no cabe en el volumen inspeccionado; la conversión a pack requiere además espacio de salida. No se descargó, no se construyó y no se intentó usar GPU. GPU0 estaba idle (15 MiB); GPU1 estaba ligada al escritorio y con una sesión de LlamaCode activa (626 MiB observados); no se detuvo ni utilizó ningún proceso ajeno. Topología local PHB, sin NVLink.

## Matriz de pruebas

| Prueba | Estado | Resultado |
|---|---|---|
| Modelo/pack exacto, hashes y carga | Bloqueada antes del gate | Peso exacto ausente; almacenamiento insuficiente para reponerlo. |
| HE0 nuevo con runtime actualizado | No ejecutado | Sin checkpoint/pack y sin build del runtime objetivo. |
| HE20 | No ejecutado | Requiere HE0 válido. |
| BCB8 | No ejecutado | Requiere HE20 válido. |
| ADV v1 / TaskFlow ULTRA | No ejecutados | No se alcanzó el gate de coding. |
| Computer Usage E2E | No ejecutado | Sin perfil ejecutable ni fixture real. |
| Visión, contexto 188K/256K, velocidad/MTP | No ejecutados | No se infiere desde el post ni desde el preflight. |
| Ingi-Charla / ASR / TTS | No ejecutados | El post no aporta evidencia de audio. |

El HE0 histórico que sí existe (1/1 después de una reparación con `--prefill 2048`) sigue siendo el único HE0 del checkpoint; no se lo presenta como prueba del runtime actualizado. HE20/BCB8/ADV/TaskFlow nunca se completaron para Orca. No se creó fingerprint nuevo. Sin cambios de perfiles, defaults, HarnessSpec, pesos, código de producto ni build de LlamaCode. No correspondían `tests-linux.sh` ni tests C++/QML porque no se modificó código.

## Decisión y reanudación

No promover ni cambiar la recomendación. El fork actual ofrece mejoras desde el runtime probado, pero este retest no pudo determinar si resuelve el stall ni medir calidad. Reanudar con el snapshot exacto o el pack/PLE/MTP íntegro verificable en almacenamiento que tenga capacidad simultánea para los pesos fuente y la conversión; verificar hashes y checkout `v0.1.44.1-nvfp4.2`, volver a hacer preflight y comenzar únicamente por HE0. Luego seguir HE20 → BCB8; reportar fuera de alcance las otras modalidades. El test de una sola GPU, si se elige GPU0, se reportará como perfil completo distinto, no como A/B directo con el ensayo histórico dual-GPU.
