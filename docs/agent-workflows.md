# Workflows de ingeniería

LlamaCode incluye presets declarativos sobre el motor de Tasks para ordenar el
trabajo del agente sin hardcodear una aplicación, una resolución o coordenadas.

Presets disponibles:

- `investigate`: inspección, hipótesis, aprobación y validación de causa raíz.
- `qa`: preflight, reproducción, corrección, prueba de regresión y verificación.
- `document-audit`: detección de documentación obsoleta, faltante o contradictoria.
- `review`: revisión funcional y revisión de alcance en paralelo.
- `release-check`: revisión del estado, `tests.bat Debug`, `build.bat Debug NOPAUSE`
  y aprobación final.

Los presets se instalan desde Tasks como procesos normales. Cada ejecución usa
los snapshots, aprobaciones, permisos y reanudación del motor existente. El
workflow sólo describe intención y pasos; la resolución concreta queda a cargo
del agente y de las tools autorizadas por el workspace.

## Seguridad

Los perfiles disponibles son `normal`, `investigation`, `guarded` y `production`.
En particular, `release-check` nunca hace commit ni push automáticamente: deja
la aprobación final en la interfaz para que el usuario revise el resultado.

Los workflows no deben asumir nombres de aplicaciones, botones, colores,
layouts ni coordenadas. Para browser y escritorio deben usar las capacidades
semánticas, OCR, evidencia y templates de Teach ya existentes.

## Evidencia y pruebas

Un workflow exitoso debe dejar un resumen de pasos, resultados, herramientas y
aprobaciones en el historial de la Task. `qa` debe agregar o justificar una
prueba de regresión y `release-check` debe verificar el ejecutable Debug según
las instrucciones de `AGENTS.md`.
