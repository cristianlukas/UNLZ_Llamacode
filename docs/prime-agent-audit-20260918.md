# Auditoría de `prime-agent` para LlamaCode — 2026-09-18

## Resultado ejecutivo

`prime-agent` es otro harness de coding/investigación; no es un modelo, un
quant ni un motor de inferencia. Sus ideas pueden cambiar la eficiencia del
flujo de trabajo, pero no mejoran por sí mismas PP, TG, VRAM, contexto, visión,
HE o BCB de SOL, QWEN35-A3B ni de los auxiliares.

Hay dos ideas interesantes para una futura campaña del harness:

1. **REPL Python persistente/RLM:** variables y resultados grandes quedan fuera
   del prompt y los subagentes se invocan programáticamente.
2. **Continual Harness:** refinamientos pequeños, explícitos y reversibles de
   prompts, memorias, skills y especificaciones de subagentes, con snapshots.

No se instaló `prime-agent` como dependencia permanente ni se incorporó su
daemon. Se construyó una copia temporal dentro de Docker para la comparación.
No se modificaron perfiles ni `assets/system_profiles.json`; SOL sigue siendo el
default. La razón es que ninguna de esas capacidades constituye una mejora de
inferencia y las dos ideas nuevas requieren medir seguridad, latencia y tasa de
reparaciones antes de incorporarlas.

Fuentes primarias revisadas: [repositorio oficial](https://github.com/PrimeIntellect-ai/prime-agent),
[documentación del runtime RLM](https://github.com/PrimeIntellect-ai/prime-agent/blob/main/packages/coding-agent/docs/rlm-runtime.md),
[documentación del REPL](https://github.com/PrimeIntellect-ai/prime-agent/blob/main/packages/coding-agent/docs/rlm.md),
[continual harness](https://github.com/PrimeIntellect-ai/prime-agent/blob/main/prime-agent-runtime/src/rlm/harness.py)
y [skills](https://github.com/PrimeIntellect-ai/prime-agent/blob/main/packages/coding-agent/docs/skills.md).

## Comparación con LlamaCode

| Capacidad | `prime-agent` | LlamaCode actual | Evaluación |
|---|---|---|---|
| Herramienta principal | REPL Python persistente; archivos, shell, tools y contexto pasan por código | tools nativas, lanes Node/Python y `HarnessSpec` por fase | Potencialmente útil para datos grandes, pero agrega ejecución Python y no cambia el modelo |
| Subagentes | `rlm.spawn(...)`, hijos en paralelo/background y comunicación directa | `SubAgentRunner`, worktrees, cola, rooms, merge y límite adaptativo por VRAM/contexto | Misma clase de capacidad; LlamaCode está más integrado con sus perfiles locales |
| Memoria de trabajo | variables del kernel + estado serializado de sesión | memoria de proyecto, `MemoryStore`, `GraphStore`, `ProjectBrain`, checkpoints y event log | El REPL conserva estado arbitrario; la memoria local es más controlable y tipada |
| Refinamiento | `/refine` propone/aplica cambios a memoria, prompts, skills y specs con snapshot/rollback | consolidación de memoria, skills portables y edición explícita de `HarnessSpec` | Idea transferible; falta un flujo dedicado de propuesta, evidencia y rollback |
| Persistencia | daemon, kernel, sesiones reanudables, heartbeats y schedules | daemon headless, managed runs, scheduler, loops, goals y heartbeats de tareas | Cobertura comparable; no justifica reemplazar el runtime |
| Autonomía | gates configurables, límites de turnos/tokens/tiempo y continuación | loops, goal-check, approvals, créditos, timeouts y políticas por perfil | Comparable; el modelo y el harness deben permanecer bajo límites locales |
| Skills | paquetes Python importables por el kernel | skills portables con selección por perfil y fase | Prime es más programático; LlamaCode evita instalar código ejecutable por defecto |
| Seguridad | el README advierte que Python/comandos corren con permisos del usuario y no son sandbox | approvals, políticas read-only, bloqueo de destructivas, sandbox y worktrees | No importar el REPL sin aislamiento y control de recursos |

## Pruebas realizadas

### Auditoría estática

Se clonó el repositorio upstream en un directorio temporal, sin tocar el
workspace de LlamaCode. Commit revisado: `ff40ea24e129e69b09b553f801dda6699d820424`.
Se verificaron los caminos de `rlm.spawn`, el runtime de REPL, el almacenamiento
`harness_state`, snapshots, rollback, `/refine`, daemon, schedules, heartbeats,
gates autónomos y límites de sesión.

### Pruebas del runtime externo

- `prime-agent-runtime/test/test_harness.py`: **52/52 OK**.
- `prime-agent-runtime/test/test_repl.py`: **104/104 OK** después de instalar
  `dill` sólo en un directorio temporal de dependencias.
- Reejecución completa de ambos módulos en el commit auditado: **156 tests
  pasaron y 25 subtests pasaron** en 15,72 s. La primera ejecución sin `dill`
  falló por dependencia ausente, no por una regresión del runtime.
- No se instaló ningún paquete en el entorno permanente ni se inició una sesión
  autenticada, un proveedor remoto o un daemon.

Estas pruebas validan el runtime del proyecto externo; no son BCB ni una
comparación de calidad contra SOL.

### Comparación ejecutable con el mismo endpoint local

Se construyó temporalmente `prime-agent` con Node 22 y se apuntó su proveedor
OpenAI-compatible al SOL AutoRound local servido por vLLM 0.27.1, TP2, con
`max_model_len=32768`. El arranque fue correcto y vLLM respondió; la medición
de inferencia del endpoint, fuera del harness, dio aproximadamente **1.418
tok/s de prefill y 24 tok/s de generación** para una petición corta de control
(el proceso de compilación/warmup no se mezcló con esa cifra).

Se usó el mismo fixture para ambos harnesses: `src/slug.py` tenía un bug de
slugificación Unicode y dos tests Pytest exigían conservar `café-déjà-vu`.
Resultado reproducible de esta campaña:

| Brazo | Resultado | Tiempo/diagnóstico | Cambio en fixture |
|---|---|---|---|
| Prime Agent, modo JSON/print | Inicializó RLM y llegó al endpoint, pero generó una secuencia repetitiva de `!`; se canceló para no consumir contexto | El protocolo emitió cientos de deltas repetidos y no produjo tool-call ni resumen útil | Ninguno |
| LlamaCode, agente nativo, mismo endpoint | Reintentó el turno y su anti-loop cortó la generación repetitiva | Primer intento detectó que el alias de perfil era DFlash2 mientras el endpoint exponía SOL; corregido el alias, el modelo siguió repitiendo y el anti-loop abortó | Ninguno |

Esto **no es una comparación de calidad válida**: el perfil DFlash2 de LlamaCode
se probó contra un alias de control que sirve los pesos SOL, y ambos brazos
mostraron una incompatibilidad de plantilla/receta con el prompt agentivo. Sí es
una prueba útil de robustez: Prime no aportó una reparación, y LlamaCode evitó
un loop infinito gracias a su guardia anti-loop. El siguiente benchmark válido
debe levantar el modelo declarado por el perfil (SOL o DFlash2 real), fijar la
misma plantilla y comprobar primero un smoke de texto/tool-call antes de medir
tiempo o calidad.

### Contraste con la cobertura local

LlamaCode ya tiene pruebas para subagentes, límites adaptativos por slots,
contexto y VRAM, goals, loops, memoria/grafo, skills, corridas administradas y
scheduler auxiliar. No se repitieron esas pruebas ni se arrancó una inferencia
real: Prime Agent no aporta pesos, flags de vLLM/llama.cpp ni una receta nueva.

## Qué podría implementarse en LlamaCode

### 1. Historial reversible de directivas — implementado

Como mejora concreta inspirada en el Continual Harness, LlamaCode ahora archiva
la versión anterior de una directiva propia antes de editarla o eliminarla.
`HarnessDirectiveStore::history()` expone las revisiones y
`rollbackHarnessDirective()` restaura una revisión exacta archivando también el
estado actual; por eso el rollback sigue siendo reversible y no reescribe la
historia. La ruta de historial queda dentro del scope de la directiva y se
rechazan revisiones con traversal.

La regresión `directiveStore_keepsHistoryAndRollsBack` verifica edición,
restauración, conservación de ambas revisiones y rechazo de `../escape.md`.
La capacidad queda disponible por Control API/AppController, pero no modifica
automáticamente perfiles, permisos ni SOL.

### 2. Continual Harness con propuesta — candidato futuro

Agregar una capa opt-in que permita proponer cambios acotados a memoria,
directivas, skills o especificaciones de subagentes, guardando:

- motivo y evidencia de la propuesta;
- diff antes/después;
- scope de proyecto o global;
- snapshot y rollback;
- prueba mínima antes de activar el cambio.

Debe reutilizar `MemoryStore`/`HarnessSpec` y mantener inmutable la política
base, los permisos y el perfil de modelo. Es la única idea del repositorio que
podría mejorar indirectamente la calidad agentiva, pero todavía no hay una
métrica local que justifique activarla por defecto.

### 3. REPL persistente — candidato condicionado

Podría ser una lane opcional para cálculos, parsing y transformaciones grandes,
con variables persistentes fuera del prompt. Antes de implementarla habría que
resolver:

- proceso aislado y límites de CPU/RAM/tiempo;
- permisos de filesystem y red;
- cancelación y limpieza de estado;
- serialización segura del namespace;
- compatibilidad Windows/Ubuntu;
- impacto en TTFT, tokens de contexto, tool-call quality y tasa de errores.

No se debe añadir un Python con permisos del usuario como tool general sin esas
garantías. Tampoco conviene convertirlo en una sustitución de las tools
tipadas: para tareas pequeñas puede ser más lento y menos auditable.

## Impacto sobre perfiles y tabla de modelos

| Perfil | Decisión |
|---|---|
| **SOL** | Permanece default; sin cambio de modelo, flags, BCB, visión o contexto |
| **QWEN35-A3B** | Permanece secundario multimodal/concurrente |
| **GALACTA, TERRA, METEOR y auxiliares** | Sin cambios; Prime Agent no ofrece inferencia local comparable |
| **ASTRA/NINFER/QWEN38-Q8 y experimentales** | Sin promoción; un REPL o `/refine` no arregla sus fallos de runtime/calidad |

No se agrega una fila `PRIME-AGENT`: sería confundir un harness con un modelo.

## Validación local de LlamaCode

- Build Linux Release: **completado** (`/home/cristian/.cache/llamacode/build_linux/LlamaCode`).
- `test_harness_modules`: **24/24 OK**, incluyendo la regresión nueva.
- `test_harness_effects`: **4/4 OK**.
- `test_agent_runs`: **6/6 OK**.
- `test_harness_spec`: **26/26 OK**.
- El gate global de `scripts/tests-linux.sh Release` compiló los 321 targets,
  pero quedó bloqueado al ejecutar `ctest` por procesos antiguos en estado
  `D` (I/O no interrumpible). No se mataron esos procesos.

## Campaña futura registrada

Si se implementa el Continual Harness, la comparación debe usar el mismo modelo
y la misma receta en dos brazos:

1. control LlamaCode actual;
2. refinamiento opt-in con snapshot y rollback.

Medir primer intento, reparaciones, archivos correctos, tool-call quality,
TTFT/TG, tokens de contexto, memoria, cancelación y regresiones después de
reiniciar. Recién después ejecutar HE0, HE20 y BCB. Para el REPL, agregar casos
con archivos grandes y procesos cancelados, y verificar que los permisos no se
amplíen.

## Decisión final

- El runtime externo pasó sus pruebas internas, pero eso no lo hace superior a
  nuestros perfiles de modelo.
- No se instala ni se incorpora como backend.
- No se cambia la tabla ni el default SOL.
- Se documentan como candidatos futuros el refinamiento reversible y, con mucha
  más cautela, el REPL persistente.
- Esta auditoría evita repetir el clone, el inventario de funciones RLM,
  continual harness, daemon/schedule y las suites externas 156+25. La prueba
  comparativa de código debe repetirse sólo después de corregir la receta del
  endpoint; no debe confundirse con una mejora de modelo.
