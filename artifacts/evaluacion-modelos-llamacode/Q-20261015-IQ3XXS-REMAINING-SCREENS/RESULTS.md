# Resultados — Q-20261015-IQ3XXS-REMAINING-SCREENS

**Fecha:** 2026-10-15. **Estado:** completada como screening parcial; el screen
262K quedó sin score y Computer Usage terminó con 1/2 tareas completas.
**Lock:** `611718ad-bc12-4a31-ac59-263ebbae5a53`.

## Resumen

| Screen | Resultado | Clasificación |
|---|---|---|
| IQ3_XXS, recuperación con contexto nativo 262.144 | Tres intentos detenidos por la guarda de recursos antes de API-ready; ningún prompt enviado. | Incompleto por infraestructura/guarda; no es cero de calidad ni prueba de capacidad. |
| Control visual ASTRA IQ3_S | 9/11 campos exactos: formas 4/4; colores 5/7. Amarillo se contó como naranja. | Corrida válida de calidad; sin exact match. |
| CU IQ3_XXS r2 | Calculator: 1387 verificado. Text Editor: repitió y duplicó la línea, después agotó recuperación AT-SPI por snapshots obsoletos. | Resultado operacional válido: 1/2 tareas; falla de agente en el editor con endpoint y escritorio sanos. |
| Audio/Charla | Sin petición de audio. El model card no declara ASR/TTS y la ruta `/v1/audio/transcriptions` había devuelto 404 en la auditoría previa. | No aplicable; no se atribuye calidad acústica. |

No se repitieron coding, HE0/HE20/BCB8, ADV, TaskFlow, Server Speed ni el
retrieval 115K: ya tenían resultados de la campaña y no eran los screens
pendientes de este follow-up. Sin edición de C++/QML/core, cambios de perfil,
build, tests de producto, descarga de pesos ni promoción de modelo.

## IQ3_XXS: contexto 262K

Se conservaron tres intentos con el backend Strata v0.1.41, contexto máximo
262.144, KV int8/resident 32768, MTP4 y muestreo
`T=.6/top-p=.95/top-k=20/min-p=0/repeat=1/presence=0`. Los tres alcanzaron el
límite de `pswpout` global configurado por el controlador antes de API-ready;
no hay solicitud ni respuesta que puntuar. La tercera corrida excedió 65.536
páginas (~257 MiB) con MemAvailable alrededor de 79 GiB y sin procesos CUDA
ajenos. El conteo `pswpout` siguió variando fuera del proceso del servidor, así
que no identifica presión causada por esa carga. No hubo OOM.

El primer controlador fue sobrescrito por el helper al iniciar el segundo
intento; el archivo `context262k-attempt-01-disposition.json` reconstruye el
estado observable (no API-ready, sin prompt, proceso detenido y puerto cerrado)
y marca explícitamente esa limitación de recibo. Los intentos 2 y 3 conservan
recibos completos. El plan cierra 262K aquí; no se considera una prueba de que
el modelo falle a 262K.

## ASTRA IQ3_S: control visual

La tercera ejecución llegó a `/v1/chat/completions` y confirmó `images: true`.
Las dos previas no generan score: la primera fue detenida por la guarda antes de
cargar y la segunda recibió HTTP 404 porque el runner usó la URL base en vez
del endpoint de chat; se corrigió el runner antes de la corrida puntuada.

En la repetición válida, sobre el mismo fixture geométrico congelado usado con
IQ3_XXS, ASTRA contó correctamente círculo 2, triángulo 2, rectángulo 2 y
estrella 1 (4/4 categorías de formas). En colores devolvió azul 1, rojo 1,
verde 1, amarillo 0, naranja 2, violeta 1 y negro 1: 5/7 valores, con
amarillo/naranja confundidos y sin match exacto. La respuesta fue JSON válido,
sin error de transporte; 558 tokens de prompt y 108 de completion. Esto iguala
la limitación observada en el screen visual IQ3_XXS; no da base para promover
ASTRA ni para cambiar el perfil.

## Computer Usage: réplica r2

El servidor IQ3_XXS llegó a API-ready y se mantuvo sano durante la ejecución.
En Calculator, el agente abrió la app, escribió `73*19=` y verificó `1387` con
los controles de la ventana: **pasa**.

En Text Editor, el agente escribió la línea solicitada, pero el control accesible
no expuso el cuerpo del documento y `desktop_assert` no encontró allí el texto.
En lugar de informar ese límite como pedía la tarea, el agente volvió a insertar
la línea varias veces; el OCR de la captura final muestra contenido duplicado y
corrupto. La última secuencia llegó a una acción sobre un snapshot obsoleto; el
guard del runner cortó tras cinco acciones obsoletas en el mismo turno. **Falla
la tarea del editor.** No fue una caída de API, app ni escritorio. El recibo
`run.json` incluye la tarea parcial, acciones, mensajes, captura de pantalla y
OCR; la inspección visual confirma el error aunque el OCR sea imperfecto.

## Recursos, limpieza y artefactos

Postflight: MemAvailable 107,84 GiB, swap libre 1,80 GiB, PSI de memoria
`avg10=0`; sin procesos CUDA de inferencia propios. Servidor y daemon detenidos,
sesión Xvfb y apps cerradas; puertos 8350, 8351 y 8898 cerrados. No se ejecutó
`swapoff`.

- Plan y guardas: `PLAN.md`.
- Configuraciones/huellas: `receipts/configs/`; el fixture visual tiene SHA-256
  `7526fe77533223bc8dc5ab5ea00af77eae16b3a10a634dadd225591e2cdd9bbf`.
- Controladores y monitor de recursos: `receipts/*controller.json` y
  `receipts/logs/*resource-monitor.jsonl`.
- ASTRA visual: `receipts/vision/astra-control-attempt-03.json` y
  `receipts/astraVision-attempt-03-controller.json`.
- CU: `receipts/runs/iq3xxs-base-r2-try3/run.json` y sus PNG/OCR; cierre del
  controlador en `receipts/cuRetry-attempt-02-controller.json`.
- No se actualiza la matriz de benchmarks estándar: estos son screens de
  modalidad, y el de 262K no alcanzó a inferir.

Decisión: no cambiar defaults ni recomendar IQ3_XXS para CU/visión/contexto 262K.
Para CU queda un fallo de manejo de verificación en Text Editor; para visión
persiste el error de color; para 262K falta un nuevo diseño de preflight/medición
antes de cualquier futura repetición.
