# Auditoría de OpenJev para LlamaCode

Fecha: 2026-09-18.

## Qué es

`AlexWortega/openjev` no es un chat model ni un checkpoint causal para
`llama-server`. Es `Qwen3_5ForSequenceClassification`, un cross-encoder NLI de
4B que recibe un par `premise/hypothesis` y devuelve tres clases:

- `entailment`;
- `contradiction`;
- `neutral`.

El propio model card describe usos como reranking, grading, guardas de
contenido y decisiones entre opciones. También declara una torre visual de
Qwen3.5, pero la salida sigue siendo una clasificación, no texto generado ni
una llamada de herramienta.

## Comprobaciones realizadas

Se consultaron el model card, el árbol de archivos y `config.json` del repositorio:

| Comprobación | Resultado |
|---|---|
| Arquitectura | `Qwen3_5ForSequenceClassification` |
| Clases | 3: contradiction / entailment / neutral |
| Pesos disponibles | `model.safetensors`, ~9,08 GB; no GGUF |
| Entrada | Par de textos con plantilla NLI |
| Salida | Logits/probabilidades de clasificación |
| Visión declarada | Sí, mediante la torre visual; salida clasificatoria |
| Compatible directamente con perfiles LlamaCode | No |
| Candidato para reemplazar SOL, Occamy o QWEN35-A3B | No |

La comprobación fue deliberadamente estática: no se descargaron los ~9 GB ni
se instaló una segunda pila PyTorch/Transformers porque el runtime local de
LlamaCode usa GGUF/`llama-server` para los perfiles y no puede cargar una
arquitectura de clasificación como endpoint generativo. Descargarlo sin una
ruta de integración no produciría una métrica PP/TG, BCB ni tool-use comparable.

## Dónde sí podría servir

LlamaCode ya contempla un sidecar opcional de embeddings/reranking. OpenJev
podría adaptarse como servicio Python separado que exponga `/rerank` y traduzca
cada candidato a un par NLI:

```text
premise: estado, petición y restricciones del usuario
hypothesis: respuesta o plan candidato
```

La puntuación de `entailment` podría ayudar a ordenar planes, verificar que una
respuesta cubra requisitos o descartar contradicciones antes de mostrar un
resultado. Eso sería una mejora de selección/verificación, no una mejora de la
calidad generativa del modelo principal.

## Decisión

No se agrega OpenJev a `assets/system_profiles.json`, no se modifica el
dropdown y no se cambia ningún default. No es superior a nuestros perfiles en
PP, TG, BCB, contexto o tool-use porque no cumple la misma tarea.

Queda registrado como candidato de sidecar `reranker/verifier`. Para retomarlo
sin repetir esta investigación habría que implementar primero un adaptador
estable `/rerank`, instalar una venv aislada en el disco con espacio y medir:

1. precisión de ranking sobre respuestas reales de SOL, Occamy y QWEN35-A3B;
2. falsos positivos de `entailment` en código y tool-calls;
3. latencia CPU/GPU y memoria concurrente;
4. impacto end-to-end del harness frente a no usar reranker.

Fuentes:

- [Model card oficial de OpenJev](https://huggingface.co/AlexWortega/openjev)
- [Laboratorio OpenJev y comparación de decisión local](https://openjev.com/)
