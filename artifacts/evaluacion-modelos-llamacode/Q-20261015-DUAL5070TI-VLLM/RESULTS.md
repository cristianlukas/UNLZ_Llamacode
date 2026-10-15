# Resultados — Q-20261015-DUAL5070TI-VLLM

## Estado

**Auditoría de fuentes y preflight completados; sin inferencia local, no promovido.** La cola estaba libre de otras tareas pendientes al comenzar. Se registró esta campaña bajo su propio lock y se liberó al cerrar.

## Qué se verificó

- ExTV `dual-gpus-vllm` es una receta de vLLM 0.30.0 con patches propios, pipeline parallel y modelo Qwen3.8-27B sobre una RTX 5090 32 GB y una RTX 4070 Ti SUPER 16 GB. Publica NVFP4/W8A16/FP8 con DFlash2 y FP8+MTP. El README informa 262K de contexto, soporte anunciado de vision/tool calling, 215–259 tok/s de code en NVFP4+DFlash2 y 111,7 s para prefill de 250K. El benchmark documenta dos boots para decode y advierte que la aceptación del drafter varía. El launcher se ajusta a GPUs desiguales con partición 21/43.
- El comentario de 150–200 tok/s en 2×5070 Ti apunta al otro proyecto. El enlace NInfer TP2 ahora redirige a `capy-flash`, renombrado desde v0.5.0; el repo visible hoy es v0.5.1. Sus pruebas de Qwen3.8-27B v0.4.9 sobre 2×RTX5070 Ti reportan replay agentic de 53 turnos a 171,2 tok/s y 156 s total. El benchmark anterior NInfer v0.2.3 midió 220,0±10,2 tok/s en structured decode, 70,9 plain decode y 4.956 tok/s de prefill a 7.680 tokens con los pesos oficiales; no todas las filas de 5090 se re-midieron. El valor ~5K no describe prefill de 250K.
- La versión actual `capy-flash` para Flash-Next 125B MoE se midió en dos 5070 Ti: 20/20 resultados de su task bank privada (5 tareas × 4 corridas), sin llamadas de herramientas malformadas en 1.124; el lote llevó 4,28 horas. Esto no cubre una suite LlamaCode y supera el corte local de 30 minutos por perfil. El replay incluye 3 sesiones sintéticas y 53 turnos, no es Computer Usage E2E.
- En RAM, el post de “5 GB con mmap / 26 GB sin mmap” es una observación de un comentarista y no una regla general. ExTV midió su receta concreta con 31 GiB; `capy-flash` v0.5.1 requiere alrededor de 70 GiB disponibles por una asignación pinned-host de 64,6 GiB para los expertos. No son el mismo artefacto ni runtime.

## Preflight local ejecutado

Recibo: [`local-preflight.txt`](receipts/local-preflight.txt).

- 2×RTX 3090, 24 GiB cada una, compute capability 8.6 (`sm_86`); topología PHB y `nvidia-smi topo -p2p p`: `NS` en ambas direcciones.
- Driver expone CUDA 13.3, pero el toolkit local es CUDA 12.0 y Python 3.12.3. `capy-flash` v0.5.1 requiere build `sm_120a`, CUDA 13.1 y dos GPUs `sm_120`; por eso no se instaló ni se compiló.
- RAM disponible 111 GiB y presión PSI 0 en el instante del chequeo; swap usado 5,1 GiB. La memoria disponible supera el requisito de `capy-flash`, pero no corrige la incompatibilidad de GPU. CPU Ryzen 9 9950X3D tiene AVX-512. NVMe con 166 GiB libres.
- GPU0 está sirviendo el escritorio y procesos gráficos del usuario; GPU1 tenía Xorg. No se detuvo nada ni se inició carga de cómputo.
- El checkpoint exacto ExTV `lued/Qwen3.8-27B-huihui-abliterated-INT8-W8A16-DFlash2` no aparece localmente. Sí existe evidencia previa de otros pesos/runtime: ver los tres informes enlazados abajo. No se repitió su fingerprint.

## Pruebas por uso de LlamaCode

| Uso | Resultado de esta campaña |
|---|---|
| Coding/agentes | Sin corrida nueva. Las cifras de agente publicadas usan otra tarea/modelo/host; el banco privado de 20 ejecuciones toma 4,28 h. Ya hay evidencia local de DFlash2 relacionada, pero fue un perfil distinto y tuvo problema de JSON/xgrammar. |
| Computer Usage | No evaluado: ninguna prueba terminó en una aplicación real con estado verificable. Tool calls y replay no son CU E2E. |
| Ingi-Charla | No evaluado: las fuentes revisadas no aportan corpus acústico, ASR/TTS ni métricas de audio. |
| Visión | ExTV anuncia imágenes hasta 4 MP, pero no presenta en el benchmark leído una matriz de calidad LlamaCode; no se envió imagen local. No inferir calidad por compatibilidad del API. |
| Contexto | 262K es capacidad/configuración anunciada y hay un prefill publicado de 250K en ExTV; no equivale a calidad general ni a retrieval LlamaCode. `capy-flash` anuncia hasta 262K, no 1M. |
| Velocidad/memoria | Señales de velocidad externas verificables, pero otro hardware y perfil. No hay A/B local comparable; el comentario de 5/26 GB no se generaliza. |

## Decisión

No cambiar perfiles, HarnessSpec, defaults ni recomendaciones. `SOL` permanece recomendado para coding/agentes con datos sensibles; ASTRA mantiene su selección actual y las advertencias TC-92/TC-74. DFlash2 ya se probó localmente sobre SOL como experimento y no se promovió por la inestabilidad de JSON/xgrammar y falta de suites completas. El fallo histórico de carga INT8 de 2026-10-01 usó vLLM 0.29.0, no la fork 0.30.0 de ExTV, así que no prueba que el repo actual sea incompatible en toda GPU Ampere.

No se declara que el stack ExTV W8A16/FP8 sea matemáticamente imposible en dos 3090: no hay configuración documentada ni checkpoint idéntico aquí. La ruta `capy-flash` v0.5.1 sí queda bloqueada por arquitectura declarada (`sm_120a`) frente a `sm_86`. Para reabrir ExTV harían falta el checkpoint exacto, Python/CUDA y runtime fijados, una partición compatible y un preflight con GPU libre; empezar por smoke de carga + tool call, y después screening emparejado dentro del corte. El banco publicado de 4,28 h no se repetirá.

## Informes y recibos previos revisados

- [Auditoría local INT8 + DFlash2 (2026-10-01)](../../../docs/reddit-qwen38-int8-dflash2-local-check-20261001.md): otro checkpoint W8A16 falló con el wheel 0.29.0 al cargar embedding cuantizado; intento diagnóstico, sin score.
- [DFlash2 local sobre SOL (2026-09-18)](../../../docs/sol-dflash2-local-audit-20260918.md): velocidad corta favorable, JSON/xgrammar inestable; no promoción ni HE20/BCB.
- [NInfer-3090 histórico](../../../docs/ninfer-3090-linux-evaluation-20260908.md): un runtime anterior SM86 de una GPU, BCB 3/8.
- [Topología peer RTX 3090](../Q-20261010-STRATA-DUAL3090-PEER/RESULTS.md): P2P `NS`, sin NVLink.
- [`source-review.json`](receipts/source-review.json) contiene los enlaces y las afirmaciones auditadas.
