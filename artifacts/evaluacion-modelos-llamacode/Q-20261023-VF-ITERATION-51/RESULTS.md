# Resultados — Iteración 51

Fecha UTC: 2026-10-23T01:52:13.514561Z

- RCO Coder: la revisión oficial actual y la revisión Q27 probada son idénticas en los 13 archivos del repositorio; hashes de ambos shards coinciden con el recibo de descarga local. El anuncio de mejora ya estaba dentro del artefacto medido. No se re-descargó ni repitió el screen 0/8 frente a 1/8.
- Swift: se encontró una nueva candidata directa a Flash-Next, `ukisai/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-GGUF` IQ2_XS. Strata 0.2.2 / engine 0.1.47 la documenta como familia soportada. Se registró el screen local pareado a ASTRA; el modelo reporta 68.15 GB y requiere reservar suficiente espacio. KLD/contexto-512 del publicador no se considera prueba de calidad agentiva.
- Licencia: Swift Open License v1.0 limita el uso comercial de entidades que superen US$1M de ingresos brutos consolidados (incluidas entidades bajo control común); por encima requiere licencia empresarial escrita. Se preguntó al usuario el dato aplicable. Hasta tenerlo no se descarga ni se ejecuta el modelo.
- Windows: el usuario indicó que hizo el arreglo allí, pero la sesión actual de Codex se mantiene en Ubuntu/Linux y no expone PowerShell, CMD ni el montaje `/mnt/c`; los tests Windows siguen pendientes para una sesión nativa.
- Inferencia/GPU/build: ninguno en Q51. Ningún modelo productivo se cambió ni eliminó.

Próximo paso habilitante: confirmación de elegibilidad de Swift; después, preflight fresco de inference/GPU y ejecución serial del screen preregistrado en `PLAN.md`.
