# Auditoría de SalesRLAgent / Jev para LlamaCode

Fecha: 2026-09-18.

## Qué aporta el material

El repositorio `DeepMostInnovations/sales-conversion-model-reinf-learning` no
es un modelo general de coding ni de control de PC. Es un agente PPO
especializado en conversaciones comerciales: estima una probabilidad de
conversión turno a turno a partir de embeddings y métricas derivadas por un
LLM. El paper declara un espacio de acciones continuo de 0 a 1 y una tarea
vertical de ventas, no generación de código, tool-calls ni planificación de
escritorio.

La segunda idea, más general, es el routing consciente de confianza antes de
generar: usar señales de incertidumbre para elegir generación local, RAG,
escalamiento a un modelo más capaz o revisión humana.

## Comparación con LlamaCode

| Idea del material | LlamaCode actual | Decisión |
|---|---|---|
| Estimar dificultad/confianza | `DifficultyRouter` evalúa tokens, archivos afectados, fallos, ciclos y confianza | Ya cubierto |
| Escalar cuando hay baja confianza | `ask_teacher`, cadena de maestros y `autoAfterFails` | Ya cubierto |
| Verificación posterior | roles `verifier` y tools de verificación | Ya cubierto |
| Reranking/selección | rol `reranker` y scheduler auxiliar opt-in | Ya cubierto como extensión |
| PPO de ventas | No corresponde a coding/control de PC | No integrar |
| Probabilidad discreta sobre opciones | Podría servir para un futuro clasificador de decisiones, no para generar código | Investigación separada |

## Pruebas realizadas

Se verificaron el paper, el model card, la arquitectura declarada y el modo de
uso. El checkpoint está pensado para Stable-Baselines3/PPO y el ejemplo usa
`unsloth/Qwen3-4B-GGUF` como LLM auxiliar para métricas dinámicas. No ofrece un
endpoint GGUF/OpenAI-compatible para el agente y su dataset es de conversaciones
SaaS sintéticas, por lo que no es una medición transferible a BCB, HE0, HE20,
tool-use o control de PC.

No se descargó el checkpoint ni el dataset: hacerlo agregaría una dependencia
Python específica y un modelo vertical sin una tarea local que validar. Tampoco
se modificó el router existente, porque la funcionalidad equivalente ya está
implementada y probada en LlamaCode.

## Resultado

No se agrega ningún perfil nuevo ni se cambia SOL, Occamy o QWEN35-A3B. La
única mejora reutilizable es conceptual y ya está presente: mantener el
escalamiento basado en fallos/confianza, con verificador y reranker optativos.

Un experimento futuro razonable sería conectar OpenJev —la variante NLI
documentada en `openjev-audit-20260918.md`— al rol `reranker/verifier` y medir
falsos positivos y latencia sobre respuestas reales de LlamaCode. Eso sería un
sidecar de validación, no un reemplazo del modelo principal.

Fuentes:

- [SalesRLAgent en arXiv](https://arxiv.org/abs/2503.23303)
- [Confidence-Aware Routing en arXiv](https://arxiv.org/abs/2510.01237)
- [Checkpoint de SalesRLAgent](https://huggingface.co/DeepMostInnovations/sales-conversion-model-reinf-learning)
- [Dataset SaaS de entrenamiento](https://huggingface.co/datasets/DeepMostInnovations/saas-sales-conversations)
