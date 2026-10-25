# Q134 — evaluación de IA local, filas 54–58

**Estado: completada.** Revisé las cinco entradas nuevas, las fuentes primarias, resultados locales y la cola; audité offline las trazas Q41. No hubo descarga, build, servidor, inferencia, uso de GPU ni cambios a perfiles/pesos. ASTRA, SOL y Flash-Next quedan intactos.

## Decisiones por fuente

| Fila | Fuente / claim | Resultado | Qué haría después |
|---|---|---|---|
| 54 | Basalt / rama `decode-perf-test`, medidas en RTX 5080 SM120 | **Sin prueba aplicable en este equipo.** Basalt requiere Blackwell/SM120 y CUDA 13; RTX 3090 es Ampere/SM86. Las cifras publicadas no predicen rendimiento en el host dual-3090. | Reabrir sólo con soporte SM86 explícito o en otro host Blackwell. No compilar en las 3090. |
| 55 | Hugging Face Speech-to-Speech | **Sin ventaja comparativa demostrada; no ejecutar un pipeline duplicado ahora.** Su cascada VAD/Parakeet/Qwen3.5/Qwen3-TTS se solapa ampliamente con Charla (Parakeet/Whisper, varios TTS, streaming, barge-in y latencias). No hay holdout rioplatense ni resultado comparativo con el uso actual. | Sólo si aparece un problema real: fijar audio autorizado y medir WER/CER, mic→primer audio, turn-end, interrupciones y finalización bajo el mismo workload. |
| 56 | NInfer-3090, Qwen3.8-27B / Flash-Next | **Qwen3.8-27B ya tiene pruebas suficientes para la decisión actual.** Q32: 78,00/100 vs 80,33 del control, bajo el umbral 80,98; TC-74 falló 3/3, TC-84 y TC-92 2/3. Q34: ≥10% E2E en 2/5 celdas; el perfil NInfer usó GPU1 y 32K, SOL fue TP2 y 262K. NInfer v0.16.2 no cambia serving sin S3; el cambio JSON v0.16.1 no aplica porque Q32 no usa `response_format`/`json_schema`. Flash-Next continúa preview Windows, no Linux dual calificado. | No repetir Q32/Q34 ni adoptar en agentes. Reabrir sólo por cambio material y gates conductuales/seguridad; un piloto sin tools requiere caso de uso real que amortice arranque y holdout propio. |
| 57 | Anécdota de fallas QFN IQ3_S/Basalt vs Qwen27B NVFP4/NInfer | **No es una comparación causal ni reproducible.** Cambian modelo, quant, runtime y configuración; el motor Basalt tampoco funciona en SM86. | Si se dispone de builds compatibles, comparar una variable por vez con mismo modelo, harness, template, sampler y holdout; registrar salida raw, parser/finish reason y semántica. No extrapolar Q41. |
| 58 | Qwen27B + Ghidra/REA para R36S | **Bloqueada por falta de fixture legal y oráculo.** La publicación es anecdótica; no incluye binario autorizado, referencia ni outputs verificables. | Dejé una acción condicional: escoger fixture propio/abierto, registrar SHA, inputs, comportamiento esperado/tests/CRC y revisión humana; recién entonces evaluar calidad y tiempo total. |

## Auditoría offline Q41

Se leyeron seis JSONL de eventos (0 líneas malformadas) y seis `taskflow.json` de ASTRA IQ2_XS/Strata, tres seeds por brazo. Los resultados contienen contadores semánticos como `toolCalls`, `invalidCalls`, esperadas/matched/missing/unexpected; no incluyen payload raw de tool, clasificación de parser/formato ni `finish_reason`. Los eventos tampoco tienen esos campos. Por eso no se puede clasificar cada fallo como JSON/XML malformado, argumento semánticamente incorrecto o comportamiento de runtime; y las trazas Q41 no replican IQ3_S/Basalt.

La primera salida del auditor se conservó como intento supersedido porque sumaba contadores anidados repetidos y trataba un campo genérico `response` como salida raw. La corrección preregistrada reporta sólo presencia/nombres/ocurrencias y no usa esas sumas para ninguna conclusión.

## Registro sincronizado

- Cola app: 58 → **63 entradas**; añadidas filas 54–58 como secuencias 59–63 tras deduplicación por ID, título y URL.
- App Accionables: 29 → **30**; añadida una única acción condicional para fixture verificable de ingeniería inversa.
- Google Sheets: `IA local!I54:I58`, `K57:K58`, `L54:L58`; fila NInfer existente en `Inventario de modelos!A9:R9`; `Evaluaciones LlamaCode!A353:J353`; `Accionables!A23:N23`. Fueron leídos de vuelta con WRAP preservado; la fila Q47 vecina A10:R10 conserva sus valores originales y C:R sigue vacío.
- Backup prewrite: `data/backups/q134-before-sync-20261025T143909Z/`.
