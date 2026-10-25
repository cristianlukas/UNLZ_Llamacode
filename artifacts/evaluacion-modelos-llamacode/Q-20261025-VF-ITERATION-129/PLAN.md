# Q129 · Auditoría de presión de memoria y gate NInfer Flash-Next Linux · 2026-10-25

## Pregunta

¿La guarda de presión de memoria está cortando por el uso alto que ASTRA DEFAULT 1M y SOL completaron con éxito? ¿Existe una ruta NInfer Flash-Next probada que permita un A/B válido en el host real de dos RTX 3090 y 128 GB?

## Alcance

- Conciliar las trazas y resultados existentes de Q97, Q116–Q118, Q126–Q128, sin repetir inferencia ni generar presión artificial.
- Separar RSS/RAM del host, PSI/OOM y VRAM. El guard AMD05 supervisa presión de memoria del host; la memoria GPU se observa por separado.
- Consultar documentación primaria fijada del release NInfer v0.16.1 y su perfil Flash-Next.
- Ejecutar un A/B de modelo sólo si la documentación y artefactos habilitan de forma explícita Flash-Next en Linux y su uso con las dos GPU físicas. No sustituir el host dual por un brazo de una GPU para decidir adopción.
- No descargar runtime/pesos, compilar, iniciar servidores, usar GPU ni cambiar modelos/perfiles en esta auditoría.

## Criterio

La guarda pasa el control de alto consumo si las cargas exitosas no detienen por RSS/VRAM alto mientras conservan headroom y no registran OOM. Se registrará aparte cualquier hueco lógico ante PSI severa. El benchmark NInfer sólo queda habilitado si la ruta runtime+modelo+plataforma+topología dual está soportada y es comparable; si falla una condición, cerrar como bloqueada con el requisito externo exacto.

## Fuentes locales fijadas

- Q117 `RESULTS.md` y traza ASTRA DEFAULT 1M: corrida real de 1.001.463 tokens, ambas RTX 3090.
- Q126 `RESULTS.md`: regresiones de frontera del helper AMD05 candidato.
- Q127 `RESULTS.md`: solicitud SOL en dual RTX 3090 y telemetría AMD05.
- Q128 `RESULTS.md`: replay contrafactual del helper histórico Q97 sobre las 707 muestras de ASTRA.
- Q116 `RESULTS.md`: regresión histórica de PSI severa alternada.

## Fuentes primarias NInfer

- Release comunitario v0.16.1 y su verificación Linux: https://github.com/ashalliants/ninfer-3090/releases
- Guía de serving/perfil Flash-Next: https://github.com/Don-Chad/ninfer-3090/blob/master/docs/serving.md
- README del runtime y límites de la ruta multi-GPU: https://github.com/Don-Chad/ninfer-3090
