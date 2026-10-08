# Campaña de calidad con Harness — 2026-09-15

## Alcance

Se probaron los perfiles solicitados con el Harness de LlamaCode, usando el
objetivo `agent`, el agente `agent-maximo`, thinking habilitado y la cadena
HE0 → HE20 → BCB8. La campaña se ejecutó con el binario Release de Ubuntu.

La prueba anterior de QWEN35-A3B que enviaba `local` o `benchmark` como modelo
no era una evaluación agentiva válida: esos valores llegaban al endpoint vLLM
como identificador de modelo. El runner ahora resuelve el backend cloud/local
igual que la ejecución interactiva y usa el modelo real.

## Resultados reproducibles

| Perfil | HE0 actual | HE20 actual | BCB8 actual | Evidencia adicional |
|---|---:|---:|---:|---|
| QWEN35-A3B | **1/1** | **9/20** | Bloqueado por compuerta HE20 | 2 tool calls en HE0; HE20 tuvo 10 calls, 9 exitosas. BCB histórico anterior: 4/8, no comparable directamente. |
| CyberTiel | **1/1** | No concluyente | Bloqueado | 3 tool calls exitosas en HE0; HE20 entró en reparación no convergente. |
| METEOR / BigBang | **1/1** | No concluyente | Bloqueado | HE20 anterior no convergió; control directo separado: 2/8. |
| Qwen3.5-9B | **1/1** | **19/20** | Bloqueado por compuerta HE20 | Resultado HE20 válido, pero una tarea no creó el archivo esperado. |
| Qwen3.5-4B | **1/1** | **20/20** | Sin score final | BCB llegó a 8/8, pero la reparación quedó repitiendo llamadas `web_search`/`read_file`; se canceló por no convergencia. |
| Qwen3.5-2B | **0/1** | No ejecutado | No ejecutado | No pasó HE0; la ejecución no produjo el archivo esperado. |

Un resultado “bloqueado” no significa 0/8: BCB no se ejecuta cuando HE20 no
supera la compuerta. El BCB de Qwen3.5-4B tampoco se convierte artificialmente
en 0/8 porque sí alcanzó 8/8 antes de quedar atrapado en reparación.

## Tiempos observados

| Perfil | HE0 | HE20 |
|---|---:|---:|
| QWEN35-A3B | 8,1 s | 230,8 s |
| Qwen3.5-9B | 11,1 s | 598,4 s |
| Qwen3.5-4B | 21,1 s | 1086,3 s |
| Qwen3.5-2B | 44,8 s | — |
| METEOR | 52,1 s | — |
| CyberTiel | 73,1 s | — |

Los TPS directos publicados anteriormente para estos perfiles no se mezclan
con la calidad Harness: miden generación aislada y no creación de archivos,
tool-use, reparaciones ni convergencia.

## Decisión

No se promovió ni se cambió el default de LlamaCode. SOL sigue siendo el
perfil principal. Qwen3.5-4B es el único auxiliar que completó HE20 actual;
Qwen3.5-9B queda cerca, QWEN35-A3B muestra una regresión real bajo la
configuración actual y Qwen3.5-2B no es confiable como agente.

## Cambios de infraestructura usados

- Se corrigió el enrutamiento de `runAgentBenchmark()` para que respete el
  backend y el modelo configurados.
- Se agregó fallback para tool calls JSON-only cuando el modelo devuelve un
  objeto válido sin el wrapper esperado.
- La reparación del Harness ahora corta un ciclo de ocho inspecciones sin
  mutación (`read_file`, `web_search` y similares) cuando el turno ya quedó
  idle; no lo corta durante prefill, después de cambios en el workspace ni
  después de una tool potencialmente mutante (`write_file`, `edit_file`,
  `apply_patch`, `run_command`).
- El binario Release compiló correctamente.
- `test_appcontroller` pasó completo después del cambio. El gate Linux general
  conserva los fallos preexistentes de `test_agent_tools` y
  `test_system_profiles`; el detalle se reporta en el resultado de tests.

No se modificaron los perfiles permanentes ni se incorporaron candidatos al
dropdown. Los directorios de cada corrida quedaron bajo
`~/.local/share/LlamaCode/LlamaCode/benchmark-runs/` para auditoría.

## A/B de perfil y reparación del Harness

Se comparó el perfil de sistema `[general/visión] 4GB · Qwen3.5-4B MTP Q4`
contra una variante duplicada con la misma arquitectura, pero con `KV q8_0`,
`batch 256`, `ubatch 128`, `split-mode layer` y MTP ajustable. La variante
conservadora se guardó como perfil de usuario para no alterar el sistema.

| Variante | PP medido en A/B | TG medido en A/B | HE0 | HE20 | BCB8 | Lectura |
|---|---:|---:|---:|---:|---:|---|
| Sistema, MTP3/base | referencia | referencia | 1/1 | 17/20 | 0/8 en la corrida reproducida | Más lento; el backend se reinició durante una respuesta BCB y dejó artefactos inválidos. |
| Conservadora, MTP5 | **+477% de mediana PP** | **+311% de mediana TG** | 1/1 | **20/20 final** | 2/8 en la primera corrida; 1/8 en la repetición | Mejor compromiso observado, pero el BCB no es estable todavía. |
| Conservadora, MTP3 | **+479% de mediana PP** | **+359% de mediana TG** | 1/1 | 18/20 | 1/8 | Más rápida que MTP5, con una pequeña pérdida de HE20. |

Los A/B fueron pareados y la prueba nula quedó dentro del ruido; la mejora de
PP/TG sí fue significativa. La variación BCB entre 0–2/8 no se presenta como
una mejora consolidada: los fallos restantes son principalmente de
implementación de tareas (copiado de archivos, OCR, ZIP, criptografía y
excepciones), no un error de PP/TG.

El Harness también fue reforzado para que, en tareas BCB, la primera llamada
sea sobre el `Archivo requerido` exacto, sin explorar directorios padres ni
crear nombres alternativos. La repetición posterior mejoró la tasa de llamadas
de herramientas del perfil MTP3 a 92%, pero no elevó todavía el BCB final por
encima de 1/8. Por eso no se reemplaza SOL ni se declara el auxiliar como
perfil BCB-validado.

### Decisión operativa

- Mantener SOL como default general.
- Conservar el perfil conservador MTP5 como candidato de velocidad/auxiliar:
  pasa HE20 20/20 y es aproximadamente 3–5 veces más rápido en PP/TG que su
  base local, pero queda marcado como **BCB experimental**.
- No promover MTP3 por encima de MTP5: gana velocidad, pero perdió 2 casos en
  HE20 y no mejoró BCB.
- No promover la variante tensorial: alcanzó aproximadamente 4/20 en HE20
  bajo Harness aunque era muy rápida en Server Speed.

## Corrección de control de razonamiento — 2026-09-15

Se detectó una diferencia entre la intención declarada y el comando efectivo:
los perfiles con `reasoningBudget=-1` heredaban `--reasoning on` aunque
`extraArgs` contuviera `--reasoning off`. `ProfileManager::updateLaunchProfile`
no persistía los campos `reasoningBudget`/`reasoningEffort`; se corrigió y se
agregó una regresión de round-trip.

Se comparó la misma receta MTP3, KV Q8 y split por capas con razonamiento
heredado contra una copia con `reasoningBudget=0`:

| Variante | PP | TG | TTFT | HE0 | HE20 | Decisión |
|---|---:|---:|---:|---:|---:|---|
| MTP3 + razonamiento heredado (`on`) | referencia | referencia | referencia | — | — | Mantener como default del tier |
| MTP3 + razonamiento desactivado (`off`) | dentro del ruido | **-25,1% mediana** (significativo) | dentro del ruido | **1/1** | **0/20** | Rechazado y eliminado |

El resultado descarta que `reasoning off` sea una mejora de velocidad o calidad
para este auxiliar. El perfil permanente MTP3 seleccionado por el usuario no
fue reemplazado; ahora su comando efectivo y su configuración persistida son
coherentes. La variante temporal se eliminó de los perfiles guardados.

## MTP2 frente a MTP3 — 2026-09-15

Se hizo un ciclo nuevo, no repetido, cambiando únicamente
`--spec-draft-n-max 3` por `2` sobre la receta MTP3 con razonamiento heredado.

| Variante | PP | TG | HE0 | HE20 | BCB8 | Decisión |
|---|---:|---:|---:|---:|---:|---|
| MTP3 | referencia | referencia | 1/1 | 18/20 | 1/8 en corrida anterior | Mantener default |
| MTP2 | **+2,1% media** (significativo) | **+5,5% mediana**, no significativo; dentro del ruido | **1/1** | **19/20** | No ejecutable por la compuerta HE20 | Conservar sólo como candidato experimental |

El único fallo HE20 de MTP2 fue de calidad del código (`make_palindrome`,
caso unitario para una cadena de un carácter); no hubo crash, OOM ni error de
herramienta. MTP2 mejora un caso de HE20, pero no presenta una ganancia de TG
demostrada ni un BCB válido, por lo que no reemplaza al default MTP3.

## Promoción de contexto 32K — 2026-09-15

Se duplicó MTP3 sin cambiar MTP, KV, batch, ubatch ni split; sólo se cambió
`ctx-size` de 8192 a 32768. El barrido de prefill fue válido hasta 19.400
tokens reales (la petición de 32.768 tokens se truncó al máximo de contenido
generado por el corpus, no por el servidor).

| Perfil | PP corto | TG corto | Prefill largo | HE0 | HE20 | Resultado |
|---|---:|---:|---:|---:|---:|---|
| MTP3 · 8K | 1.144,7 tok/s | 228,4 tok/s | Rechaza 16K/32K (`Bad Request`) | — | — | Fallback |
| MTP3 · 32K | 1.131,4 tok/s | 228,3 tok/s | 3.500 / 3.685 / 3.624 / 3.452 tok/s a 1.247 / 4.878 / 9.718 / 19.400 tokens | **1/1** | **19/20** | **Promovido a default del tier 4B** |

La diferencia de PP corto es aproximadamente -1,2% y la de TG es despreciable;
el beneficio es la capacidad de contexto, no la velocidad. El mismo fallo de
HE20 reapareció como caso de calidad, sin OOM ni crash. El perfil 8K quedó
conservado como fallback y el 32K quedó como perfil `best`/`menuOrder=1`.

## Validación del prompt operativo y del fingerprint — 2026-09-16

Se revisó la causa de los puntajes BCB bajos antes de cambiar el runtime. La
ejecución con MTP3 y contexto 32K no presentó OOM, `device-side assert`, cierre
del servidor ni fallo de visión; los errores reproducidos fueron de calidad del
código generado y de llamadas redundantes del Harness. Para evitar mezclar
experimentos, el fingerprint de benchmark ahora incluye una revisión explícita
del prompt operativo y los resultados viejos quedan pendientes cuando cambia.

| Iteración | Cambio aislado | HE0 | HE20 | BCB8 | PP/TG | Decisión |
|---|---|---:|---:|---:|---|---|
| v3 | Completar implementación, prohibir stubs y exigir prueba mínima; luego `py_compile` y relectura de Python | 1/1 | 19/20 final tras reparación | **2/8** | ~3.100–3.400 ms TTFT; ~185 tok/s Harness | **Mejor resultado reproducido; conservar** |
| v4 | Añadir checklist demasiado específico de rutas, mocks, archivos comprimidos, bytes y escalares | 1/1 | 19/20 final tras reparación | **1/8** | ~3.100 ms TTFT; ~185 tok/s Harness | **Rechazado; más llamadas redundantes** |

La v4 sí cambió algunos fallos individuales, pero introdujo otros: perdió el
caso previamente aprobado, bajó la tasa de éxito de tools a aproximadamente
80,9% y no elevó el BCB. Se revirtió antes de dejarla activa. El binario final
vuelve a v3, con el fingerprint correspondiente, y el perfil `192_...32K`
permanece como default del tier Qwen3.5-4B. La evidencia final de BCB v3 es
2/8; no se convierte artificialmente en una validación completa.

### Diagnóstico por capa

- **Perfil/runtime:** MTP3, KV Q8, split por capas y 32K cargan y generan sin
  error de CUDA; el barrido corto conserva aproximadamente 1.131 tok/s PP y
  228 tok/s TG.
- **Contexto:** 32K no degradó TG corto y permitió prefills hasta 19.400
  tokens medidos; no es la causa de los fallos BCB.
- **Drafter/MTP:** MTP2 no mostró una mejora significativa frente a MTP3 y
  perdió calidad en un caso; se conserva experimentalmente, no se promueve.
- **Harness/prompt:** v3 mejora la completitud y la sintaxis, pero BCB sigue
  limitado por tareas de filesystem, OCR/mock, ZIP, criptografía y plotting.
  La v4 intentó sobreespecificar esos casos y empeoró el resultado global.
- **Infraestructura:** las corridas finales fueron clasificadas como calidad;
  no hay fundamento para atribuir el 1–2/8 a VRAM, P2P, OOM o al motor.

La compuerta secuencial quedó completa para el perfil activo con la mejor
receta: HE0 válido, HE20 válido y BCB válido como etapa ejecutada, aunque el
puntaje BCB sea sólo 2/8. Las corridas, fingerprints y artefactos quedan en
`~/.local/share/LlamaCode/LlamaCode/benchmark-runs/`.
