# Q124 · XFUND es.val OCR screen · resultados

**Fecha:** 2026-10-25
**Decisión:** **No integrar Unlimited-OCR Q49** en la extracción documental de LlamaCode.

## Comparación

| Métrica | Tesseract 5.3.4 (CPU) | Unlimited-OCR Q49 (GPU) |
|---|---:|---:|
| Mean CER | 0,229119 | 0,339435 |
| Median CER | 0,219632 | 0,310024 |
| Recall exacto de palabras | 0,846828 | 0,935267 |
| Tiempo medio por página | 1,041 s | 11,408 s |
| Páginas con menor CER | — | 4/12 |

El CER de Unlimited-OCR fue 48,15% mayor que el baseline en esta muestra. Aunque recuperó más palabras anotadas, tuvo más errores de carácter; no alcanzó la reducción ≥15% ni las ≥8/12 victorias exigidas. Por la regla preregistrada no corresponde ampliar el holdout de esta revisión ni integrarla. Los tiempos se informan sólo como observación: Tesseract corrió en CPU y el candidato en GPU, por lo que no constituyen una comparación normalizada de velocidad.

## Ejecución y recuperación del fallo de postproceso

El intento A18 procesó las 12 páginas XFUND hash-seleccionadas: seis secuenciales en la RTX 3090 física 0 y seis después en la física 1. Los dos workers y el guard completaron con código 0, sin abort. El launcher falló al consolidar el resultado (`KeyError: 'seconds'`), porque el scorer de calidad no incluye tiempos en sus filas, aunque los workers sí los registran. No fue un error de inferencia ni del detector de memoria.

A19 fijó un reconciliador offline que une las métricas ya puntuadas con los tiempos de recibos mediante el ID congelado, y verifica hashes del manifest, workers y textos. No recalculó CER ni cambió el parser. A20 ajustó sólo la precisión de una aserción decimal sintética. La regresión pasó 6/6 y la comparación offline terminó con todos los hashes/IDs y 12/12 textos coincidentes. No se repitió inferencia.

## Memoria y protección de la corrida

AMD05 registró 141 muestras durante el screen: MemAvailable mínima 108,184 GiB, cgroup del intento máximo 1,789 GiB, PSI avg10 global/cgroup de 0%, cero swap del intento, cero eventos OOM y ningún motivo de aborto. El servicio quedó inactivo tras terminar. Esto confirma que esta carga no causó un falso stop; no es un estrés de presión severa.

Para la pregunta original del detector, la evidencia relevante de alta memoria sigue siendo ASTRA DEFAULT 1M real: RSS máximo 51,306 GiB y MemAvailable mínima 58,698 GiB, completó sin stop/OOM/swap; Flash-Next 1M completó 3/3 con 64,98–65,06 GiB disponibles; SOL Q34 TP=2 terminó en las dos RTX 3090 sin OOM, aunque no conserva PSI continua. Las pruebas/replays Q116–Q121 encontraron y corrigieron el gap de racha OR en el guard de campaña AMD05, pero ese candidato no está integrado en el guard productivo. No hay evidencia aquí que justifique cortar por RSS alto, cambiar memoria/swap o atribuir el cierre de Codex.

## Auditoría del detector con ASTRA DEFAULT 1M

La corrida real Q117 es la evidencia pertinente para el temor de un falso stop por consumo alto: AMD05 observó 707 muestras mientras ASTRA completaba ~1,00 M de tokens usando ambas RTX 3090. El árbol del proceso llegó a 51,306 GiB de RSS; `MemAvailable` no bajó de 58,698 GiB. La PSI avg10 máxima fue 53,61% en host y 94,77% en cgroup. Hubo 216 avisos moderados, pero ningún stop, OOM ni swap. Como el headroom se mantuvo sobre el umbral de 48 GiB, el candidato AMD05 conservó la corrida sin tratar RSS o PSI por sí solos como condición de parada. El replay independiente de la traza pasó 12/12 checks (Q118).

Esto responde afirmativamente para AMD05 en el caso real ASTRA: el uso alto que ya demostró ser viable no fue interrumpido. SOL Q34 también terminó sin OOM usando las dos RTX 3090, aunque no tiene PSI continua y por eso no prueba el comportamiento del detector. El screen OCR A18 fue liviano y tampoco es un estrés severo. AMD05 sigue siendo candidato y no está integrado en producción; el gap histórico de Q97/Q100 ante PSI severa alternante permanece. No se creó presión artificial ni se atribuyó el cierre de Codex al detector.

## Alcance

- Muestra: 12 de 50 páginas `XFUND v1.0 es.val`, seleccionadas antes de inferencia por hash.
- Candidate: Baidu Unlimited-OCR Q49, revision `8249d20b2822a7d8a4c22c8d8c9069b5ac36bda3`, pesos SHA fijados en el prerregistro.
- Parser Q49 y scores originales conservados; texto OCR crudo continúa sólo local.
- Ningún cambio a producción, ASTRA DEFAULT, Flash-Next, SOL, PeritoSoft, contexto, RAM o swap.

## Recibos principales

- Prerregistro: `PLAN.md`, `receipts/preregistration.json`, enmiendas A19/A20.
- Comparación final: `outputs/a18-xfund-screen/comparison-q124-offline.json`.
- Regresión offline 6/6: `receipts/attempt15-a19-synthetic-regression.json`.
- Reconciliación y memoria: `receipts/attempt16-a19-offline-comparison.json`.
- Inferencia/monitor original: `outputs/a18-xfund-screen/receipts/guarded-inference-a18-xfund-screen.json`, workers GPU0/GPU1 y `memory-monitor-a18-xfund-screen.jsonl`.
