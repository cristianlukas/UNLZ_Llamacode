# Resultados — Q-20261017-LLAMACPP-MTP-CODING-RESUME

**Cierre:** 2026-10-17. Screening parcial; no se promueve MTP ni se cambia un
perfil productivo. Los intentos planeados se ejecutaron, pero dos quedaron
incompletos y el TaskFlow MTP-on terminó con un fallo válido de calidad.

## Resumen

| Prueba | Resultado | Clasificación |
|---|---|---|
| HE0 / HE20 | Se reutiliza la evidencia vigente del perfil: HE0 1/1 y HE20 20/20. | Gate válido para iniciar BCB8; no se repitió. |
| BCB8 MTP-off | Se completó la aceptación individual de los primeros 4/8 ítems; el prompt 4 quedó activo sin progreso útil durante más de 15 min. Se canceló el benchmark completo. | Incompleto; no es 4/8 final ni 0/8. |
| TaskFlow ULTRA MTP-off | Se observó 3/10 en el primer probe de archivos; el único prompt seguía activo a los 24 min y se canceló después de que el agente lanzara un `find /` amplio que quedó vivo. | Incompleto; no hay resultado final de 13 criterios. |
| TaskFlow ULTRA MTP-on | 0/13 final después de 3 oportunidades de reparación; `py_compile`, `unittest` y `--self-test` fallaron porque faltaban los módulos requeridos. | Fallo válido de calidad, no de infraestructura. |

No se rehicieron Hard Mode, Server Speed, HE0, HE20 ni BCB8 MTP-on; esos
resultados válidos se conservan. Una corrida por brazo de TaskFlow sólo sirve
como screening: no alcanza para afirmar una mejora estable ni para promover un
perfil.

## Condiciones fijadas

- Modelo: Qwen3.8-Flash-Next UD-Q4_K_XL, revisión
  `38bb39ee97821de2c9009abb7e93950eec396e66`; los cuatro shards coinciden con
  los SHA-256 fijados en `receipts/base-model-hashes.json`.
- Runtime: llama.cpp `836d57176dc699a726c55418e4f96b8ca628e1bf`; servidor
  aislado en dos RTX 3090, `split-mode layer`, `parallel=1`, contexto 32768,
  KV K/V q8_0, 16 threads, 999 GPU layers. Draft MTP Q8_0 SHA-256
  `58a47d6a216307e9b97172d5bfdc3436a8994b632f5e436b9bb6edf8951da8d1`.
- HarnessSpec: `cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef`.
- TaskFlow ULTRA: suite `qwen38_taskflow_ultra_ast_vs_sol_20261006`, un prompt,
  SHA-256 `f04febb440208d5bf74c01e84d78f5127e57c164fabece2acbfb346215dc0c17`.
  Seed efectiva 4242; el harness limitó temperatura efectiva a 0,1.
- Fingerprints TaskFlow: MTP-off
  `e9c5c527e30744049cff955f0489c36cd08a8777b9bf87422f0f768c3d42cf23`;
  MTP-on `b39dcfa4f912aee2ae973d28f25ac04f81e5ba1c0dbaaa2e0a7e5641e38d3d27`.
  Ambos son fingerprints específicos de TaskFlow/R8192 y no tienen una corrida
  histórica idéntica. El MTP-on difiere de la huella histórica de perfil por la
  ruta aislada del sidecar; los bytes del sidecar sí coinciden.
- BCB8: suite `05c28394-11d0-41fe-a55f-b3cb69db9c15`, ocho tareas, SHA-256
  `42771136b447b7b5619e04a1ea211f663222cd6752ca38d995083b5a4d207574`; perfil
  MTP-off con fingerprint `7f84727070a2fb93d008a42c90391f3904d800f7d7c2e67f173813ab0435ff89`.

## Detalle de las corridas

### BCB8 MTP-off

El run empezó el 2026-10-17 a las 19:33:33Z. El monitor no detectó presión de
recursos; aun así, el prompt 4/8 quedó activo más de 15 minutos. Se canceló a
las 20:17:40Z para recuperar el único slot del benchmark. Los primeros cuatro
ítems habían pasado su aceptación individual, pero el suite no cerró sus ocho
tareas y no existe un score BCB8 final. La cancelación no se interpreta como
fallo de calidad.

### TaskFlow ULTRA MTP-off

El prompt empezó a las 20:19:56Z y se canceló a las 20:43:51Z, sin completar la
tarea. El probe parcial encontró 3/10 archivos requeridos (`__init__.py`,
`models.py` y `scheduler.py`); no se ejecutó un conjunto completo de los tres
comandos de aceptación. El agente después abrió una búsqueda recursiva amplia
desde `/`, fuera del workspace, que bloqueó el turno. Se canceló el benchmark,
se detuvo el agente y sólo se terminó el proceso `find` cuya línea de comandos
se verificó como propia de este run. Este 3/10 no es el score final de
TaskFlow.

### TaskFlow ULTRA MTP-on

La tarea terminó normalmente a las 21:03:27Z, tras 1099,557 s y tres
reparaciones. La aceptación final fue 0/13: faltaban los diez archivos
(`taskflow_ultra/{__init__,models,storage,service,scheduler,query,reports,cli,main}.py`
y `tests/test_taskflow_ultra.py`), por lo que también fallaron `py_compile`, el
`unittest` generado y `--self-test`. El agente hizo 9 llamadas de herramienta;
la primera llegó a los 629,871 s, no hubo primera escritura (`firstWriteSec=-1`)
y sólo dejó un archivo monolítico de 2806 bytes llamado
`solution_taskflow_ultra_advanced_project.py`, que no satisface la estructura
pedida. Sus llamadas finales inspeccionaron el directorio y buscaron código de
llama.cpp fuera del workspace; no modificaron el repositorio. El recibo clasifica
el resultado como `quality`, `failed=true`, `timedOut=false`.

La etiqueta visual `Completado.` corresponde al cierre del flujo de benchmark;
el resultado persistido es 0/13 fallido. No debe leerse como una tarea aprobada.

## Por qué las demás tareas esperaban

Los perfiles lanzan llama.cpp con `parallel=1`. El runner avanza cada prompt
cuando recibe `turnFinished` y espera un cooldown de 250 ms para liberar el slot
CUDA; en BCB se evita avanzar antes del cierre natural para prevenir errores de
memoria CUDA. Por eso `benchmarkProgress=0` durante la generación larga no
significaba que hubiera tareas concurrentes iniciándose en segundo plano: el
turno actual y sus reparaciones ocupaban el único slot. Véanse
`src/AppController.cpp` alrededor de las líneas 21724, 22813 y 22929.

La cola de `WORK_QUEUE.md` también es una cola de coordinación manual, no un
despachador: la siguiente tarea necesita que un agente la inicie y reclame el
lock exclusivo después de este cierre. Al cierre, el archivo contiene 96 tareas
completas, cuatro bloqueadas y ninguna fila `Pendiente` o `Activa`; las cuatro
bloqueadas tienen sus condiciones de reanudación registradas y no se inician
automáticamente.

## Recursos y cierre

Las guardas no se dispararon en ninguna corrida: `MemAvailable` mínimo fue
109,29 GB en BCB8, 114,51 GB en TaskFlow MTP-off y 115,12 GB en TaskFlow MTP-on;
PSI no mostró presión sostenida y `oom_kill` quedó en 0. El postflight de
21:05:17Z registró 120,87 GB disponibles, cero procesos de cómputo propios,
benchmark/agente/servidor detenidos y puertos 18111, 18112 y 18119 cerrados.
Swap quedó como telemetría y no se modificó.

No se modificaron fuentes, perfiles productivos, HarnessSpec ni modelos. No se
ejecutó la suite C++/QML: no hubo cambios en C++/QML. No repetir estos
fingerprints para producir otra copia del resultado. Para reabrir la evaluación
de TaskFlow hace falta corregir primero el flujo de escritura al workspace y la
deriva a búsquedas externas; para BCB8 se necesita una estrategia de reanudación
que complete las ocho tareas sin romper la huella de calidad.

## Recibos

- Corridas: `receipts/bcb8-mtp-off.json`, `receipts/taskflow-mtp-off.json`,
  `receipts/taskflow-mtp-on.json` y sus `.events.jsonl`.
- Preflight, perfiles/hashes y trazas de recursos: `receipts/preflight-*.json`,
  `receipts/effective-profiles.json`, `receipts/base-model-hashes.json`,
  `receipts/resource-monitor-*.jsonl` y `receipts/postflight.json`.
- Transcripciones, archivos generados y eventos completos: `runtime/lch/`.
- Preregistro: [PLAN.md](PLAN.md).
