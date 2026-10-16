# Plan preregistrado — Q-20261016-FLASHNEXT-FOLLOWUP

- Fecha: 2026-10-16.
- Lock: `7e5aa78d-d037-4529-9efd-3be34d6a8610`.
- Solicitante: usuario; continuación explícita de la evaluación Flash-Next/Strata.
- Estado inicial: `Q-20261009-FLASHNEXT-IQ3XXS-AB` terminó con cobertura parcial; `Q-20261010-FLASHNEXT-Q4-P100-POST` fue complementada por TaskFlow el 2026-10-14. La cola no tenía filas `Pendiente`; esta campaña se activa con un ID nuevo.

## Objetivo

Completar las mediciones útiles que faltan para el post Q4/Flash-Next y comprobar
localmente el reclamo nuevo de `STRATA_STAGE_TRIM`. No promover modelo ni cambiar
perfiles, defaults, prompts globales o HarnessSpec.

## Evidencia que se reutiliza; no repetir

- IQ3_XXS vs ASTRA en coding/agentes, TaskFlow, ADV, Server Speed (n=2), vision,
  retrieval de 115K y Computer Usage: artefactos de `Q-20261009-FLASHNEXT-IQ3XXS-AB`,
  `Q-20261014-IQ3XXS-MODALITY-FOLLOWUP` y `Q-20261015-IQ3XXS-REMAINING-SCREENS`.
- Q4 UD-Q4_K_XL coding/agents, ADV, TaskFlow y tool-eval ya cuentan con screens
  válidos; el TaskFlow Q4 fue 11/13 inicial y 13/13 tras dos reparaciones, n=1.
  No repetirlos para esta hipótesis de memoria/rendimiento.
- El E2E Computer Usage anterior dejó incompleta la segunda réplica base de
  ASTRA y Q4; hay 10/12 celdas completas. Sólo esas dos réplicas pueden
  repetirse, con el recovery guard actual, sin reabrir los brazos overlay.
- Flash-Next no tiene ASR/TTS local: no enviar texto como prueba de audio ni
  medir WER/CER sin corpus. El audit previo queda como no aplicable.
- El 262K de IQ3_XXS abortó tres veces antes de API-ready por un contador global
  de `pswpout` que avanzó también sin el servidor; no repetir esa huella ni esa
  guarda. Esta campaña mide otra cuantización (Q4) con supervisión por MemAvailable,
  PSI y procesos propios.

## Hipótesis y criterios

### A/B de `--trim-stage-weights`

- Modelo: Unsloth UD-Q4_K_XL, revisión `38bb39e` (reutilizar hashes del manifiesto
  existente); Strata local 0.1.41, commit `fb58e0dbc8399662c0e47c76578c6e878b14f6cf`;
  dos RTX 3090; split explícito 18/30; KV int8, ventana residente 32768,
  MTP4, contexto 131072, una solicitud concurrente y el resto de flags de la
  configuración Q4 existente.
- Control A: configuración local original, sin el flag.
- Candidato B: copia aislada del mismo config con sólo `--trim-stage-weights`;
  mantener `layer_split=18` explícito. Si el binario local no reconoce la opción,
  no sustituir silenciosamente por otra versión ni por otro flag: registrar y
  terminar ese brazo como no ejecutable.
- Medición: LlamaCode Server Speed v1 (mismo JSON/hash de corpus), temperatura 0,
  top-p 1, seed 424242, una solicitud, warmup 1. Tres pares alternados A/B,
  B/A, A/B; cada corrida mide cold y warm de las ocho categorías. Mantener cada
  perfil debajo del corte acumulado de 30 minutos. Registrar TTFT, prefill,
  decode, latencia total, outputs, carga, RSS/PSI, VRAM por GPU, slots/cache de
  expertos y todos los errores. Reutilizar el corpus dentro de este A/B está
  permitido para emparejar; es una repetición intencional, no evidencia de
  calidad nueva.
- Umbral: sólo describir una mejora local si la dirección se repite en los tres
  pares y las diferencias superan la dispersión observada. No usar el dato de
  tres GPU/2080 Ti como comparación directa ni declarar promoción global.

### Contexto Q4 262K

- Sólo con preflight aprobado: una solicitud nueva con `max-context=262144`,
  prompt objetivo ≥249K tokens (95% del límite), diez valores sembrados en
  posiciones distintas y verificación exacta; usar la configuración Q4 y el
  flag B sólo si el A/B confirma que el motor lo acepta. Registrar `usage`,
  recuperación por hecho, prefill/decode, carga, RSS, VRAM, swap y PSI.
- Screen de una corrida, no benchmark estadístico ni réplica de 4×P100.
  No puntuar calidad si falta respuesta, truncamiento o `usage` válido.

### Visión Q4

- Si el `mmproj` oficial local y el ejecutable de visión son compatibles, usar
  la misma imagen geométrica congelada del screen IQ3_XXS/ASTRA y el mismo
  schema/prompt para añadir un punto comparable Q4; guardar salida cruda y
  conteos. No inferir visión desde texto ni descargar pesos sin necesidad.
- Si no hay encoder/`mmproj` o el endpoint no confirma `images: true`, cerrar
  esta rama como no ejecutable y conservar el audit como límite.

### Computer Usage

- Si X11/Xvfb, AT-SPI, OCR y los runners aislados están disponibles, ejecutar
  sólo la réplica 2 base faltante de ASTRA IQ3_S y Q4 sobre Calculator y Text
  Editor, con el mismo entorno/criterios, recovery guard actualizado, capturas y
  verificación de estado final. No acceder al escritorio `:0`.
- Si el control accesible no expone el documento, el agente debe abstenerse de
  reintentar escrituras sin evidencia fresca; guardar captura/OCR y clasificar
  el resultado como operacional, no como fallo de infraestructura.

## Guardas de recursos y abortos

- Antes de cargar: lock propio vigente; ambos GPUs sin procesos de inferencia
  ajenos; MemAvailable ≥32 GiB; swap libre ≥1 GiB; endpoints/puertos de prueba
  libres. No ejecutar `swapoff`, no limpiar cachés y no detener procesos ajenos.
- Durante inferencia: registrar PSI y MemAvailable cada 1 s. Abortar el proceso
  propio si MemAvailable <20 GiB durante 15 muestras consecutivas, PSI memory
  `some avg10 ≥80%` o `full avg10 ≥60%` durante 15 muestras, sube el contador
  OOM del sistema, aparece fallo CUDA o falla la API. Tras observar en A que
  SwapFree descendió a 0.76 GiB sin PSI alta y volvió a 1.07 GiB al cerrar el
  servidor, se añadió antes de B un aborto adicional si SwapFree queda debajo
  de 0.5 GiB durante 15 muestras consecutivas. No usar `pswpout` global como
  límite único.
- Las ramas se ejecutan secuencialmente y sólo si su propio preflight pasa.
  Si una rama no puede ejecutarse, guardar la causa y la condición de reanudación;
  no forzar el escenario.

## Cierre previsto

Guardar configs efectivas, hashes, runner, prompts/fixture, logs, respuestas,
telemetría, capturas y resultados bajo `artifacts/evaluacion-modelos-llamacode/Q-20261016-FLASHNEXT-FOLLOWUP/`;
actualizar el documento canónico y la cola. No editar C++/QML ni perfiles
productivos; por tanto no aplica build/test de producto.
