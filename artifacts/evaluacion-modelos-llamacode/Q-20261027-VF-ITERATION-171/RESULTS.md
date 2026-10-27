# Q171 — resultados finales de los gates de IA ejecutables en Linux

**Estado:** dos de cinco evaluaciones completadas; tres siguen bloqueadas por datos/artefactos que faltan. Se ejecutaron sólo pruebas de IA. No se hicieron tests generales de LlamaCode, Job Objects, estrés artificial ni nuevas corridas de Swift, PLE o HyperQwen.

## 1. NInfer vs. Strata · Qwen3.8 Flash-Next RCO IQ2_XS

**Diseño.** Mismo artefacto IQ2_XS y los mismos cinco prompts sintéticos, cinco repeticiones intercaladas por engine (25 respuestas cada uno), seeds 4242–4246, una sola solicitud concurrente y la misma RTX 3090 (GPU 1). Contexto 8.192, salida máxima 2.048, KV int8, sin reutilización de prefijo y sampling `temperature=0.6, top_p=0.95, top_k=20, min_p=0, repetition_penalty=1.0, presence_penalty=0`. Ninguno cargó un drafter MTP. Strata retuvo `--spec 2` porque el pack IQ nativo exige esa ventana de verificación; los logs muestran cero drafts aceptados.

| Runtime | Exactitud del fixture | Prefill mediano | Decode mediano | TTFT mediano | E2E mediano |
| --- | ---: | ---: | ---: | ---: | ---: |
| NInfer 0.16.1 Linux preview | 25/25 | 218,75 tok/s | 31,99 tok/s | 0,820 s | 8,243 s |
| Strata 0.1.52 Linux | 25/25 | 310,30 tok/s | 90,30 tok/s | 0,432 s | 2,977 s |

En este fixture, Strata tuvo una mediana E2E 2,77× menor y decode 2,82× mayor. En la recuperación de 1.700 tokens, el prefill mediano fue 1.138,8 tok/s con Strata y 907,4 con NInfer. El arranque de Strata necesitó 811 s para cargar el modelo.

**Lectura y límites.** Los dos engines resolvieron todos los checks exactos de este holdout; esto no estima inteligencia general, seguridad ni calidad de programación. Es una comparación de runtimes en una GPU, no un resultado dual-GPU ni una sustitución de ASTRA/SOL. Strata conservó una ventana `--spec 2` obligatoria sin drafter y empezó las solicitudes con sólo 501 MiB de VRAM libres, por debajo del umbral de aviso de posible paging. Por tanto, el delta de velocidad es prometedor para este perfil, pero requiere una réplica con margen de VRAM suficiente antes de recomendar promoción. No se cambió el perfil productivo.

## 2. Harness² · ASTRA dual RTX 3090, perfil Básico vs. Intermedio

Se conservaron sólo pares con oracle válido. A y B son pares comparables del harness v4 sobre Strata 0.1.41; cada perfil pasó 6/6 aserciones deterministas y no tuvo reparaciones. El par C final es una sensibilidad aparte: usó Strata 0.1.52, nuevas ofertas y el oracle corregido de cinco campos; también ambos perfiles pasaron 6/6 y no tuvieron reparaciones. No mezclo sus tiempos en la mediana A/B.

| Par válido | Runtime / fixture | Intermedio: E2E / tools | Básico: E2E / tools | Resultado |
| --- | --- | ---: | ---: | --- |
| A | Strata 0.1.41 · holdout v4 | 34,413 s / 11 | 61,926 s / 20 | Ambos 6/6; cero reparaciones |
| B | Strata 0.1.41 · holdout v4 | 32,482 s / 12 | 38,751 s / 17 | Ambos 6/6; cero reparaciones |
| C final corregido | Strata 0.1.52 · valores nuevos | 42,581 s / 14 | 134,309 s / 25 | Ambos 6/6; cero reparaciones |

En los dos pares comparables A/B, Intermedio fue más rápido en ambos. Sus medianas fueron 33,448 s frente a 50,339 s para Básico (33,55 % menos). El par C también favoreció a Intermedio, 68,30 % menos tiempo, pero se informa aparte porque cambió el runtime y la variante del fixture. El orden A/B estuvo contrabalanceado; C ejecutó Intermedio primero.

**Configuración.** Qwen3.8 Flash-Next ASTRA RCO IQ2_XS; dos RTX 3090; contexto configurado 1.048.576; seed 4242; herramientas MCP apagadas; red externa aislada y loopback únicamente; sin límite artificial de memoria. Los perfiles comparados fueron `agent-basico` y `agent-intermedio`. Fixture C final SHA-256 `e875e36289ebe25641e85816bf8cdc4648f0ff892305bf55cca30390d00bf8ef`.

**Decisión.** Intermedio fue más rápido en los dos pares comparables y también en la sensibilidad C corregida, sin bajar el resultado determinista. Esto no acredita calidad general, seguridad ni superioridad en programación real: son variantes sintéticas pequeñas, C cambió de Strata y no hay holdout representativo de coding. Antes de cambiar un default, validar ambos perfiles con tareas de programación representativas y criterios de seguridad. Ningún perfil productivo fue modificado.

## 3. Gates bloqueados con condición concreta

- **Qwen/Ghidra:** no existe un target verificable con fuente/hash, entrada, oracle reproducible y revisión humana. No se descargó una ROM ni se sustituyó por el ELF sintético Q138. Reabrir cuando se proporcione el artefacto atribuible y reproducible.
- **Pedido ambiguo del Reel de Instagram:** no hay transcripción/caption primaria accesible y atribuible; el fetch del Reel fue limitado por Instagram. No se inventó transcripción ni se ejecutó una prueba específica de esa fuente. Reabrir al recibir la transcripción o el contenido original.
- **A/B híbrido con proveedor externo:** faltan proveedor/modelo/versiones, un `keyRef` local autorizado, límite de gasto y frontera de datos aprobada. No se llamó un proveedor externo ni se transmitieron datos. Reabrir cuando estén definidos esos cuatro datos.

## 4. Memoria y cierre de procesos

No se impuso límite artificial de RAM/swap. Durante Harness², `MemAvailable` mínimo fue aproximadamente 55,6 GiB; los eventos `high`, `max`, `oom` y `oom_kill` permanecieron en cero. Al cierre: `MemAvailable` 112.639.832 kB, PSI de memoria `avg10=0`, y eventos cgroup OOM en cero. El host reportó GPU0 1.362 MiB usados (GUI) y GPU1 110 MiB; la GUI quedó intacta. El servidor Strata de la prueba y el daemon aislado de LlamaCode fueron detenidos; no quedaron procesos, servicios ni listeners de este test. ASTRA, SOL, PeritoSoft y sus datos no se modificaron.

## Evidencia

- Prerregistro y configuración NInfer/Strata: `receipts/inference-preregistration-v2.json`, `receipts/runtime-configs-v2.json`, `receipts/inference-preflight-v2.json`.
- Resultados crudos NInfer/Strata: `/media/cristian/HDD extra/Modelos-eval/Q-20261027-VF-ITERATION-171/runs/ninfer-strata-paired-v2.jsonl` (SHA-256 `2069c11fe761fb1988bdfd6d3acd0b41750c9c212e3f3ac3deeb8ba91a0ae56e`).
- Prerregistro Harness² final C: `receipts/harness2-astra-dual-preregistration-v5-amendment-05.json`.
- Preflight de Harness²: `receipts/harness2-astra-dual-preflight-v5-final-c.json`.
- Resumen final de Harness²: `/media/cristian/HDD extra/Modelos-eval/Q-20261027-VF-ITERATION-171/harness2-v5/home/harness2-run-final-c/summary.json` (SHA-256 `7c40609c6d068e86023935b4f36178d34199c77925fa54cce7cc17e19ad74166`); eventos de control `control-events.jsonl` (SHA-256 `a68b1436a0c1caf3cffd6d730107556c7ce05e9b2db5d2764f03c9b4e81285f6`). Los pares A/B están en `/media/cristian/HDD extra/Modelos-eval/Q-20261027-VF-ITERATION-171/harness2-v5/home/harness2-run/summary.json`.
- Fixture C final y controlador: `fixtures/harness2-astra-dual-workflow-holdout-v5-final-c.json`; `scripts/run_harness2_final_c_validation.py`.
- El recibo agregado de cierre y hashes queda en `receipts/q171-final-result.json`.
