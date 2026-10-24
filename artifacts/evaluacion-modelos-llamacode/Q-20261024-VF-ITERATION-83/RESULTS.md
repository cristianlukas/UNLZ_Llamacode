# Q83 · resultados

Estado: **completa · auditoría CPU/read-only**. No se ejecutaron inferencias, benchmarks, builds, descargas ni consultas de GPU. No se modificaron perfiles, modelos, drivers ni servicios.

## Lo que confirma el reporte

- El criterio de decisión correcto es tarea terminada, calidad, tiempo E2E y estabilidad. TPS aislado no basta.
- Mantener el default de ASTRA en 131K es consistente con Q37: 1M recuperó 8/8 en tres semillas sintéticas, pero no mostró una ganancia general frente a respuestas completas a 131K y elevó mucho la latencia.
- Los resultados OpenJet/Qwen, Swift y MTP que cita el usuario coinciden en lo esencial con los screens locales: no habilitan adopción.

## Corrección importante sobre Q76–Q78

- **Q76 ya está implementada y validada:** `./scripts/build-linux.sh Debug`, `./scripts/tests-linux.sh Release` (94/94) y `test_agent_wire` pasaron con regresiones loopback de replanificación. No es una reparación pendiente.
- **Q77 fue inconclusa, no un fallo:** Qwen3.8-27B serializó las tools en 3/3 semillas; no generó el lote diferido que activa la rama Q76. La regresión CPU ya cubre esa rama de forma determinista; otra corrida Q77 con la misma fixture no cambiaría la decisión.
- **Q78 sí deja un requisito de arquitectura:** la ruta MCP local inspeccionada no transporta un principal tenant autenticado. Sin un backend/contrato real que defina principal y autorización por recurso, no se puede hacer una prueba cross-tenant fiel sin inventar la política.

Ver [Q76](../Q-20261024-VF-ITERATION-76/RESULTS.md), [Q77](../Q-20261024-VF-ITERATION-77/RESULTS.md) y [Q78](../Q-20261024-VF-ITERATION-78/RESULTS.md).

## Claims externos revisados

- **HyperQwen:** el README reporta 127 tok/s en una solicitud y alrededor de 1.035 tok/s agregados con 64 solicitudes. Son cargas distintas y cifras del propio repositorio, no resultados locales. La documentación oficial de multi-GPU admite TP=2 y registra un A/B comunitario de dos RTX 3090 frente a una: +16–35% decode C1–C8 (DFlash2, 127,4→161,6 tok/s en C1); sirve para justificar el candidato, no para predecir el resultado de este host. La prueba principal debe usar las dos RTX 3090 y 128 GB contra el setup productivo ASTRA/SOL, con la misma suite LlamaCode y comparando tareas correctas, E2E, TTFT, prefill/decode y estabilidad. Como brazo secundario, medir HyperQwen TP=1 frente a TP=2 con el mismo modelo/runtime para cuantificar el valor de liberar una GPU. C64 se mide aparte y sólo contra otro C64 con configuración compatible; no comparar su throughput agregado con una solicitud interactiva. No cambiar ni parchear drivers para habilitar P2P. El repositorio también indica una imagen Docker de ~9,5 GB y un modelo preparado de ~20 GB; el server debe quedar limitado a loopback o autenticado.
- **MoMoE:** el repositorio dice que Flash-Next corre mediante el engine de Strata; su engine CUDA propio sirve otras familias. Sus mediciones de Flash-Next en PC no son de una RTX 3090. No es un motor independiente que justifique repetir el A/B Flash-Next/Strata ya hecho.
- **Project Maya:** el README confirma una medición de Maya-S24 en 2×RTX 3090 y 128 GB RAM: 53 tok/s decode y 885 tok/s prefill, en un Threadripper 3970X distinto. Es un candidato complementario GLM, no evidencia de que supere ASTRA/SOL en tareas LlamaCode. Maya-S24 ocupa ~94,7 GB y la documentación recomienda NVMe rápido; el host no tiene espacio suficiente.
- **Geezuz:** su propio repositorio muestra 190 tok/s Q4_K_M y 622 tok/s agregados a ocho solicitudes en 2×RTX 3090. El resultado se obtuvo con driver 595.84 open y parche P2P; cambiar el driver principal no forma parte de esta prueba y queda fuera de alcance.
- **NVIDIA OpenShell:** ofrece sandbox/políticas de filesystem, proceso, red y credenciales. Puede ser una capa de aislamiento futura, pero no crea por sí misma el principal de tenant que falta en la ruta MCP auditada.

## Capacidad del host y decisión

`df -B1` al 2026-10-24 13:49 UTC: raíz 10.272.423.936 B libres; `Disco local` 23.472.803.840 B; `HDD extra` 30.465.982.464 B. Docker usa `/var/lib/docker` en raíz. HyperQwen requiere aproximadamente 9,5 GB de imagen más 20 GB de modelo preparado; no hay un destino que sostenga ese payload y conserve el margen local de 20 GiB. No se descargó nada ni se borró ningún modelo.

Decisión: crear el accionable HyperQwen como prioridad alta, **bloqueado por almacenamiento**. No iniciar prueba hasta identificar un destino con espacio suficiente sin tocar ASTRA/SOL/Flash-Next/PeritoSoft ni dejar los discos por debajo del margen. La prueba principal será TP=2 en las dos 3090 frente al setup productivo; TP=1 queda como brazo secundario. Antes de reservar GPU, fijar fingerprints/configuraciones y un gate de calidad no inferior más una mejora práctica de E2E. No se usará el número agregado a 64 para justificar adopción sin una medición C64 equivalente.

No se cambian los resultados previos ni se promueve ningún candidato. Reabrir el test HyperQwen sólo cuando haya margen de almacenamiento y un plan de instalación que pueda fijarse y desinstalarse sin afectar el setup productivo.

### Corrección del alcance de hardware (2026-10-24)

El usuario aclaró que el host objetivo es dual RTX 3090 con 128 GB RAM. Por tanto, la recomendación de centrar la prueba en una sola GPU era inadecuada para la decisión principal y queda sustituida por TP=2 en ambas GPU; TP=1 es sólo un análisis secundario de eficiencia. La capacidad de dos GPU no elimina el bloqueo de almacenamiento ni autoriza alterar el driver. Fuentes primarias adicionales: [HyperQwen multi-GPU](https://github.com/syv-ai/HyperQwen/blob/main/docs/multi-gpu.md) y [A/B dual 3090 #40](https://github.com/syv-ai/HyperQwen/issues/40).

## Fuentes primarias

- [HyperQwen README](https://github.com/ultimaterex/HyperQwen)
- [MoMoE README](https://github.com/aflin/momoe)
- [Project Maya README](https://github.com/mw00/project-maya)
- [Geezuz README](https://github.com/ohgeebtw/geezuz-qwen3.8-27b-dual-gpu)
- [NVIDIA OpenShell README](https://github.com/NVIDIA/OpenShell)

