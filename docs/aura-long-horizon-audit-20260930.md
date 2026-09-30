# Auditoría Aura: agentes locales de horizonte largo — 2026-09-30

## Pregunta

¿La demo de Aura resolviendo 2048 durante unos 29 minutos aporta una mejora
transferible a Ingi Charla, Computer Use, el harness o los perfiles de
LlamaCode?

## Fuentes y límites de la evidencia

Se revisó la publicación del usuario `bryany97` en r/vibecoding, su enlace al
video de 28:41 y el repositorio público
[`youngbryan97/aura`](https://github.com/youngbryan97/aura), en particular el
README, `HOW_IT_WORKS.md`, `TESTING.md` y `docs/ABLATION_LEGIBILITY.md`.
Consulta de fuentes: 2026-09-30.

La publicación describe un resultado de una corrida: un modelo local Qwen de
clase 27B, control de escritorio, memoria, estado del juego/modelo del mundo,
búsqueda de estados futuros y cambio de estrategia. El clip demuestra que esa
ejecución llegó a 2048; no contiene un A/B con el modelo solo, semillas/cargas
repetidas, tasa de éxito, trazas cuantitativas ni ablaciones que atribuyan el
resultado a cada subsistema. Por sí sola, la demo no demuestra superioridad
general ni una mejora para tareas de escritorio arbitrarias.

El repositorio actual expone mucha más arquitectura que la publicación —entre
otros mecanismos, recuperación episódica, metas persistentes y varios módulos
de razonamiento—. Sus propios documentos distinguen entre pruebas de cableado,
cambios en la salida del módulo y cambios en el éxito de tareas. La auditoría de
ablación informa que las primeras dos clases no bastan para afirmar que un
componente mejora la capacidad; en el runner de capacidad compara presupuestos
iguales y declara `unresolved` cuando el delta no es concluyente. Esa disciplina
experimental sí es transferible.

El repositorio declara la licencia **All Rights Reserved (Read-Only)**: permite
lectura y ejecución local, pero prohíbe copiar, modificar o crear derivados.
Esta revisión toma únicamente ideas generales; no se copia código, pesos ni
artefactos de Aura.

## Contraste con LlamaCode y pruebas previas

| Idea de Aura | Cobertura existente | Evidencia / lectura |
|---|---|---|
| Mantener el objetivo durante una tarea larga | Loop de Tasks con `goalCheck`, topes explícitos y créditos elásticos del `AgentProgressGovernor` | `tests/test_appcontroller.cpp`: `loopTaskRunsBodyUntilGoalMet`, `loopTaskStopsAtMaxIterations`, `loopTaskStopsAtMaxSeconds`; cobertura funcional del controlador, no una corrida de escritorio de 29 minutos. |
| Detectar estancamiento y replantear | Detección de llamadas repetidas, espirales de errores, créditos y eventos de progreso/replan | `docs/harness.md`; pruebas en `tests/test_agent_wire.cpp`. Más seguro que seguir insistiendo, aunque no equivale a búsqueda de estados futuros. |
| Aprender de una interfaz que cambió | Teach persiste learnings de adaptaciones exitosas y los reinyecta en la siguiente corrida | `tests/test_automation.cpp`: `artifactLearningsAppendAndPrompt`, deduplicación y límite de contexto. Es aprendizaje de receta, no un modelo aprendido de dinámica arbitraria. |
| Persistir objetivo, eventos y resultados | Sesiones, transcript íntegro, checkpoints, eventos, corridas durables y entregables | `docs/harness.md`, `docs/agent-runs.md` y README; la continuidad ya existe en el plano de ejecución y auditoría. |
| Preservar restricciones con compactación | A/B `raw` contra compactación tras cinco resets, Qwen3.5-4B y 9B | `docs/compaction-quality-audit-20260923.md`: 4B pierde restricciones en 1/3 corridas compactadas; 9B retiene, pero las cinco compactaciones duplican aproximadamente el tiempo de la consulta final. No bajar umbral ni compactar antes por defecto. |
| Decidir acciones de Computer Use | 48 estados fáciles y difíciles, incluyendo inyección, secretos, confirmaciones y destinatarios | Swift Genesis, 2026-09-29: 240/240 por variante, 145/145 estados sensibles, transporte completo; `question-first` mediana 633.73 ms y `state-first` 654.84 ms. Sandwich fue correcto, pero 795.47 ms y no pasó el gate de latencia. Es selección de una acción por estado, no control prolongado con realimentación. |
| Modelo del mundo / planificación con simulación | No hay benchmark largo-horizonte apareado que mida el efecto en LlamaCode | La prueba 2048 mostrada es específica a un entorno con dinámica discreta conocida; no justifica codificar juego, app, acciones o layouts en el motor general de PC. |
| Perfil de voz / Ingi Charla | Charla prioriza latencia por turno y concurrencia con agente; auditorías de audio separadas | No se midió voz continua, latencia conversacional prolongada ni continuidad de metas durante una sesión de voz. No cambiar perfil de voz desde una demo de 2048. |

Otros datos recientes de perfil tampoco miden la tesis: Swift Genesis logró 5/5
contratos de tool, pero BCB-Hard fue 1/8 en ocho tareas. El resultado de
Computer Use de 48 casos mide decisiones aisladas. No inferir desde esos smokes
una mejora de persistencia, planificación de horizonte largo o calidad de
código.

## Decisión

**No se cambia código, harness activo, perfil ni sampling.** No hay evidencia
local que haga a Aura o a una de sus piezas superior a la arquitectura actual
para una carga equivalente. Las ideas de memoria persistente, goal-check,
receipts, estancamiento y aprendizaje de Teach ya están representadas en
LlamaCode. Su modelo de mundo con búsqueda podría ser útil en entornos con
estado estructurado, pero la demostración de 2048 no valida su generalización
a Computer Use.

Sí se adopta como criterio de evaluación futuro —no como feature— exigir pruebas
de ablación de capacidad: comparación entre harness completo y una variante sin
el componente, mismo modelo, prompts, presupuesto de tokens/acciones, semillas y
carga. El caso debe poder resolverse sin ese componente; si no, el resultado
sólo demuestra que está conectado. Reportar tasa de éxito, seguridad,
abstención, latencia, intervalos de incertidumbre y fallos; un delta no
concluyente se registra como tal.

## Próxima prueba válida si se retoma la línea

No repetir el smoke de 48 decisiones ni la matriz raw/compactación de cinco
resets como sustitutos de una tarea larga. Congelar primero un corpus nuevo de
tareas multi-etapa con cambios de estado, desvíos/distractores y recuperación
tras interrupción, usando superficies y apps variadas. Comparar, con el mismo
modelo y límites:

1. harness actual;
2. harness actual sin recuperación de memoria/learning relevante;
3. harness actual sin progress-governor/replan (sólo en sandbox y sin efectos
   externos);
4. si existe un entorno con API de estado/dinámica, control ciego frente a
   modelo de transición + búsqueda, manteniendo idéntico el actuador.

Usar al menos cinco seeds/corridas por celda, orden intercalado y checkpoints
fríos/calientes. Guardar las trazas de estado/acción y receipts, el hash de la
carga y configuración completa. Éxito exige el objetivo verificable; el tiempo
de pared y la coherencia narrativa no reemplazan esa métrica. No usar 2048 como
implementación ni como única tarea. La promoción además debe conservar el gate
de seguridad de Computer Use y no degradar la ruta de voz/código si el módulo
se comparte.

## No repetir exactamente

- No volver a ejecutar `computer_use_prompt_order_v1` + `hard_v1` con las tres
  variantes en Swift Genesis bajo 64K para responder esta misma pregunta:
  720 requests, 5 pasadas, seeds 11/42, ya están en
  `artifacts/swift-genesis-evaluation-20260929/computer_use_64k.json`.
- No repetir como prueba de continuidad la matriz de compactación de cinco
  resets con Qwen3.5-4B/9B; está en los dos JSON referenciados por la auditoría
  del 2026-09-23.
- No tratar `harness_tool_contract_v1` (cinco pasadas) ni BCB-Hard (1/8) como
  evidencia de horizonte largo; sus artefactos están en
  `artifacts/swift-genesis-evaluation-20260929/`.
- Reabrir esta auditoría sólo si aparece una carga multi-etapa/ablation
  comparable o evidencia nueva, y anexar sus hashes/resultados aquí antes de
  lanzar esas suites.

## Verificación local

Esta auditoría es de investigación y documentación; no se modificó C++/QML ni
un perfil. Los tests de controlador, agente y Teach nombrados arriba son
cobertura preexistente, no se vuelven a declarar como ejecutados en esta
revisión. Se intentó `./scripts/tests-linux.sh Release`, pero al iniciar ya
había otras dos ejecuciones del mismo script usando
`~/.cache/llamacode/build_tests_linux`. Al compartir el build y los datos CTest,
el intento concurrente mostró `test_download_history::append_capsToMax` con 17
en vez de 200 filas mientras otros tests también escribían/limpiaban su estado.
Se canceló ese intento; el resultado del test queda **inconcluso por colisión
de corridas**, no como fallo reproducible del código. Repetir el gate sólo cuando
las ejecuciones existentes hayan terminado y en un directorio de tests aislado
(por ejemplo, `LC_TEST_BUILD_DIR=/tmp/llamacode-tests-aura-audit`). La prueba de
capacidad larga recomendada todavía no se ejecutó porque el corpus apareado no
existe.
