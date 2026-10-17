# Resultados — Q-20261017-DS4-STARFORGE-EVAL

**Estado:** auditoría documental completa; compatibilidad local no aplicable.
**Decisión:** sin promoción de modelo/perfil y sin cambios de harness/producto.

## Comprobaciones ejecutadas

| ID | Resultado | Evidencia |
|---|---|---|
| P1 — plataforma | No aplicable al candidato: host `Linux x86_64`, dos RTX 3090 SM 8.6; no hay `xcrun` ni `system_profiler`. `sf-q3-8flash` exige Apple Silicon/macOS/Xcode y Metal. | [preflight](receipts/platform-preflight.json) |
| P2 — artefacto local | No se encontró binario, checkout o referencia del candidato en el workspace. | [preflight](receipts/platform-preflight.json) |
| P3 — fuentes / harness | Revisados README de StarForge y `sf-q3-8flash`, guía de Qwen, registro de performance/upstream PR y documentos locales Server Speed / KV-cache. | [revisión de fuentes](receipts/source-review.md) |

P1 y P2 son comprobaciones read-only. No se construyó ni descargó el motor o
los pesos, no se cargó un modelo ni se ejecutó inferencia. La ruta CPU del
candidato es una referencia/debug según su documentación y no produciría el
resultado Metal que se quiere medir. La tabla completa de pruebas no ejecutadas
por incompatibilidad está en [PLAN.md](PLAN.md). La triage inicial incluyó un
chequeo de plataforma read-only antes de guardar el plan; se registró la
desviación y se repitió P1 después del preregistro.

## Lectura por uso de LlamaCode

| Uso | Resultado para esta fuente |
|---|---|
| Coding/agentes | No hay evaluación local de calidad. El servidor anuncia tool calls compatibles, pero el fork no incluye agente; hace falta cliente externo y un screen LlamaCode en hardware/backend compatible. |
| Computer Usage | No evaluado. Soporte de tool calls HTTP no equivale a E2E de escritorio, ejecución de acciones ni verificación de estado. |
| Ingi-Charla | No aplica como sustituto: la publicación no ofrece ASR/TTS ni evidencia acústica. |
| Visión | Hay ruta de imágenes con encoder Qwen3-VL; no hay resultado local. La prueba local anterior de IQ3_XXS/Strata ya registró 5/7 conteos de color y no se repitió. |
| Contexto | Documenta 262.144 tokens nativos y YaRN más allá; el límite configurado no prueba recuperación. La prueba previa de IQ3_XXS a 115K ya pasó 10/10; los intentos 262K quedaron abortados por guardas de recursos y no se repitieron. |
| Rendimiento | Los números del mantenedor son M5 Max/Metal. No se comparan con las RTX 3090 locales ni con perfiles Strata/CUDA, vLLM o llama.cpp. |
| Harness | La disciplina de paridad y telemetría es buena referencia. LlamaCode ya tiene A/A, AB/BA, intervalos pareados, hashes de perfil/corpus, cold/warm, contexto y concurrencia. No se identificó una mejora que requiera cambio ahora. |

La documentación del fork declara ganancias para Qwen3.8 Q2/Q4 en el M5 Max y
una batería de identidad de tokens/logits/MTP; no se replicó de forma
independiente en este entorno. Un test válido requeriría el Apple Silicon,
runtime, cuantización, merge-base y pesos exactos que el reporte compara, y
después un A/B de calidad con un cliente LlamaCode compatible.

## Decisión y límites

No repetir IQ3_XXS/ASTRA ni alterar recomendaciones vigentes. No se ejecutan
`make`, kernel/MTP/visión tests, parity oracle ni `speed-bench` del fork porque
el host no dispone de Metal ni del runtime/modelo. No corresponden build ni
tests del producto LlamaCode: no hubo cambios de C++/QML/core.

Siguiente oportunidad útil: acceso a un Mac Apple Silicon con el perfil de
memoria/recurso que permita cargar el GGUF seleccionado, fijar el commit del
hijo y su merge-base de `ds4`, reutilizar el harness LlamaCode con tres seeds
para coding/agentes y separar Computer Usage, visión y contexto de las medidas
de velocidad. No arrancar por tests repetidos del mismo fixture IQ3_XXS.
