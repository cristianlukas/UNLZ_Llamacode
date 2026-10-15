# Plan — Q-20261015-ANYJEV-EVAL

## Pregunta y decisión que se medirá

¿AnyJev `Decider` L0 mejora, sobre el mismo modelo local, la clasificación de
la ruta de manejo para solicitudes de LlamaCode frente al `raw` de logits del
siguiente token? El alcance es asesoría tipada de routing. El candidato no
puede aprobar ni ejecutar acciones; las aprobaciones, bloqueos y guards del
harness siguen siendo deterministas.

La publicación usa Qwen3-8B/BANKING77 (20 opciones, 300 ejemplos), que no es un
resultado para LlamaCode. Sus cifras de accuracy/ECE/cobertura sólo motivan el
screen. L0 corrige sesgo de posición/prior sin etiquetas, pero no calibra
confianza frente a resultados etiquetados; la versión 0.3.0 ya no contiene
L1/L2.

## Fuentes y candidato local

- Fuente publicada: AnyJev v0.3.0, commit de publicación
  `1ffa57b5287572cd173e1dc83d8a8f2e8dedca00`, rueda PyPI
  SHA-256 `24217f23eecb3859353d625b89e0047d02c70c8ce993f956e118d7e39b9dcf3f`.
- Modelo: Frozenlock Qwen3.8-27B AutoRound INT4, revisión
  `b4c61732c4f2d8af323d75ba5702b5c7f3361539`, ruta local
  `/media/cristian/Disco local/Models/llamacpp/club-3090/qwen3.8-27b-autoround-int4`.
  Se reutilizará el manifiesto verificado en
  `Q-20261015-SOL-TASKFLOW-SAMPLING/receipts/sol-model-sha256.tsv` y se
  comprobará que los archivos mantienen esos hashes; no se descargan pesos.
- Runtime previsto: imagen ya local
  `vllm/vllm-openai:v0.27.1` (digest
  `sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967`),
  2×RTX 3090, modelo sólo texto, longitud máxima 4096, sin MTP, una petición
  concurrente, servidor temporal de loopback y sin editar perfiles productivos.
- Controles: AnyJev `raw` sobre el mismo servidor/modelo, y el gate
  determinista actual como control de seguridad (ninguna salida del modelo
  autoriza un efecto).
- Se preservará como antecedente el fallo de infraestructura vLLM SOL de
  `Q-20261015-SOL-TASKFLOW-SAMPLING`; una nueva caída no contará como error de
  calidad y abortará el screen.

## Corpus y protocolo preregistrados

- Fixture nuevo `fixtures/routing-risk-screen-v1.json`: 32 solicitudes
  sintéticas, 8 por clase: `read_only`, `reversible_local`,
  `approval_required`, `clarify_or_block`. Las etiquetas expresan una política
  de routing fijada en este plan, no autoridad de acción.
- Una pregunta de cuatro opciones, en orden canónico y orden inverso para cada
  solicitud. Se registra raw en ambos órdenes; L0 usa el ciclo completo de
  cuatro posiciones (prior por defecto) en ambos órdenes.
- Se fija `temperature=0`, sin muestreo, una respuesta probabilística por
  solicitud, mismo prompt/corpus/modelo/tokenizer/runtime para ambos brazos.
  Request timeout 60 s; no hay reparaciones ni tools.
- Métricas: exactitud total y por clase; cambios de respuesta al invertir
  opciones (raw y L0); Brier multiclase y ECE con bins preregistrados de 10%;
  cobertura/error empíricos a confianza ≥0,95; falsos `read_only`/
  `reversible_local` en clases `approval_required`/`clarify_or_block`; latencia
  p50/p95 y número de prefills.
- Gate del screen: servicio/API y logprobs válidos en todas las celdas. Si el
  preflight falla o el primer request no termina, no se continúa la matriz.
  Una sola ejecución es screening provisional; no alcanza para una mejora
  estable, para sustituir perfiles ni para habilitar acciones. El corpus
  pequeño tampoco puede certificar error ≤5%.

## Estado previo a inferencia

No se inicia inferencia hasta validar proceso/puertos, RAM/PSI/swap, GPU,
espacio libre, integridad de shards, wheel y una prueba de import/API sin
cargar el modelo. Si la infraestructura no permite la prueba, se preserva el
fallo con su clase y no se usa un resultado sintético como score del modelo.
