# Prompt reusable: evaluar ideas externas para LlamaCode

Pegá este prompt junto con el post, comentario, repositorio o informe que quieras
revisar. Si no hay adjunto, pegá el texto al final.

```text
Leé la referencia adjunta completa y revisá las evaluaciones previas de
LlamaCode antes de proponer o repetir una prueba. Determiná qué afirmaciones son
hechos verificables, cuáles son impresiones/anécdotas y qué partes podrían servir
para uno o más de estos objetivos: Ingi-Charla (voz y diálogo), Computer Use /
control de escritorio, harness de agente/coding, modelo/perfil o runtime.

Usá el README, AGENTS.md y docs/benchmark-manual.md como guía. Busca evidencia
en docs/benchmark-results.md, docs/benchmark-results-history.md,
docs/benchmark-profile-ledger-2026-08.md, docs/benchmark-profile-matrix.md,
docs/benchmark-ranking-and-use-cases.md y los informes/artefactos enlazados.
Buscá por modelo, quant, runtime, perfil, suite, hardware y fecha. Antes de
ejecutar, comprobá si ya existe la misma combinación y configuración. No repitas
una corrida idéntica: reutilizá su evidencia y explicá qué pregunta nueva queda
por responder. Si hace falta repetir para medir variación, declaralo como
repetición estadística y cambiá sólo semilla/orden según el protocolo.

Para cada hipótesis, fijá el baseline vigente más relevante (incluí SOL y ASTRA
cuando corresponda) y una candidata. Especificá antes de correr: pregunta,
caso de uso, métrica primaria, guardas de no-regresión, hardware, modelo/archivos
y hashes disponibles, quant, runtime/commit, perfil efectivo, sampling,
contexto/KV, suite/prompts, harness, agente, tools, seed, timeout, pasadas y
criterio de promoción. Mantén constantes las variables que no estés evaluando.
Si una diferencia de arquitectura, quant, hardware o configuración impide un A/B
justo, documentá el límite y no presentes la comparación como equivalente.

Cuando la afirmación dependa de usar más recursos o concurrencia, tomá una línea
base antes de cargar el candidato y registrá pico de RAM residente/pinned,
`MemAvailable`, uso de swap antes/después, VRAM por GPU y slots simultáneos. Fijá
un margen de RAM que debe quedar disponible y un umbral de aborto antes de iniciar;
no interpretes “usa toda la RAM” como una mejora por sí sola. Para claims de
“termina el trabajo más rápido”, medí el tiempo hasta un artefacto que pase
validaciones, los errores y las intervenciones humanas, además de tok/s. Separá
una corrida serial de otra con concurrencia/subagentes; no mezcles sus resultados.

Elegí pruebas que respondan la hipótesis, no una puntuación genérica:
- Coding/agente: usá el harness real de LlamaCode y seguí HE0 → HE20 → BCB;
  añadí adversarial o una suite pertinente. Conservá por separado primera
  pasada, reparaciones, resultado final, llamadas de tools, errores, tiempo y
  tokens. Una prueba de endpoint directo no sustituye el loop del agente.
- Para una comparación difícil de uso de herramientas, añadí `tool-eval-bench`
  Hard Mode: **28 tareas (TC-70…TC-97) × 3 semillas por perfil** (`42`, `43`,
  `44`), con `variant_seed=20261010`. Fijá la versión de la suite (v2.8.0 para
  esta receta), sampling común (`temperature=0.6`, `top_p=0.95`, `top_k=20`,
  `min_p=0`, `repeat_penalty=1`, `presence_penalty=0`), `reasoning_effort=medium`,
  `parallel=1`, máximo 8 turnos y timeout de 120 s por request. Mantén idénticos
  suite, escenarios, herramientas, límites y semillas; ejecutá perfiles de a uno
  si comparten recursos. Informá el score y los estados pass/partial/fail por
  semilla y escenario, tasa de completitud, tiempo y fallos de endpoint. Las
  herramientas son simuladas: esta suite complementa HE/BCB y el agente real,
  pero no mide ejecución en aplicaciones, GUI ni calidad general de coding.
  Reutilizá resultados históricos sólo cuando coincidan la huella de suite y
  las condiciones; si runtime, plantilla o hardware difieren, describí el
  resultado como comparación de perfiles completos. Conservá los recibos crudos
  y no cuentes fallos de infraestructura como errores de calidad. El corte de
  interés para el usuario es **30 minutos acumulados como máximo por perfil para
  las tres semillas**. Estimá el tiempo con evidencia existente o una primera
  semilla; si la proyección de las tres supera 30 minutos, no inicies o detén las
  semillas restantes, registra el parcial con su proyección y no lo presentes
  como comparación completa. Una solicitud explícita posterior puede cambiar
  este límite.
- Computer Use: separá exactitud/seguridad y latencia del corpus textual de la
  operación real de escritorio. Para promover control general, probá más de una
  app y variaciones razonables de layout/idioma/resolución; revisá observación,
  acción, verificación y recuperación.
- Ingi-Charla: medí por separado ASR, TTS y diálogo integrado, incluida latencia
  de turno, interrupciones, calidad en español y estabilidad; una prueba de LLM
  de texto no certifica la ruta de voz.
- Runtime/velocidad: fijá modelo y quant si querés aislar el motor. Medí
  prefill/decode, TTFT, tiempo hasta completar la tarea, RAM/VRAM por GPU,
  errores y concurrencia. Reportá si el sistema queda interactivo bajo carga.

Descargá sólo los pesos, binarios o datos necesarios para resolver una pregunta
que todavía no tenga evidencia local; verifica origen, versión, licencia,
integridad, espacio y requisitos antes de usarlos. No reemplaces modelos,
perfiles ni defaults vigentes para probar: creá una variante candidata aislada.
Podés liberar recursos GPU usados por corridas de LlamaCode si hace falta,
registrando qué detuviste; no mates procesos ajenos sin comprobarlos. Ejecutá las
pruebas necesarias hasta obtener evidencia suficiente o identificar un bloqueo,
sin convertir fallos de infraestructura en fallos de calidad.

Al terminar, guarda un informe reproducible y los artefactos no sensibles:
referencia y fecha, hipótesis, decisión, comandos/config efectiva, hashes,
hardware, suites/prompts, resultados crudos y agregados, fallos, tiempos,
memoria, limitaciones y pasos exactos para repetir. Actualizá la tabla viva y el
historial de resultados, el ledger de perfiles, la matriz/ranking y los enlaces
del README según corresponda. Dejá una nota explícita
de “No repetir” que identifique las combinaciones ya cubiertas y qué cambio
habilitaría otra corrida. No guardes secretos, credenciales ni workspaces que
puedan contenerlos.

Promové sólo en el caso de uso que la evidencia respalde. Una anécdota, una
ventaja de velocidad aislada o una única pasada no justifica cambiar un perfil
BEST/default. Para promover, confirma una mejora repetible en la métrica
primaria, sin regresiones importantes en calidad, seguridad, estabilidad,
latencia, memoria, concurrencia o funciones requeridas. Si falta evidencia,
dejá la variante como experimental y enumera el siguiente gate concreto. Si es
superadora, integra únicamente el cambio aplicable, actualiza su documentación y
ejecuta los gates de build/tests indicados por AGENTS.md. Conservá los cambios
ajenos del árbol de trabajo.

Entrega: resumen ejecutivo; tabla de hipótesis y resultado; comparación con el
baseline por caso de uso; decisión (promover / experimental / descartar / no
concluyente); archivos cambiados; comandos/gates ejecutados; links a informe y
artefactos; y sección “No repetir”.
```
