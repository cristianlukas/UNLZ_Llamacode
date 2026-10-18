# Plan — Q-20261018-STRATA-PEER-RETEST

## Objetivo

Completar las pruebas locales pendientes del análisis del post “Qwen3.8-Flash-Next, dual RTX 3090s, NVLink”, determinando con evidencia fresca si este host permite probar el camino peer de Strata.

## Pruebas y gates preregistrados

1. Capturar topología actual (GPU modelo/driver, `nvidia-smi topo -m`, estado NVLink y P2P en ambos sentidos), procesos GPU, RAM/swap/PSI y runtimes/pesos compatibles ya presentes. Sólo inspección; no interrumpir ni modificar procesos ajenos.
2. Si CUDA informa P2P soportado y ambas GPU/puertos están libres, identificar versión/commit exactos, modelo y hashes locales, luego probar la ruta disponible. Sin NVLink se rotulará como P2P sobre PCIe y no se atribuirán sus resultados a NVLink.
3. Correr A/B sólo con un mismo modelo, prompt, contexto, sampling, runtime/build y cache; incluir el control layer-split/`--gpu1-experts` cuando exista. Reusar huellas previas idénticas. Tres semillas por perfil; corte máximo de 30 minutos por perfil.
4. Si NVLink/P2P no están activos, GPU está ocupada, o faltan checkpoint/runtime comparables, no cargar modelos ni forzar la ruta: registrar la prueba bloqueada por la condición concreta y cerrar con preflight actualizado.

No se cambian perfiles de LlamaCode, no se instala software y no se descargan modelos. Sin cambios de código de producto.
