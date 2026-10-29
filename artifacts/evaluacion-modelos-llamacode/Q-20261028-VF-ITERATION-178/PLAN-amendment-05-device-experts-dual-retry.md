# Q178 A05 — NInfer-all con expertos residentes en ambas GPU

## Motivo

A04 cargó los pesos base en pipeline dual y el mismo PID apareció en las dos RTX 3090, pero NInfer-all abortó antes de readiness al inicializar el stream de expertos desde disco: `cudaEventRecord(half_done[half], half_stream)` devolvió `cudaErrorInvalidResourceHandle`. No fue OOM ni falta de RAM: MemAvailable seguía sobre 100 GiB. A04 limpió el proceso y liberó ambos GPU; los logs/JSON quedan preservados.

El manual del commit fijado documenta expertos `device` para dos GPU de 24 GB y KV dispersa `--kv-resident N` que pasa posiciones posteriores a memoria host. A05 prueba ese modo: evita el código `expert_stream.cpp` de residencia disk y limita la KV de GPU a 32K para dejar sitio a las matrices. Es un perfil dual distinto de A04 y de la fila histórica Q173.

## Artefactos y runtime

Se mantienen exactamente los mismos GGUF IQ2_XS/RCO convertidos a NInfer v3, sus hashes, la tabla n-gram, NInfer-all Q174, tokenizer y llama-benchy ya fijados en `receipts/prereg-amendment-04-ninfer-all-dual-context-ladder.json`. El nuevo runner tiene SHA-256 `618ae0d911b36de4755d91857d0d25227497ce8cff994bb392dc13eba916cf2f` y el preregistro está en `receipts/prereg-amendment-05-device-residency.json`.

## Cambio controlado de perfil

- Pipeline `--devices 0,1`, `--expert-residency device`; no se usa el caché de expertos disk/host. Una etapa de pipeline por RTX 3090, no tensor-parallel.
- KV `int8`, `--kv-resident 32768`, contexto/capacidad 262.144. Las posiciones sparse-KV por encima de 32K van a memoria host según el runtime; esto se etiqueta en la tabla.
- El resto de parámetros, muestreo, puerto local, ausencia de prefix reuse/speculation, salida exacta de 128 tokens y ladder queda igual a A04 y Q173: 8K×3, 32K/64K/128K/261888×1. No Q172 nuevo, 512K ni 1M.
- Cold-process y relanzamiento inmediato Popen→`/health` + `/v1/models`; page cache no se purga y los hashes previos ya leyeron pesos. Etiquetar como inicio de proceso y cache probable, no frío/caliente de disco.
- Sólo iniciar si ambas GPU están visibles y no hay otro inference server. Requerir el mismo PID compute en las dos tarjetas. Abortar ante OOM/Xid, error CUDA/runtime, RAM disponible <32 GiB durante cuatro muestras consecutivas de 15 s, prompt/output incorrectos o cleanup no verificable.

## Atribución y presentación

A05 genera una fila aparte `NInfer-all v3, device experts, dual 3090, KV resident 32K`. No hereda el Q172 77/100 de Q173 como puntuación propia: ese score y TC-75/82/84/92 siguen vinculados a v0.16.1/GPU1. La fila histórica Q173/Q171 conserva todos sus datos y el inicio aproximado de 330 s. Strata YaRN×4 a 1M sigue separado.
