# Q97 · Swift 1.5 vs ASTRA Flash-Next · BCB-Hard-8

**Estado: completa; gate de promoción/repetición no superado.**

## Decisión

Swift obtuvo **2/8**, igual que ASTRA. Ambos aprobaron exactamente `BigCodeBench/870, BigCodeBench/310` y fallaron los otros seis. La condición preregistrada para habilitar un estudio repetido era Swift ≥3/8 y al menos dos aprobaciones más que ASTRA; no se cumple. **No adoptar Swift ni sustituir ASTRA/SOL.** No repetir el mismo fixture y la misma revisión salvo cambio material de pesos, runtime, sampling o workload representativo.

## Diseño y compatibilidad

A/B serial con el mismo holdout BigCodeBench-Hard-8, seed 4242, contexto 8192, sampling y presupuesto fijados. Swift 1.5 Qwen3.8-27B IQ2_XS estándar en llama.cpp sin MTP; control ASTRA Flash-Next IQ2_XS con Strata/MTP4. Cada brazo usó ambas RTX 3090 y 128 GB de RAM, sin límites de memoria. Las versiones/configuraciones no son idénticas: es comparación de perfiles completos, no efecto aislado del modelo. No representa el contexto ASTRA 1M ni el rendimiento general de todas las tareas.

## Resultados

| Brazo | Calidad BCB-Hard-8 | Transporte | Sandbox / sin contenido | Prefill medio por request | Decode medio por request | Wall E2E medio / total |
|---|---:|---:|---:|---:|---:|---:|
| ASTRA IQ2_XS Strata/MTP4 | 2/8 | 8/8 | 0 / 0 | 366.36 tok/s | 121.61 tok/s | 20.407 s / 163.259 s |
| Swift 1.5 IQ2_XS llama.cpp/no-MTP | 2/8 | 8/8 | 0 / 0 | 538.55 tok/s | 48.34 tok/s | 50.233 s / 401.861 s |

Swift mostró +47.0% de prefill, -60.3% de decode y un tiempo E2E 2.46× el de ASTRA. Es descriptivo de **una semilla y ocho tareas**: no demuestra superioridad estadística, pero tampoco aporta mejora de calidad; los scores quedaron empatados y Swift fue mucho más lento hasta terminar las tareas.

## Detector de presión de memoria

Q94 revisó la evidencia que el usuario señaló. ASTRA DEFAULT a 1.048.576 tokens llegó a 51.14 GiB de RSS y 55.64 GiB mínimos disponibles, sin OOM. La matriz Q35 de ASTRA Flash-Next a 1M completó tres semillas; cada respuesta completa recuperó 8/8, con mínimo disponible de 64.98–65.06 GiB, cero swap y cero OOM; cada request duró ~434.82 s. SOL también completó el A/B vLLM TP2 en las dos 3090 sin OOM (Q34; ~20.4 GiB VRAM por worker y ~103.4 GiB disponibles al readiness), aunque esa corrida no guardó PSI por segundo y **no** sirve para calibrar PSI.

La corrección relevante es separar aviso de parada. Q91/Q93 usaban una parada sensible a PSI full≥20% durante 30 s y abortaron ASTRA con 101/92 GiB disponibles y OOM=0. Eso detectó stalls reales/reclaim, pero no predijo un crash. Q97 usa warning cuando PSI global full avg10≥20% o some≥70% durante 30 muestras; sólo detiene por full≥60% o some≥80% durante 15 muestras, MemAvailable<32 GiB o aumento de OOM. PSI del cgroup es diagnóstico.

En Q97 hubo 928 muestras. Durante la carga ASTRA, PSI global llegó a 34.72% y disparó 64 muestras de warning; bajó a ~0.05% y el brazo completó 8/8 respuestas HTTP, sin crash, error de sandbox u OOM. MemAvailable mínimo fue 71.864 GiB; el pico PSI cgroup 81.53% fue diagnóstico y no alcanzó el límite severo global. Swift no tuvo warning: MemAvailable se mantuvo sobre 105 GiB, PSI 0%, OOM 0.

**Conclusión del detector:** tu observación era correcta. La guarda de Q91/Q93 era demasiado agresiva como criterio de aborto. El detector de PSI sí identifica presión/stalls, pero PSI moderado no es un pronóstico de crash. La política actual avisa y deja continuar en esa zona; hard stops se reservan para PSI sostenida severa, poca memoria disponible u OOM. Q97 confirma esta distinción en vivo y completa sin cerrar Codex. El test Q97 usó contexto 8192; la evidencia 1M proviene de los resultados históricos citados, no de esta corrida.

## Limpieza

Los dos brazos reportaron `healthy_dual_gpu` y terminaron con cleanup propio. El servicio transient quedó `inactive/dead`, resultado `success`; puertos 8363/18789 libres, cero `llama-server` residual. Postflight: 110.46 GiB disponibles, PSI avg10 0%, OOM global 0. GPU0/GPU1: 1064/110 MiB usados. La aplicación gráfica ajena ArtCraft permaneció abierta (PID 3952271, ~207 MiB en GPU0; listener 47413), sin relación con los puertos de inferencia. No se cambiaron límites persistentes, modelos, perfiles, ASTRA, SOL ni archivos productivos.

## Artefactos

- Prerregistro y protocolo: [`PLAN.md`](PLAN.md).
- Resultados crudos: [`ASTRA`](runs/astra/bcb8-result.json) · [`Swift`](runs/swift/bcb8-result.json).
- Guardas y evidencia de memoria: [`revisión del detector`](receipts/q97-memory-guard-review.json), [`postflight`](receipts/q97-cleanup-postflight.json), [`resultado final`](receipts/q97-final-result.json).
- Muestras de recursos: [`host-samples.jsonl`](runs/host-samples.jsonl).
- Historial 1M: [Q35](../Q-20261022-VF-ITERATION-35/RESULTS.md); revisión de umbrales y SOL: [Q94](../Q-20261024-VF-ITERATION-94/RESULTS.md).
