# Q83 · auditoría del diagnóstico y selección del próximo test

## Objetivo

Contrastar el diagnóstico pegado por el usuario con los resultados locales Q76–Q82 y revisar en fuentes primarias las opciones HyperQwen, MoMoE, Project Maya, Geezuz y NVIDIA OpenShell. Elegir sólo pruebas que puedan cambiar una decisión; mantener protegidos ASTRA/SOL/Flash-Next y los recursos de PeritoSoft.

## Alcance y límites

- CPU y lectura documental únicamente; no build, inferencia, benchmark, descarga ni uso de GPU.
- Releer artefactos de resultados y revisar almacenamiento local antes de proponer una descarga.
- Si aparece un candidato ejecutable, registrarlo como accionable con gates y huella antes de reservar GPU.
- No modificar perfiles, pesos ni drivers.

## Preguntas

1. ¿Q76–Q78 siguen dejando una prueba de dispatcher/tenant ya ejecutable?
2. ¿Los claims externos aportan un A/B relevante para Qwen3.8-27B o Flash-Next?
3. ¿El host tiene capacidad suficiente para preparar el candidato sin romper el margen de almacenamiento?

## Corrección del diseño tras aclaración del hardware

El usuario confirmó que el equipo objetivo tiene 2×RTX 3090 y 128 GB de RAM. El brazo de una GPU no representa su configuración principal. Si se habilita almacenamiento suficiente, registrar antes de ejecutar:

1. **A/B primario:** HyperQwen TP=2 usando las dos 3090 frente al setup productivo ASTRA/SOL, sobre la misma suite congelada de LlamaCode, prompts, herramientas, límites y evaluación. Comparar éxito funcional, tiempo hasta resultado correcto, TTFT, prefill/decode y estabilidad; fijar el margen de calidad y mejora práctica antes de cargar modelos.
2. **A/B secundario de eficiencia:** mismo HyperQwen/modelo/runtime en TP=1 y TP=2, para valorar si el rendimiento por GPU justifica dejar una 3090 libre. No sustituye la comparación productiva.
3. **Concurrencia:** C64 sólo si importa al workload real y sólo contra un control C64 con contexto, KV cache, vision y configuración equivalentes. No mezclar agregados con latencias de usuario único.

La evidencia externa de HyperQwen incluye TP=2 y una medición comunitaria en 2×3090 sin NVLink; es una hipótesis para priorizar, no un resultado del host. No modificar el driver ni aplicar parches P2P. Fuentes: https://github.com/syv-ai/HyperQwen/blob/main/docs/multi-gpu.md y https://github.com/syv-ai/HyperQwen/issues/40. El bloqueo actual sigue siendo el espacio de almacenamiento.

