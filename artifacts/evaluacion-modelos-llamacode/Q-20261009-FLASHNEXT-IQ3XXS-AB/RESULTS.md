# Evidencia de Q-20261009-FLASHNEXT-IQ3XXS-AB

Fecha: 2026-10-09. Fuente solicitada: post de r/LocalLLM sobre Flash-Next Q4, KV q8, contexto 262K, cuatro P100 PCIe 3 x8, 128 GB DDR4-2133 y E5-2683 v4. El material textual está en `source-reddit.txt`.

## Conclusión provisional

No promuevo el IQ3_XXS/Strata a producción. En el A/B local, HE20+BCB8 terminó 24/28 para IQ3_XXS (BCB8 4/8) y 28/28 para ASTRA IQ3_S calibrado (BCB8 8/8). ADV v1 complementaria cerró 10/10 en ambos tras dos reparaciones (primera pasada 7/10 vs 8/10); TaskFlow ULTRA terminó 11/13 vs 13/13. La suma descriptiva HE20+BCB8+ADV+TaskFlow fue 45/51 vs 51/51. En dos pasadas, Server Speed dio 126,59 vs 122,09 tok/s, diferencia pequeña frente a la variación; TTFT de IQ3_XXS fue menor en ambas. El A/B usa dos RTX 3090, IQ3_XXS, Strata v0.1.41 y contexto 131K; no replica el hardware, Q4, 262K ni el control llama.cpp del post. Ver informe técnico y limitaciones en `../../../docs/qwen38-flashnext-iq3xxs-strata-20261009.md` y el resumen acumulativo en `../../../docs/evaluacion-modelos-llamacode.md`.

## Estado de contexto

La sonda sintética 115K bajo `max-context=131072` llegó a 65.536/115.015 tokens y se desconectó durante el transporte, sin respuesta ni `usage` válido; es inválida por transporte y no puntúa calidad. El smoke separado de 262K preparado para el post Q4/4×P100 quedó bloqueado antes de cargar el engine: la guarda requería MemAvailable ≥32 GiB y swap usado <2 GiB, pero se observaron 110,564 GiB disponibles y 3,253 GiB de swap usado. No se generó ni envió prompt de 262K y no hubo solicitud al modelo. No es un fallo de calidad. Ninguno de estos probes sustituye la medición de cold prefill/compactación a 128K, encolada como Q-20261009-STRATA-COLD-PREFILL-128K.

## Recibos y límites

`receipts/` contiene configuraciones, suites, JSON de calidad/velocidad y capturas originales de corridas; `benchmark-runs/` incluye workspaces generados por los agentes y sus event logs. No se copiaron perfiles productivos, settings activos ni pesos de modelos. `source-reddit.txt` conserva el archivo aportado. `SHA256SUMS.txt` y `manifest.json` cubren los archivos de evidencia y fixtures; ambos excluyen los `.pyc` de `__pycache__`, y cada índice documenta las excepciones de autorreferencia en `SHA256SUMS-NOTES.md`. El detalle de hashes de modelos, suites, HarnessSpec, corpus, hardware y runtime está en el informe y en el documento canónico.

No se cambiaron perfiles productivos, HarnessSpec ni sampling. `profiles/launches.json` tenía cambios previos y se preservó.
