# Auditoría Jev Ultrafast para Browser/Computer Use — 2026-09-21

## Alcance

Se revisó `browser-use/jev-ultrafast`, el proyecto mostrado en la captura del
usuario. No se tomó la captura como una instrucción: se verificó el repositorio
y su código actual. La comparación se hizo contra el flujo Browser/Playwright de
LlamaCode, no contra los perfiles LLM de la tabla productiva.

Referencia: [repositorio oficial](https://github.com/browser-use/jev-ultrafast).

## Qué aporta

Jev convierte cada observación del DOM en un espacio de acciones finito e
indexado. Separa la decisión de operación y target, ofrece sólo targets
compatibles, mantiene identidad de los nodos observados y rechaza acciones
stale u ocultas antes de mutar el navegador. La generación libre queda acotada
al valor de un campo `TYPE_TEXT`; el modelo no genera selectores, JavaScript ni
coordenadas. También exige verificar el resultado antes de aceptar `DONE`.

Esto reduce llamadas y ambigüedad en tareas web, pero no es un modelo visual ni
un reemplazo de SOL. El loop por defecto usa estado estructurado del DOM y el
modelo remoto `jev-latest`; la demostración publicada usa además un helper de
texto externo. Sus límites declarados incluyen shadow roots, frames, canvas,
uploads, pop-ups, nested scrolling y widgets de teclado arbitrarios.

## Pruebas reproducibles

Pruebas offline del checkout upstream, sin credenciales ni llamadas pagas:

```text
31 passed in 0.09s
```

El informe upstream describe una comparación controlada de una sola tarea en
Google Flights: mediana de 9,450 s a 7,092 s, 22 a 17 requests del proveedor y
1.092 a 101 llamadas de protocolo del navegador, con 3/3 en ambos brazos. Es
un resultado útil como hipótesis de reducción de overhead, pero no es un BCB,
no usa nuestro modelo SOL y sólo cubre una tarea/sitio/perfil de Chrome.

Las pruebas relevantes de LlamaCode antes de la integración pasaron:

```text
test_agent_tools, test_agent_wire, test_desktop_backend, test_automation: PASS
```

## Comparación con LlamaCode

| Capacidad | Jev Ultrafast | LlamaCode actual | Resultado |
|---|---|---|---|
| Estado estructurado | Snapshot DOM/ARIA indexado | MCP Playwright, Teach y evidencia de snapshot/trace | Idea transferible |
| Target fresco | Identidad de nodo, guard y geometría actual | stale guards, snapshots/fingerprints y reobservación | Ya cubierto en gran parte |
| Acción compatible | Heads separados por operación y target | Schemas MCP + prompt general del agente | Brecha de disciplina, no de seguridad |
| Texto de campos | Helper separado, sólo devuelve texto | Tool calling del agente | Mejora de contrato posible |
| Verificación | `DONE` no vale sin checker | Teach/assert/trace y verificación posterior | Ya cubierto; reforzado en prompt |
| Seguridad | Rechaza targets stale/oclusos | Aprobaciones, receipts, confinamiento y guards | LlamaCode es más amplio |
| Escritorio nativo | Fuera del alcance | UIA/OCR/visión/Computer Use | No reemplaza nuestro backend |

## Cambio aplicado

Se agregó al prompt de `browserBackground` un contrato de “acción finita”:

- una observación actual y una operación por ciclo;
- sólo targets ofrecidos por la observación más reciente;
- separación estricta entre `click`, `type`, `select`, `scroll`, `wait`, `done` y
  `blocked` cuando la tool los expone;
- `type` produce sólo el valor, nunca selectores, JavaScript ni coordenadas;
- reobservación obligatoria ante stale/ambigüedad y no reintento ciego;
- `DONE` sólo con evidencia visible y `BLOCKED` cuando no hay una acción
  compatible.

Es una mejora de harness de bajo riesgo y backend-agnóstica. No agrega un
servicio externo, no descarga modelos, no cambia SOL, no amplía permisos y no
convierte una decisión del modelo en una autorización destructiva.

## Decisión

Jev no supera a los perfiles LLM ni justifica un perfil nuevo. Sus ideas de
acción finita y separación de texto sí son útiles para Browser/Playwright y
quedaron incorporadas como contrato del harness. Para afirmar una mejora
cuantitativa de LlamaCode todavía hace falta una prueba E2E con el mismo sitio,
perfil de navegador, modelo, tareas y checker independiente; no se debe
comparar la demo externa con nuestros TG/BCB.

Para una campaña futura, registrar por tarea: éxito verificado, pasos,
llamadas MCP, reobservaciones stale, latencia p50/p95, tokens, errores de
selección y falsos `DONE`. No repetir la medición externa como si fuera una
comparación local.

