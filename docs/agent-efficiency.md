# Eficiencia, contexto estructurado y workflows

LlamaCode implementa estas capacidades de forma propia y desacoplada del agente:

- `AgentEfficiency`: normaliza telemetría `timings` de llama.cpp y `usage` de
  proveedores OpenAI-compatible, agrega por fase y calcula comparaciones A/B.
- Prefijo estable: el system prompt contiene un protocolo fijo y los cambios
  Plan/Ejecución se agregan como controles cortos al final del historial. El
  runner continúa aplicando el bloqueo efectivo de tools en Plan.
- Checkpoints de sesión versionados: cada turno persiste longitudes UI/API y
  restaura snapshots al abrir. Las sesiones antiguas reconstruyen checkpoints
  conservadores sin inventar snapshots de archivos.
- `StructuredSourceView`: produce una vista efímera compacta con mapeo byte a
  byte al original. Nunca escribe la proyección; rechaza sintaxis dudosa y
  lenguajes sensibles a indentación, donde se usa la fuente exacta.
- `WorkflowEngine`: máquina de estados determinista con pasos agent/tool,
  aprobación, condiciones/paralelo/verificación como tipos validados,
  presupuestos y snapshots JSON reanudables. La ejecución real debe pasar por
  los runners existentes para conservar permisos y límites de concurrencia.

## Esquema de workflow v1

```json
{
  "schemaVersion": 1,
  "entry": "explore",
  "budget": { "maxIterations": 12, "maxSeconds": 1800 },
  "steps": {
    "explore": { "type": "agent", "next": "review" },
    "review": { "type": "approval", "accept": "execute", "reject": "stop" },
    "execute": { "type": "tool", "onSuccess": "verify", "onFailure": "stop" },
    "verify": { "type": "verify", "onSuccess": "finish", "onFailure": "execute" },
    "finish": { "type": "finish" }
  }
}
```

Tasks y Automations preservan un objeto `workflow` opcional. Los registros de
historial preservan `workflowState` y `metrics`. Los registros legacy siguen
siendo válidos.

La vista visual es una proyección editable y sin pérdida: conserva campos avanzados,
ramas, argumentos, presupuestos y metadata que no representa gráficamente, y al
guardar modifica únicamente los campos visibles de cada nodo.

## Benchmark A/B

Comparar con el mismo modelo, quant, contexto, prompt, temperatura y hardware:

1. Prefijo estable apagado/encendido.
2. Fuente exacta/vista estructurada.
3. Caché fría y caliente por separado.
4. Cinco pasadas como mínimo y orden aleatorio.

Registrar tokens de prompt/generados, tiempos de prefill/generación/pared,
tool calls, bytes de tools, éxito, reparaciones, RAM y VRAM. Una variante pasa
el gate si reduce al menos 15% tokens o 10% tiempo sin reducir éxito ni producir
ediciones incorrectas.

El primer resultado exitoso de cada combinación suite/perfil/target queda marcado
automáticamente como baseline. Las corridas posteriores persisten su ID y los deltas
de tiempo y calidad, para evitar comparaciones manuales ambiguas.

## Límites de seguridad

- Un workflow no ejecuta shell directamente: solicita una tool al runner.
- Cambiar de fase no modifica permisos.
- Una proyección compacta nunca es destino de edición.
- Un hash/cambio de archivo debe invalidar cualquier proyección cacheada.
- Acciones destructivas conservan aprobación humana incluso dentro de jobs.

### Suite E2E fija

`assets/benchmarks/custom/agent_efficiency_e2e_v1.json` se distribuye con la app.
Sus IDs, prompts, límites y comandos de aceptación están versionados; una comparación
válida usa la misma revisión de la suite, modelo, perfil, hardware y cantidad de
pasadas. El resultado persistido aporta calidad, tiempo, tokens y uso de tools.

## Project Brain incremental

El manifiesto schema v2 persiste únicamente metadata y SHA-256. Un refresh completo
reutiliza el hash cuando tamaño y mtime coinciden. Después de una escritura del agente,
o al recibir `changed_paths`, actualiza sólo esos archivos/subárboles y reporta
`scanMode=events` y `changes.added/updated/removed/reused`. El cache es regenerable y
no guarda contenido fuente.

## Parser estructural opcional

`read_file(compact=true)` intenta `tree-sitter parse --xml` si encuentra el CLI (o
`LLAMACODE_TREE_SITTER`) y el archivo existe. La vista se construye con las hojas del
árbol y conserva el mapeo exacto al byte original. Sólo marca
`parserBackend=tree-sitter-ast` ante un árbol completo sin `ERROR`/`MISSING`; cualquier
ausencia, timeout, gramática no instalada o mapeo dudoso cae automáticamente al
validador lexical conservador.

## Scheduler persistente

Al habilitar Tasks programadas se registra el companion `--scheduler-daemon` en el
inicio de sesión del sistema operativo. Un heartbeat permite distinguir registro y
proceso activo; deshabilitar el scheduler elimina el registro. El daemon conserva el
lock de instancia e IPC existentes.
