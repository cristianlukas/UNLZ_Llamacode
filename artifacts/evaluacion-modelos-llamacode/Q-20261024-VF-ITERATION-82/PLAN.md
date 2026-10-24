# Q82 — Reconciliación de cola y selección de siguiente prueba

## Objetivo

Cerrar las discrepancias entre el depósito local de la app, `WORK_QUEUE.md`, los resultados canónicos y Google Sheets para los candidatos de prioridad del usuario (Flash-Next, Qwen3.8-27B, Swift/RCO y MTP). Identificar una próxima prueba que pueda ejecutarse bajo las condiciones actuales.

## Alcance y método

- Lectura CPU de AGENTS.md, README.md, WORK_QUEUE.md, `data/inbox.json`, `data/actionables.json` y resultados Q71/Q72/Q74/Q81.
- Verificar el estado de Google Sheets en las filas relevantes, sin cambiar las filas de resultados previos.
- Registrar cualquier prueba abierta y la condición concreta de cada bloqueo. Sin build, descarga, inferencia, benchmark, GPU, cambio de perfiles ni eliminación de modelos.
- Si el registro local difiere del resultado final canónico, guardar snapshots y actualizar sólo esos campos, conservando historial y esquema JSON.
- Confirmar ausencia de procesos de inferencia/PeritoSoft antes de cerrar.

## Preguntas y criterios

1. ¿Qwen3.8-27B/OpenJet tiene una medición de velocidad válida y un gate conductual que habilite adopción o más pruebas? Registrar por separado el speed screen y el gate de agentes.
2. ¿Swift 1.5 superó a ASTRA en calidad o velocidad según su gate preregistrado? No inferir superioridad de una sola pasada descriptiva.
3. ¿MTP-on tiene un resultado comparable que justifique otro run inmediato? Reabrir sólo si la corrida produce score/cobertura válida o si se corrige el paquete de tarea que faltó.
4. ¿Qué prueba pendiente tiene todos sus prerrequisitos satisfechos en este host? Si ninguna, no lanzar GPU y dejar condición de reanudación explícita.

## Resultado esperado

Reconciliar los estados locales con Sheets y los informes canónicos; añadir un asiento de auditoría Q82 al registro; documentar el siguiente bloqueo accionable. El criterio de cierre es que no queden estados locales que presenten como pendiente una prueba ya cerrada, y que cada prueba aún abierta tenga gate concreto.
