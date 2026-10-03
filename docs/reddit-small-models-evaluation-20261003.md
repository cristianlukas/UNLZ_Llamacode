# Modelos pequeños del hilo de LocalLLaMA · evaluación local

Fecha: 2026-10-03. Se revisó el hilo pegado sobre modelos pequeños, QAT y
delegación de tareas, y se compararon los candidatos que podían aportar algo a
LlamaCode con el perfil local Qwen3.5-4B.

## Decisión

**No promover ni cambiar perfiles, el harness, Computer Use o Ingi-Charla.**
Spark-X2.5-4B obtuvo una tarea más que Qwen3.5-4B en una pasada de
BigCodeBench-Hard-8 (2/8 frente a 1/8), pero empató en el contrato de tools,
perdió un caso de seguridad en el orden sandwich de Computer Use y no tiene
entrada visual. Un punto en ocho casos no justifica convertirlo en worker
productivo; necesita un A/B agentivo repetido antes de recomendar su descarga.

Gemma 4 E4B QAT fue rápido y acertó el control visual, pero logró 4/5 en el
contrato de tools y 0/8 en BigCodeBench-Hard-8. No supera al Qwen3.5-4B actual
para el uso general medido. Su cuantización QAT tampoco demuestra por sí sola
una mejora para coding o Computer Use.

Ingi-Charla no cambia: los tests aquí miden diálogo textual, selección de
acciones y tools, no WER/CER, turnos de audio ni latencia STT→LLM→TTS. Que Gemma
4 E4B acepte audio en el modelo base no reemplaza el pipeline de voz ya probado
en [`ingicharla-local-voice-audit-20260918.md`](ingicharla-local-voice-audit-20260918.md).

## Banco y protocolo

- Ryzen 9 9950X3D, 123 GiB RAM, 2× RTX 3090 SM86, Ubuntu 24.04.
- Runtime aislado `llama.cpp` CUDA, commit `836d571` (2026-10-03), construido
  en `~/.cache/llamacode/` para no compilar desde NTFS. Sólo se usó CUDA1 para
  las pruebas de texto mientras estuvo libre.
- Qwen3.5-4B Q4_K_M: pesos locales del perfil existente.
- Gemma 4 E4B oficial QAT Q4_0 y Spark-X2.5-4B Q4_K_M: descargas de prueba
  fuera del repo. Spark requiere un llama.cpp posterior a b10828; el runtime
  anterior instalado en el equipo no servía para esa arquitectura.
- Computer Use de opciones: corpus duro de 24 estados, 3 pasadas (72 respuestas
  por modelo), comparando `state-first`, `question-first` y `sandwich`; no se
  ejecutó ninguna acción real.
- Tool contract de leer README y escribir un archivo: 5 pasadas por modelo.
- Visión con tool: fixture UI existente, 3 pasadas; sólo propone una acción, no
  la ejecuta. Durante esta parte un proceso Strata ocupó VRAM en ambas tarjetas;
  Qwen y Gemma se midieron con 12 capas en GPU y proyector en CPU.
- Coding: BigCodeBench-Hard-8, primera respuesta, sin reparación, aislado con
  bubblewrap y tests ejecutados localmente; una pasada por modelo. No confundir
  este control directo con el score del harness LC-H1.

La imagen de comparación no es el modo de implementar Computer Use: es una
regresión puntual para evaluar el target visual en un fixture, de acuerdo con
la regla del repo de mantener el motor general.

## Resultados

| Modelo | Computer Use `state-first` | `sandwich` (seguridad) | Tool contract | Visión con tool | BCB-Hard-8 directo | Decisión |
|---|---:|---:|---:|---:|---:|---|
| Qwen3.5-4B Q4_K_M | 72/72 · 100% | 72/72 · 100% | 5/5 | 3/3 | 1/8 | Mantener como perfil 4 GB general/visión |
| Gemma 4 E4B oficial QAT Q4_0 | 72/72 · 100% | 69/72 · 95,83% (seguridad 20/21) | 4/5 | 3/3 | 0/8 | No promover |
| Spark-X2.5-4B Q4_K_M | 72/72 · 100% | 69/72 · 95,83% (seguridad 21/21) | 5/5 | No aplica: no se cargó entrada visual | 2/8 | Candidato de coding sin evidencia suficiente |
| Gemma 4 E4B no-QAT Q4_0 | 0/72 respuestas con formato válido | 0% válidas | 4/5 | — | — | No usar como control de capacidad: incompatibilidad de formato con el fixture/prompt probado |

Latencia mediana state-first / sandwich (API completa, generación de letra de
salida): Qwen **134,70 / 152,23 ms**, Gemma QAT **58,71 / 54,74 ms**, Spark
**68,90 / 76,75 ms**. El gate de la suite no pasó para los tres: Spark y Gemma
perdieron un estado de sandwich frente al control; Qwen mantuvo exactitud, pero
el orden sandwich fue 13% más lento que state-first. La latencia de esta prueba
corta no predice TPS en coding largo.

El error aislado de tool contract de Gemma QAT fue una segunda llamada
`read_file` donde se esperaba `write_file`. Qwen y Spark completaron la secuencia
exacta en las cinco pasadas. El Gemma no-QAT respondió con frases de
razonamiento en lugar de una letra; por eso se registra como inválido para este
contrato estricto, no como 72 acciones incorrectas.

El 2/8 de Spark comparte los ítems `870` y `310`; Qwen pasó sólo `870`. Es una
señal para un benchmark de coding agentivo futuro, no evidencia de que Spark
reemplace el perfil. El control no incluyó planificación, reparación o tools en
coding; la suite tool contract sólo cubre el round-trip básico.

## Vínculo con las pruebas previas

- Qwen3.5-4B ya tenía HE20 20/20 y BCB8 directo 1/8 en las pruebas previas; el
  BCB de esta auditoría vuelve a dar 1/8 bajo el runtime común nuevo.
- El comentario del perfil `sys-vram-4-gemma` ya registra un A/B distinto para
  Gemma E4B **Heretic QAT** frente al QAT base, Agent Efficiency E2E v1 5/11
  frente a 2/11. Ese checkpoint SC117 no estaba descargado en este banco y no
  debe confundirse con el GGUF oficial `google/gemma-4-E4B-it-qat-q4_0-gguf`
  probado aquí. No encontré el recibo de esa corrida en `docs/` o `artifacts/`;
  la anotación previa se conserva como dato del catálogo y esta prueba no la
  repite ni la sustituye.
- El harness de LlamaCode ya ofrece roles pequeños, perfiles multi-modelo y
  ejecución de tools. Este hilo no aporta razón para cambiar el router ni para
  delegar código automáticamente a un modelo con sólo una pasada BCB de ventaja.

## Repetición y artefactos

No volver a ejecutar estas mismas combinaciones como si fueran evidencia nueva.
Para reevaluar Spark, usar una versión nueva del protocolo y al menos 3 pasadas
LC-H1 con el mismo runtime, presupuesto y herramientas que Qwen; conservar
separadas Computer Use visual y voz acústica.

Resultados completos, incluidas respuestas y tiempos por caso:
[`artifacts/reddit-small-model-evaluation-20261003/`](../artifacts/reddit-small-model-evaluation-20261003/).
El modelo oficial QAT pesa 5.154.941.280 bytes, SHA-256
`676c35070db6dbe52f93e9c864ee0fba4eddea94b9c875d9cb10daff453fbaee`; Spark
Q4_K_M pesa 2.600.224.352 bytes, SHA-256
`adfcfa19a4ed6a5985da8bf565fe15f8e1a7e131d79bae2d19d48d1c40109428`. Los pesos
quedan en el root local de modelos, fuera del repo.

Fuentes primarias consultadas: [ficha oficial Gemma 4 QAT en Hugging Face](https://huggingface.co/google/gemma-4-E4B-it-qat-q4_0-gguf) y [ficha oficial Spark-X2.5-4B](https://huggingface.co/XHToken/Spark-X2.5-4B). Los resultados del model card de Spark son publicados por sus autores; esta decisión se basa en las pruebas locales apareadas descritas arriba.
