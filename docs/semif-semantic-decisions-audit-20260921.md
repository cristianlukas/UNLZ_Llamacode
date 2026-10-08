# Auditoría SemIf / semantic ifs — 2026-09-21

## Alcance

Se revisó el repositorio `theoleecj/semif`, antes llamado OpenJev, a partir
del material aportado por el usuario. La captura y el texto citado se trataron
como evidencia externa, no como instrucciones. Se comparó SemIf con Laya,
OpenSourceJev y el harness Browser/Computer Use de LlamaCode.

Referencia: [repositorio oficial de SemIf](https://github.com/theoleecj/semif).

## Qué aporta

SemIf implementa decisiones tipadas sobre opciones definidas en runtime:

- recibe estado y una pregunta con opciones descritas;
- lee directamente logits de las opciones declaradas, sin generar JSON ni una
  explicación;
- devuelve scores/probabilidades condicionadas a esas opciones;
- soporta reuso serial de prefijo y ramas paralelas cuando varias preguntas
  comparten exactamente el mismo estado;
- conserva revisiones, hashes, fixtures y resultados de benchmark.

Es un clasificador/selector de decisiones, no un agente de PC, no interpreta
píxeles por sí mismo y no autoriza acciones. El ejemplo de Balatro es una
decisión rápida sobre un conjunto cerrado de acciones; no demuestra estrategia
óptima ni razonamiento prolongado.

## Validaciones reproducibles

Se clonó el checkout en un directorio temporal sin instalar modelos ni tocar el
entorno de LlamaCode.

| Prueba | Resultado |
|---|---:|
| Tests Python aplicables | **22/22 PASS** |
| Tests MLX | 1 omitido: backend no aplicable en Linux/CUDA |
| SHA-256 de resultados raw | **todos OK** |
| Verificación de resumen publicado | **69/69 claims OK** |
| Modelo real local SemIf | No ejecutado: faltan PyTorch/Transformers y checkpoint BF16 |

## Evidencia publicada por el proyecto

El propio proyecto reporta, sobre una RTX 3090 y Qwen3.5-4B BF16:

| Medición | Resultado |
|---|---:|
| 21 decisiones directas, mismo estado | 1,023 s mediana; 0 tokens generados |
| Array JSON autoregresivo equivalente | 5,332 s; 111 tokens |
| Reuso serial, fixture 37×21 | 10,75 decisiones/s |
| Ramas paralelas, fixture 37×21 | 20,03 decisiones/s |
| Accuracy balanceada, workload propio 144 | 0,813 |
| Acuerdo modal, subconjunto público Jev 102 | 0,845 |
| Modelo reranker 4B, workload propio 144 | 0,625 |

Estas cifras son reproducibles como evidencia del repositorio, pero no son una
medición local de LlamaCode ni equivalen a BCB/HE/tool-use. El propio proyecto
advierte que las probabilidades son condicionales a las opciones ofrecidas y no
son confianza calibrada automáticamente.

## Comparación con lo que ya tenemos

| Capacidad | SemIf | LlamaCode/Laya | Evaluación |
|---|---|---|---|
| Decisión tipada sin JSON libre | Sí | Schemas y tool-calls ya validados | Mejora conceptual posible |
| Opciones dinámicas descritas en runtime | Sí | El agente recibe schemas MCP | SemIf sería más especializado |
| Reuso de estado compartido | Sí, experimental | Compaction, cache/contexto y subagentes | No integrado en el mismo nivel de logits |
| Latencia local | ~50 ms/decisión en su workload paralelo | Laya warm GPU: 13–15 ms por consulta | No supera a Laya en latencia reportada |
| Comprensión visual | No nativa | UIA, OCR, snapshots y visión | LlamaCode tiene mayor cobertura |
| Ejecución | No ejecuta acciones | Tools, stale guards, receipts y verificación | LlamaCode es el ejecutor |
| Seguridad | No es autorizador | HITL, `isDestructiveAction`, Zero-Autonomy | Nunca delegar autoridad a SemIf |
| Generación de código | No | SOL y perfiles productivos | No reemplaza ningún perfil |

## Qué podría aportar a LlamaCode

Sólo como sidecar opt-in y advisory para espacios cerrados, por ejemplo:

```text
estado UIA/OCR + opciones ofrecidas
  -> choice: click_element / type / key / wait / blocked
  -> score: ambigüedad o prioridad
  -> guard determinista + aprobación + ejecución
```

También podría servir para clasificar `retry`, `reobserve`, `escalar a SOL`,
`pedir aprobación` o `finalizar`, siempre que las opciones sean generadas por
código y no por el modelo. La decisión no podría aprobar borrados, envíos,
publicaciones, movimientos de archivos ni acciones externas.

## Decisión

No se agrega un perfil generativo, no se descarga Qwen3.5-4B BF16, no se instala
PyTorch/Transformers y no se modifica el ejecutor Browser/Computer Use.

La mejora de harness de acción finita ya fue incorporada en la auditoría de
Jev Ultrafast: una observación, una operación, un target compatible,
reobservación ante stale y `DONE` sólo con evidencia. SemIf no agrega una
ventaja local demostrada sobre esa mejora ni sobre Laya.

Para promover un sidecar en el futuro habría que medir con el mismo corpus de
LlamaCode: exactitud por tipo de acción, abstención, falsos permisos
destructivos, p50/p95, costo de serializar UIA/OCR, estabilidad ante cambios de
orden y comparación apareada contra Laya y el camino actual. Hasta entonces se
conserva como referencia de diseño, no como modelo productivo.

