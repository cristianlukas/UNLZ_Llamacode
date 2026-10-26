# Q144 — reconciliación de resultados históricos

## Objetivo
Revisar resultados locales antiguos contra el contenido del libro de Google Sheets y sumar a `Resultados` las mediciones verificadas que faltan, sin duplicar filas ni confundir fallos operativos con puntuaciones de modelo.

## Reglas de carga
- Mantener filas por perfil/configuración y cohorte cuando existan métricas comparables.
- Usar `N/D` para información ausente; distinguir un resultado no puntuable por infraestructura de un cero de calidad.
- No interpretar smoke de salida truncada como evaluación de calidad.
- Conservar como evidencia local las rutas relativas a sus informes y recibos fuente.
- Anexar filas; no editar datos existentes.

## Alcance
Auditoría de `Resultados` y pestañas de IA existentes, además de los artefactos históricos `source/artifacts` y `source-post-eval-tests/docs` del cache local. Solo cambios documentales/Sheet; cero ejecución de modelos.
