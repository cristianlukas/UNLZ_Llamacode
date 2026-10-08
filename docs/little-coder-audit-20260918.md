# Auditoría de `little-coder` para LlamaCode — 2026-09-18

## Resultado ejecutivo

`little-coder` es un harness TypeScript/Node basado en pi, orientado a modelos
locales pequeños y especialmente a Qwen3.6-35B-A3B servido por llama.cpp. No
es un modelo ni un runtime de inferencia. Sus resultados publicados no son
comparables directamente con nuestra tabla: usan otra máquina, otra versión de
llama.cpp y benchmarks distintos de HE/BCB.

La revisión sí encontró ideas transferibles:

- steering dinámico de subagentes y skills;
- carga perezosa de tools para no inflar el contexto;
- retry guiado por salida de tests y continuación ante límite de tokens;
- write guard/CWD guard y parámetros más tolerantes para modelos chicos;
- planificación y revisión con subagentes;
- compresión de contexto experimental.

LlamaCode ya cubre buena parte de esto con `HarnessSpec`, `skill_list/load`,
context scout/fetch, compaction, worktrees, approvals, confinamiento al cwd,
loops de goals y subagentes. No se encontró una mejora demostrada que justifique
cambiar SOL, QWEN35-A3B o cualquier perfil de modelo.

Fuentes primarias: [repositorio oficial de L3tum](https://github.com/L3tum/little-coder),
[README](https://github.com/L3tum/little-coder/blob/main/README.md),
[reproducción de benchmarks](https://github.com/L3tum/little-coder/blob/main/docs/benchmark-reproduction.md)
y [arquitectura](https://github.com/L3tum/little-coder/blob/main/docs/architecture.md).

## Resultados externos y comparabilidad

El README conserva resultados del proyecto original/fork:

| Modelo y entorno externo | Benchmark | Resultado | Comparabilidad |
|---|---|---:|---|
| Qwen3.5-9B, Ollama | Aider Polyglot | 45,56% | No es BCB ni nuestro runtime |
| Qwen3.6-35B-A3B, llama.cpp | Aider Polyglot | 78,67% | Misma familia que QWEN35-A3B, pero otra suite/harness |
| Qwen3.6-35B-A3B, llama.cpp | Terminal-Bench-Core | 40,0% | No sustituye HE/BCB |
| Qwen3.6-35B-A3B, llama.cpp | Terminal-Bench 2.0 | 24,6% ± 3,2 | Máquina y protocolo externos |
| Qwen3.5-9B, llama.cpp | Terminal-Bench 2.0 | 9,2% ± 2,4 | Referencia de capacidad, no ranking local |

Los runs se hicieron en un i9-14900HX con 32 GB de RAM y RTX 5070 Laptop de
8 GB. Nuestro QWEN35-A3B tiene mediciones locales de 123,98 BCB/134,4 TG,
visión 4/4 y contexto 262K, pero su BCB 4/8 no puede compararse con Aider o
Terminal-Bench. No se eleva ni se degrada el perfil por estas cifras externas.

## Comparación con LlamaCode

| Capacidad | `little-coder` | LlamaCode actual | Decisión |
|---|---|---|---|
| Prompt inicial corto | AGENTS.md de ~3.000 caracteres y steering dinámico | perfiles `agent-minimal`/`agent-chat`, directivas por módulo y presupuestos de contexto | Medir un perfil compacto, sin activarlo por defecto |
| Skills y tools | frontmatter, steering por intención y carga dinámica | `skill_list/load`, allowlists por perfil/fase y routing MCP adaptativo | Ya cubierto en lo esencial |
| Subagentes | modelo configurable por subagente y niveles de steering | roles de modelo, `DifficultyRouter`, `SubAgentRunner`, límite por VRAM/contexto y worktrees | LlamaCode conserva mejor integración con 2×3090 |
| Retry de tests | reinyecta salida del test en un segundo intento | loops/goal-check, reparación BCB y logs de herramientas; no hay una política idéntica de retry automático genérico | Candidato útil para una prueba aislada |
| Límite de tokens | auto-continue hasta 3 veces y luego compaction | compactación LLM y límites por perfil; no se detectó el mismo auto-continue por `finish_reason=length` | Candidato útil, opt-in |
| Write/CWD guards | write sólo crea; edit exige texto único; cwd y permisos acotados | `safeProjectDir`, confinamiento al cwd, approvals y bloqueo de destructivas | Ya cubierto, no copiar reglas textuales |
| LSP | integrado mediante pi-hooks/lsp | no hay adaptador LSP equivalente detectado | Mejora futura del harness, no del modelo |
| Plan/review | `/deep-plan`, revisión dual y pipelines de 7 subagentes | HybridPlanning, phases plan/exec/verify/goalCheck, revisión y teacher escalation | Cobertura comparable |
| Compresión | pi-vcc experimental y compaction | compaction propia, poda de imágenes, dedup y checkpoints | No cambiar sin A/B de calidad |
| Perfil del modelo | catálogo separado de perfiles de contexto/temperature/tokens | system profiles y `HarnessSpec` con roles/modelo/contexto | No agrega un perfil de inferencia |

## Pruebas y verificaciones realizadas

Se clonó el fork en un directorio temporal, sin instalarlo en LlamaCode. Commit
revisado: `65118f8cdb987f67d7886384ba604e21e2a3a63b`.

Se inspeccionaron el catálogo de modelos, `.pi/settings.json`, extensiones de
steering, skill/tool loading, write/CWD guards, retry, compaction, deep-plan,
review, perfiles, LSP y documentación de benchmarks.

El checkout declara Node `>=22.19`. Se probó en un contenedor Node 22.23.2 sin
instalarlo en LlamaCode. `npm ci` quedó bloqueado por el binding opcional
Android; `npm install --ignore-scripts --force` permitió ejecutar la suite:
58 archivos, **975 tests PASS, 3 SKIP y 2 FAIL**. Los dos fallos son los tests
de parcheo de `pi-vcc`/notificaciones contra un target upstream que cambió; no
son fallos de inferencia ni del fixture comparativo. El typecheck también quedó
bloqueado por dependencias opcionales de `@plannotator` ausentes.

Se levantó el SOL AutoRound local mediante vLLM 0.27.1 en Docker, TP2 sobre las
dos RTX 3090, FlashAttention/Marlin/NCCL y contexto configurado de 32K para que
la comparación fuera reproducible. El alias HTTP usado por el perfil externo
era sólo un alias: **no era DFlash2**, sino el mismo SOL servido con el nombre
esperado por el adaptador.

La comparación end-to-end usó el mismo fixture Python, la misma instrucción y
el mismo endpoint:

| Harness | Resultado | Medición observada |
|---|---|---|
| LlamaCode, prompt amplio | Terminó con salida corrupta y sin cambio | ~52 s; 4 tools correctas; expuso un bucle de exploración/modelo que no llegó a editar |
| LlamaCode, prompt acotado | **Completó correctamente** | ~124 s; 12 llamadas de tool, 1 intento de edición rechazado/recuperado, `pytest`: **3/3** |
| little-coder, adaptador RPC | **No completó** | timeout de 120 s esperando la respuesta RPC; no produjo cambio ni resultado de tests |

El segundo resultado de LlamaCode es una comparación funcional, no un BCB:
el fixture mide convergencia, herramientas y tests, no calidad general del
modelo. little-coder no puede recibir un puntaje de calidad porque su RPC no
llegó a ejecutar la tarea en este entorno.

Durante el A/B apareció además un fallo de integración reproducible: el perfil
declaraba 262K, pero el vLLM de prueba estaba configurado a 32K y no ofrecía
`/props`. LlamaCode ahora aprende el `maximum context length` informado por el
400, suma el costo de los schemas de tools y calcula `max_tokens` con margen
respecto del prompt estimado. En la repetición, después del primer rechazo que
revela el límite, desapareció el segundo rechazo por `8192 + 24577 > 32768` y
el agente avanzó a editar y ejecutar tests. La sesión temporal quedó luego
atascada en compactaciones porque reutilizó un transcript persistido grande;
por eso no se registra esa última corrida como éxito adicional.

## Mejoras candidatas para LlamaCode

### Retry guiado por test

Implementar una política opt-in por perfil que, ante un test fallido, reinyecte
sólo el comando, salida acotada, archivo afectado y diff relevante. Debe:

- conservar el límite de tokens y el contexto útil;
- no repetir ciegamente el mismo tool call;
- cortar después de un máximo configurable;
- guardar `retryOf`, causa y resultado;
- medirse con primer intento, total final, reparaciones y tokens.

Es probablemente la mejora más prometedora para BCB, pero no se la activa sin
un A/B local.

### Auto-continue por límite de generación

**Implementado en LlamaCode.** El backend captura `choices[0].finish_reason` y
reanuda sólo con `length`, texto no vacío y un máximo de dos continuaciones por
turno. Conserva el fragmento anterior en el historial y usa una instrucción
anti-repetición. No se dispara por timeout, error de tool, respuesta vacía ni
un `stop` normal. La política pura tiene regresiones para los cuatro bordes
principales en `tests/test_agent_wire.cpp`.

La medición de integración quedó pendiente de una respuesta que fuerce
`finish_reason=length`; la decisión no se promociona como mejora de BCB todavía.

La compilación Release finalizó correctamente. El test focalizado del backend
quedó en **55/55 PASS** (`test_agent_wire`). El gate completo de ctest no pudo
cerrar porque hay procesos `ctest` antiguos en estado `D` en este host; no se
atribuyó ese bloqueo a este cambio.

### Perfil compacto

Crear una variante experimental con menos directivas y tools cargadas bajo
demanda. No tocar el perfil principal: reducir el system prompt puede mejorar
prefill y memoria, pero también puede bajar la tasa de primer intento o romper
tool-use. La validación correcta es Harness Context A/B seguida de HE0/HE20/BCB.

### LSP read-only

Evaluar una integración local y opcional para diagnósticos, símbolos y
referencias. No debe convertirse en una dependencia obligatoria ni ejecutar
escrituras fuera de approvals.

## Impacto sobre perfiles y tabla

| Perfil | Decisión |
|---|---|
| **SOL** | Sigue como default; sin cambio de pesos, flags, BCB, visión o contexto |
| **QWEN35-A3B** | Sigue como multimodal/concurrente; las cifras externas no cambian su fila |
| **GALACTA, TERRA, METEOR y auxiliares** | Sin cambios |
| **ASTRA/NINFER/QWEN38-Q8 y experimentales** | Sin promoción; el scaffold no repara sus fallos de runtime/calidad |

No se agrega `LITTLE-CODER` como modelo: es un harness externo.

## Decisión final

- No se instala `little-coder` ni Node/npm en el entorno productivo de LlamaCode;
  la ejecución comparativa se mantuvo temporal y aislada.
- No se cambia la tabla ni el default SOL.
- El auto-continue controlado por `finish_reason=length` queda integrado y
  apagado para respuestas normales por diseño; el test funcional completo con
  un servidor que fuerce truncamiento queda como validación siguiente.
- El retry guiado por test ya existe como disciplina/prompt y recuperación de
  tools; no se añadió otro loop automático porque la corrida comparativa mostró
  que aumentar iteraciones sin un error de test explícito sólo puede amplificar
  el bucle de exploración observado.
- Perfil compacto y LSP quedan como mejoras futuras, no activas.
- Esta auditoría evita repetir el clone, la inspección de extensiones y la
  comparación de los benchmarks históricos de little-coder. La comparación
  local queda registrada con el endpoint, contexto, fixture, tiempos y conteo
  de tools anteriores.
