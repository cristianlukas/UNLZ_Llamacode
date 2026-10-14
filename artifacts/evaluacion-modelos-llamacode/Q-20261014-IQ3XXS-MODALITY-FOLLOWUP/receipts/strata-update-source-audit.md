# Auditoría de la actualización de Strata citada

Revisada el 2026-10-14. El post compara una actualización en un sistema 2× RTX 5090 / 256 GB, pero no incluye hash del modelo, cuant exacta, prompt, seed, TTFT, número de muestras ni configuración completa. Su throughput no es un A/B reproducible contra las 2× RTX 3090 locales.

El perfil de esta evaluación es Strata v0.1.41 (`fb58e0d`), publicado el 8 de octubre. Sus notas oficiales describen ganancias en prompts cortos de una GPU y cargas concurrentes multi-GPU; las tablas publicadas no demuestran que una sola secuencia larga en dos RTX 3090 deba superar 200 tok/s.

- PR #711: streaming de KV híbrida K8V4 con `--kv-resident`; el perfil local usa `--kv int8`, por lo que no activa este cambio.
- PR #749: respeta la capacidad de commit de Windows al reservar memoria; el host local es Ubuntu/Linux.
- Al 14 de octubre, upstream ya publicó 0.1.44 y corrigió incidencias inmediatas en 0.1.44.1. No se cambió el runtime durante esta prueba para conservar el fingerprint. Cualquier comparación de versión requiere un A/B separado con la misma suite/perfil.

Fuentes primarias:
- https://github.com/Niko1221/Strata/releases/tag/v0.1.41
- https://github.com/Niko1221/Strata/pull/711
- https://github.com/Niko1221/Strata/pull/749
- https://github.com/Niko1221/Strata/releases/tag/v0.1.44
