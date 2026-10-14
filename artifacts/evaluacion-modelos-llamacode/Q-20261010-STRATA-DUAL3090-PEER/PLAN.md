# Plan — Q-20261010-STRATA-DUAL3090-PEER

## Objetivo

Verificar qué mide el post “Qwen3.8-Flash-Next, dual RTX 3090s, NVLink” y si sus afirmaciones sobre peer-to-peer/NVLink o velocidad se transfieren al perfil Strata/LlamaCode local.

## Candidato y controles

- Candidato reportado: Qwen3.8-Flash-Next/Strata en 2×RTX 3090 con NVLink. Fijar cuantización, Strata/runtime, contexto, sampling, test, seeds y topología reportados antes de calcular deltas.
- Controles locales reutilizables: perfiles Strata dual-GPU Q4 UD-Q4_K_XL e IQ2_XS y sus recibos; comparar sólo dimensiones alineadas. Reusar el A/B existente si la misma huella contesta la pregunta.
- No atribuir diferencias al NVLink si cambian quant, runtime, CPU, prompt, contexto, cache/resident experts, P2P o suite.

## Trabajo preregistrado

1. Identificar la publicación y verificar configuración/fuente primaria o recibos del autor.
2. Inspeccionar en sólo lectura la topología local (`nvidia-smi topo -m`, estado NVLink/P2P), hardware, ocupación, RAM/swap y logs locales Strata existentes.
3. Contrastar con documentación oficial de Strata, CUDA/NVIDIA y resultados locales ya guardados.
4. No iniciar benchmark nuevo si GPU0 está ocupada, la topología no coincide, no se puede aislar el factor, o el tiempo total proyectado por perfil supera 30 minutos. No tocar/desconectar ArtCraft.
5. Sin cambios de perfiles/harness. Si no hay A/B comparable, cerrar como auditoría documental con el límite específico.

## Recursos y corte

- Dos RTX 3090 posibles; ninguna reservada antes del preflight. Secuencial si se usa GPU.
- Límite de interés: máximo 30 min por perfil para un bloque completo de tres seeds. Este trabajo prioriza recibos existentes y no repetirá una huella exacta sin hipótesis nueva.

## Evidencia

URL/claims, documentación primaria, salida de topología y ocupación sin modificar el sistema, huellas/resultados históricos pertinentes y conclusión por uso. No inferir de una salida teórica de NVLink una mejora de calidad ni de velocidad efectiva de Strata.
