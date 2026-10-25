# Q131 — Qwen3.8 Flash-Next Q4 262K, diez claves

## Objetivo y decisión

Repetir correctamente el screen Q4 a 262.144 tokens que Q130 encontró
incompleto: el intento previo recuperó una sola clave aunque el plan pedía diez.
Esta corrida contesta sólo si el runtime Q4 recupera diez valores sintéticos
distribuidos en una solicitud larga. No es una comparación de calidad general,
no habilita un default de 262K/1M y no modifica ASTRA/SOL ni perfiles.

## Prerregistro congelado

- Modelo/runtime: Qwen3.8 Flash-Next UD-Q4_K_XL; Strata local 0.1.41,
  configuración Q4 `context262k-q4.json` del cierre RESUME2, con las mismas
  opciones efectivas. Se copiará el config a Q131 sólo para redirigir su log y
  registrar sus hashes.
- Topología obligatoria: **ambas RTX 3090 (GPU0+GPU1), split 18/30 y el host
  completo de 128 GiB**. No se acepta un resultado de una GPU como sustituto.
  Ejecución serial, una solicitud, sin `MemoryHigh`, `MemoryMax`, límites de
  swap ni presión artificial. GUI/ArtCraft permanece abierta.
- Contexto: `262144`; usuario objetivo de ~258.000 tokens (aceptación 257.000–
  259.000 tras tokenizer local). Diez valores aleatorios deterministas únicos,
  cada uno aparece una vez en el prompt en posiciones objetivo 5%, 15%, …, 95%.
  El prompt sólo existe en memoria; se conserva hash, tokens, posiciones, fixture
  de claves, salida cruda y metadatos, no el texto completo del prompt.
- Sampling fijo: temperatura 0, top-p 1, top-k 1, seed 4242; salida máxima 512
  tokens; una petición, sin reparación, retry ni segundo pase.
- Único criterio de pase: respuesta JSON parseable con exactamente K01–K10 y
  valores exactos 10/10; además `usage.prompt_tokens` debe estar dentro del
  rango. Un 9/10, respuesta truncada, `usage` ausente o JSON inválido es fallo
  del screen; no se reintenta. Guardar tiempos de prefill/decode y total como
  observaciones de esta corrida, no como benchmark estadístico.

## Guard y protección del host

- Antes de iniciar el servicio: lock Q131 vigente; fingerprints de runtime,
  config, tokenizer y artefactos previos conciliados; dos RTX 3090 visibles;
  modelo/puerto 8350 disponibles; detectar inference servers por proceso,
  contenedor y listener. Si hay un servidor no perteneciente a Q131, no abrir un
  segundo; sólo detener el servidor PeritoSoft identificado conforme a la
  autorización previa del usuario. Dejar la GUI en paz.
- `MemAvailable >=32 GiB` al inicio; registrar OOM baseline, MemAvailable, PSI
  global, swap como telemetría, RSS del árbol y VRAM por tarjeta.
- Ejecutar el runner bajo una unidad user-systemd transitoria con timeout duro,
  `KillMode=control-group`, `OOMPolicy=stop` y sin límite de memoria. Durante la
  solicitud, muestrear cada segundo. Abortar sólo el grupo propio ante un nuevo
  OOM, `MemAvailable <20 GiB` por 15 muestras consecutivas, o PSI `some >=80%`
  / `full >=60%` por 15 muestras consecutivas. RSS/VRAM altos y swap usado no
  son por sí solos abortos. Registrar explícitamente si el guard continuó pese a
  RSS alto, PSI moderada o GUI abierta.
- Cleanup: parar el servicio propio; confirmar puerto 8350 libre, ningún proceso
  del modelo Q131 y OOM sin incremento. No matar procesos ajenos ni cambiar
  cachés, swap, driver, límites del host o perfiles productivos.

## Registro previo a la solicitud

Antes del preflight final se fijarán SHA-256 de script, config, ejecutable,
tokenizer, manifest de pesos previamente verificado y fixture; se ejecutarán
validaciones CPU-only de posiciones/unicidad/parser/guard. La fila Q131 de
Google Sheets y el accionable deben leerse de vuelta exactamente antes de
arrancar cualquier servidor.

### Enmienda preregistrada: validar la misma guarda contra las trazas reales

Antes de lanzar modelo, la transición de guard que usa el controlador Q131 se
reproducirá offline contra las 707 muestras ASTRA 1M Q117 y las 157 muestras SOL
Q127, normalizando sólo `MemAvailable`, PSI global y OOM. Se añadirá un caso de
RSS alto con headroom suficiente, un caso sintético sólo en memoria de PSI
`some`/`full` alternada por 15 muestras, y bordes sintéticos de OOM/headroom.
No se genera presión en el host ni se usa GPU. El gate requiere no cortar las
trazas exitosas por RSS/VRAM; el caso alternante debe detenerse exactamente en
la muestra 15, mostrando que un solo contador compuesto OR mantiene la racha.
Si alguna traza histórica se corta, el benchmark Q131 no se habilita hasta
resolver el falso stop y revisar la causa.

## Riesgos y límites

Es una única consulta sintética y el umbral 10/10 sólo aplica a este holdout. No
inferir calidad general, adopción, superioridad sobre ASTRA productivo ni
estabilidad de Codex a partir de una sola corrida. La auditoría disponible ya
mostró ASTRA DEFAULT 1M completado con ~51,3 GiB RSS y ~58,7 GiB disponibles, y
SOL completado en TP=2; este screen no busca reproducir presión extrema.

## Enmienda 01 — congelamiento previo a preflight y unidad aislada

Antes de probar el wrapper systemd o consultar el estado de procesos/GPUs, se
fijaron en `receipts/preregistration.json` los hashes del runner, config,
fixture, binario Strata, tokenizer y pesos. Los cuatro shards conservan sus
SHA-256 previamente verificados en Q10; tamaño, fecha y marcador `.done` actual
coinciden, por lo que no se releen 111 GB sólo para repetir el hash. El perfil
experto, pack y MTP quedan fijados por ruta, tamaño y mtime y se archivarán sus
hashes durante la verificación de assets antes de iniciar el servidor.

Se añade una prueba inocua de unidad transient con `/usr/bin/true` o un `sleep`
corto para leer de vuelta `KillMode=control-group`, `OOMPolicy=stop`,
`RuntimeMaxSec`, límites de memoria/swap en `infinity`, `PrivateNetwork=yes` y
pesos CPU/I/O. No inicia Strata ni carga modelo. Si systemd no refleja esas
propiedades, Q131 se detiene antes del servidor hasta corregir el lanzador y
registrar la enmienda.


## Enmienda 02 — separar el preflight de la línea de comandos del shell

La primera captura de estado, ejecutada como heredoc de `bash`, se marcó a sí
misma como proceso de inferencia. No arrancó ni detuvo servidores y no cuenta
como preflight aprobado. Para evitar que el texto de la comprobación contamine
la búsqueda de procesos, se preregistró `scripts/q131_preflight_snapshot.py`
con SHA-256 en `receipts/amendment-02-probe-self-detection.json`. El runner de
inferencia no cambia. La nueva captura es sólo lectura; si detecta un servidor
que no sea PeritoSoft claramente identificado, la prueba queda bloqueada.
