# Auditoría de tuning de Qwen3.8 + OMP para LlamaCode — 2026-09-21

## Fuente y criterio

Se contrastó el reporte externo sobre Qwen3.8-27B en dos RTX 3090 con el
harness nativo de LlamaCode. El reporte atribuye una reducción de espera por
turno de 28 s a 7 s a cuatro cambios: esfuerzo explícito por rol, presupuesto
de thinking de 7.500 tokens, `maxTokens` de 32K y externalización de resultados
de tools grandes; también usa hasta cuatro subagentes y contexto acumulativo.
La fuente primaria del artículo es [Tuning a Local Coding Agent](https://doug.sh/posts/tuning-a-local-coding-agent-oh-my-pi/)
y su análisis de prefix cache está en [Keeping vLLM's Prefix Cache Warm](https://doug.sh/posts/vllm-kv-cache-agents/).

## Qué ya tenía LlamaCode

| Idea del reporte | Estado previo en LlamaCode | Decisión |
|---|---|---|
| Prefix cache y schemas deterministas | Ya validado: canonicalización recursiva de tools, `cache_prompt=true`, warmup y vLLM prefix cache; 17.776 tokens reutilizados en la prueba local | Mantener; no repetir |
| `maxTokens=32K` | El agente principal ya calcula una reserva dinámica con tope 32K | Propagar al subagente |
| Presupuesto de thinking | SOL ya tiene política persistida y el request principal enviaba `reasoning_budget` | Propagar a sesiones y subagentes |
| Hasta cuatro subagentes | Ya existe límite adaptativo por contexto, slots y VRAM, con techo absoluto 5 | No fijar 4 artificialmente |
| `appendOnlyContext` | LlamaCode separa transcript y memoria de trabajo, poda/compacta y conserva prefijos estables | No copiar el nombre; conservar el mecanismo existente |
| Resultados de tools >10 KB a archivo | El fallback textual ya acota resultados; el protocolo nativo conserva contenido completo | No externalizar todavía: requiere contrato de artefactos y lectura segura; queda como experimento separado |

## Cambio aplicado

Se corrigió la parte que sí era una diferencia real:

- `SubAgentRunner` hereda `reasoning_effort` y `reasoning_budget` del perfil
  principal.
- Los subagentes envían `chat_template_kwargs` coherentes con esa política.
- Su reserva de salida pasa de 8.192 a 32.768 tokens, acotada al mismo máximo
  del agente principal.
- Las sesiones runtime y las ramas paralelas de Tasks también copian la
  política de razonamiento.
- El warmup usa el mismo presupuesto de reasoning que el turno real; antes
  enviaba `-1` aunque el perfil tuviera un presupuesto finito.

No se cambió el default de SOL, su modelo, MTP4, KV FP8, contexto 262K,
muestreo ni límite adaptativo de subagentes.

## Validación reproducible

- Build Release Linux: correcto; se compiló `SubAgentRunner`, `LlamaAgentBackend`,
  `AppController` y el ejecutable `LlamaCode`.
- Suite Linux: **77/77 tests PASS**.
- `test_agent_wire`: PASS, incluyendo que warmup conserva `reasoning_budget=4096`
  cuando el turno real usa ese presupuesto.
- Build Debug Linux: no regenerable en este checkout por el bloqueo externo de
  CMake `OpenGL::GL IMPORTED_LOCATION` para la configuración Debug.
- No se hizo benchmark de tokens contra un servidor en esta corrida porque no
  había un endpoint SOL activo en `127.0.0.1:8113`; iniciar un servidor de dos
  GPUs sólo para una prueba de harness habría mezclado el benchmark con una
  nueva carga del modelo.

## Conclusión

La mejora transferible no es “subir a cuatro subagentes” ni poner 7.500 tokens
globales. Es evitar defaults silenciosos: cada perfil debe declarar su esfuerzo
y presupuesto, y cada subagente debe heredarlos. El límite adaptativo actual es
más seguro que el fijo del reporte para 262K, donde varias secuencias pueden
provocar preemption del KV; para SOL a contexto largo se conserva la reducción
automática de concurrencia.

La externalización de resultados grandes queda fuera de este cambio. Puede
mejorar TTFT, pero sólo debe implementarse junto con un almacén de artefactos
confinado al proyecto, escritura atómica, expiración y una tool explícita de
lectura; truncar silenciosamente un resultado nativo sería peor que el problema
que intenta resolver.

Como referencia operativa, vLLM documenta que los presupuestos de thinking y
la caché de prefijo dependen de la versión y del template; hay incidencias
abiertas sobre presupuestos ignorados o inconsistentes en ciertos modos, por lo
que la política se deja en el payload y no sólo en una bandera del servidor:
[vLLM #55382](https://github.com/vllm-project/vllm/issues/55382),
[vLLM #54906](https://github.com/vllm-project/vllm/issues/54906).
