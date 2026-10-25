# Q130 — Reconciliar la continuación Flash-Next antes de repetir pruebas

## Objetivo

Comprobar, sólo con recibos locales ya existentes, si los pendientes de
`Q-20261016-FLASHNEXT-RESUME` realmente siguen sin ejecutar o fueron completados
por `Q-20261016-FLASHNEXT-FOLLOWUP`/`RESUME2`. Corregir el estado canónico y la
hoja si hay contradicción. No repetir inferencia o benchmarks ya registrados.

## Prerregistro

- Hipótesis: el par 3 A/B y las ramas Q4 262K, visión y Computer Usage están
  completos en `Q-20261016-FLASHNEXT-RESUME2`, aunque el estado anterior de
  `Q-20261016-FLASHNEXT-RESUME` aún diga “bloqueado/2 de 3 pares”.
- Validaciones CPU/offline: consistencia de los seis brazos A/B (16 muestras,
  configuración y limpieza); integridad del recibo 96/96; resultado y
  clasificación del intento Q4 262K; score visual Q4; revisión manual CU de
  ASTRA/Q4; postflight y bloqueos explícitos de audio.
- Éxito: cada afirmación de `RESUME2/RESULTS.md` coincide con sus recibos y los
  tres pares del A/B están completos en la campaña original. Documentar el
  resultado y marcar el registro intermedio como supersedido por RESUME2.
- Sin nuevo uso de GPU/modelo, descarga, build, carga de memoria o proceso de
  servidor. No cambiar ASTRA, SOL, perfiles ni modelos protegidos.
- Si aparece un desacuerdo o falta de recibo, preservarlo y no volver a inferir
  hasta aislar una hipótesis material nueva.

## Fuente y alcance

- Campaña: `artifacts/evaluacion-modelos-llamacode/Q-20261016-FLASHNEXT-FOLLOWUP/receipts/server-speed/`.
- Resultados posteriores: `artifacts/evaluacion-modelos-llamacode/Q-20261016-FLASHNEXT-RESUME2/`.
- Conciliación secundaria: filas 39–41 de `Evaluaciones LlamaCode`.
- Hardware original: 2×RTX 3090; los recibos son del setup dual, no de un brazo
  de una sola GPU.

## Enmienda tras descubrir recibos posteriores

La campaña original contiene pair 3 A/B completos, aunque el informe de
`RESUME` se cerró antes de ese cierre posterior. El objetivo de este turno es
reconciliar ese historial sin repetirlo. Además, la comprobación del runner de
contexto encontró que `probe_q4_262k.py` contiene una sola `KEY`, mientras el
plan pide diez valores. Si el recibo de attempt05 confirma una sola clave,
marcar el screen como capacidad de una clave y abrir una nueva prueba de diez
valores; no tratarlo como cumplimiento del criterio original.

Para visión, extraer sólo el JSON entre fences del response ya guardado y
recomputar los once campos contra el fixture. No repetir inferencia por el
fallo del parser de fences. Registrar Computer Usage usando la revisión manual
existente de capturas, no el OCR que se documentó como poco fiable.
