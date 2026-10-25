# Q132 · reconciliar el seguimiento del guard de memoria · 2026-10-25

## Alcance

Reflejar en el accionable `q119-memory-pressure-composite-streak` y en la entrada general #57 del inbox los resultados Q131. La evidencia nueva incluye el screen Q4/262K sobre las dos RTX 3090 y el replay guard de ASTRA/SOL ya registrado en Q131.

Esta iteración sólo actualiza registros locales, WORK_QUEUE, documentación y Google Sheets. No inicia servidores, inferencia, benchmark, build ni uso de GPU. No integra AMD05 ni modifica los guards Q97/Q100, perfiles o modelos productivos.

## Criterios

- Conservar el gap de PSI severa alternada de Q97/Q100 como abierto y AMD05 como candidate-only.
- Registrar que el RSS alto observado con headroom no provocó falsos cortes; distinguirlo del problema de PSI alternada y de los cierres de Codex.
- Mantener 131K como default productivo; el resultado Q4/262K es una recuperación sintética de una solicitud, no calidad general.
- Actualizar sólo las celdas de estado/evidencia del accionable Q119, preservar formatos y verificar los vecinos.
- Crear backup fechado de `actionables.json` e `inbox.json` antes de la escritura local.

## Evidencia de partida

- Q117/Q118/Q126/Q127/Q128/Q131: trazas y resultados citados en Q119.
- Q131 Sheets: `Evaluaciones LlamaCode!A352:J352`, `Accionables!A19:N19`, Inventario de modelos Qwen Flash-Next y replay ASTRA.
- Q119 actual: `Accionables!A18:N18`, estado de guard candidate-only.

## Límite

Q132 no convierte la evidencia del screen en una integración ni en una prueba causal de crash de Codex. Gates que requieren Windows nativo quedan pendientes por indicación del usuario.
