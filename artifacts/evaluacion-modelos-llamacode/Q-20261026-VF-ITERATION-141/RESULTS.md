# Q141 — Resultados históricos conciliados en Google Sheets

**Estado:** completado el 2026-10-26. Se hizo una migración documental; no se
ejecutaron inferencias, benchmarks, builds ni uso de GPU.

## Alcance y resultado

- Se inventariaron 195 archivos `RESULTS.md` del repositorio y se cotejaron las
  pestañas de IA `IA local`, `Evaluaciones LlamaCode`, `Accionables`,
  `Inventario de modelos` y `Resultados`.
- `Resultados` tenía 192 registros. Se añadieron 32 cohortes/perfiles históricos
  que tenían métricas locales y no estaban ya representados, en
  `Resultados!A194:AF225`. La pestaña queda con 224 registros.
- Los resultados se mantienen separados por suite, contexto, cuantización y
  configuración. Las corridas parciales siguen marcadas como parciales; los
  valores no disponibles dicen `N/D`.
- `Inventario de modelos` se actualizó para ASTRA IQ2_XS, ASTRA IQ3_S y Flash-Next
  UD-Q4_K_XL, y se agregó la ficha local de Ekbasis en la fila 23. La ruta Linux
  de Ekbasis identifica el depósito de evaluación; el recibo no confirma una
  ruta Windows ni el snapshot exacto servido.

## Cohortes añadidas

- **Q35 ASTRA IQ2_XS:** los brazos de 262K y 524K que faltaban de la matriz
  4×3. A 262K las tres salidas llegaron al límite y quedaron en 6/8, 7/8 y
  8/8; a 524K hubo 2/3 respuestas completas con 8/8. El default sigue en 131K.
- **Q14 contexto ASTRA:** cuatro screens de recuperación NIAH, con 10/10 hechos
  en una corrida por tamaño de 131K a 1M, y cuatro mediciones separadas de
  velocidad con salida fija de 64 tokens. No se mezclan los TPS de ambos
  fixtures; la lectura de 1M tardó 449,17 s por request en NIAH.
- **Q09 caché de compactación:** control apagado y candidato encendido, tres
  pares. El control recuperó 4/4 en 3/3; el candidato lo hizo en 2/3 y produjo
  una salida corrupta 0/4. Se conserva apagada por defecto.
- **Q14 sampling ASTRA 1M:** temp 0,1, 0,6 y 1,0; los tres brazos dieron 0/13
  en cada una de sus tres semillas por la misma repetición de `!`.
- **Q14 Flash-Next UD-Q4_K_XL TaskFlow:** 13/13 después de dos reparaciones, en
  una única corrida; queda como señal exploratoria, no como promoción.
- **Q130 `--trim-stage-weights`:** brazo control y candidato, tres pares. El
  primer par favorece al control y los otros dos al candidato; no hay dirección
  estable ni métrica de calidad.
- **EkBasis:** pantalla textual Q09 y seguimiento visual/contexto Q15. Se
  registraron exactitud, seguridad sintética, latencia y límites; no se
  recomienda integrarlo ni delegarle permisos.
- **Muse:** cuatro brazos del screen textual Q09 y cuatro condiciones de GUI en
  Q13 y Q16. Las suites textuales quedaron en 72/72 en base y overlay, con más
  latencia en el overlay. Las dos rondas de GUI quedan como cohortes
  independientes y desbalanceadas; no se promueve el overlay.

## Deduplicación y límites

Los registros Q10 Frontier, Saluki, MTP y R9700 que ya estaban en `Resultados`
se dejaron en su cohorte actual. Q19 no se repitió como fila porque su fixture
con huella coincidente ya está representado por Q56. Las auditorías de
publicaciones sin benchmark local, los intentos inválidos y los resultados sin
score no se transformaron en perfiles de rendimiento. La pestaña operativa
`Evaluaciones LlamaCode` conserva el historial de esas entradas y sus bloqueos.

Ningún resultado cambia el default ASTRA de 131K, activa la caché de
compactación ni promueve un perfil Flash-Next/SOL. El uso de PeritoSoft no se
infirió a partir de rutas locales.

## Verificación

La lectura de vuelta coincidió en las 1.024 celdas de las 32 filas nuevas. La
ficha Ekbasis, las tres notas de inventario y el resumen superior también
coincidieron. `Resultados` conserva 1 fila congelada y 4 columnas congeladas;
las filas nuevas tienen ajuste de texto, alineación superior y Arial 10.
`Inventario de modelos` conserva sus 3 filas congeladas y wrap. No se modificó
código del producto.

Recibo: `receipts/google-sheet-sync.json`.
