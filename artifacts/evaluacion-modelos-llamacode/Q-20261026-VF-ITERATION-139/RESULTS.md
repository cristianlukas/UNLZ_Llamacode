# Q139 — Auditoría de históricos y sincronización de Resultados

**Fecha:** 2026-10-26
**Estado:** completo; sólo lectura y migración documental. No se ejecutaron pruebas, build ni inferencia/GPU.

## Resultado

Se revisaron las 18 pestañas del Google Sheet y los históricos locales. El tab `Resultados` tenía 177 filas de datos hasta la fila 178. El escaneo local encontró 202 archivos `RESULTS.md`; las migraciones Q136/Q137 y las filas más recientes ya cubrían gran parte del historial. Se anexaron 15 registros que faltaban y que conservaban evidencia verificable:

| ID añadido | Resultado registrado | Alcance / decisión |
|---|---|---|
| `Q29-QWEN38-27B-Q4KM-BASELINE` | 80,33/100; semillas 77/84/80 | Control de calidad que Q32 citaba y no estaba visible en `Resultados`. No midió TPS; TC-74 y TC-84 fallaron 3/3 y TC-92 falló 2/3. No adoptar. |
| `ASTRA-TASKFLOW-20261008-R8192-3REPAIR` | ASTRA 13/13 en dos corridas; tiempos 287,296s y 333,456s | TaskFlow ULTRA, perfil calibrado, reasoning 8192 y tres reparaciones. Promedio 310,376s; evidencia de una suite, no calidad general. |
| `SOL-TASKFLOW-20261008-R8192-3REPAIR` | SOL 7/13 en una corrida válida, 138,365s | Cuatro intentos operativos inválidos quedaron excluidos. Menor tiempo en una sola observación, pero menos criterios completados y distinta cantidad de réplicas. No reemplaza ASTRA. |
| `Q06-H2-ASTRA-PILOT` | 1/3 casos, 23/27 aserciones | Piloto sintético Harness²; un fallo de contrato aunque la recomendación de contexto fue prudente. |
| `Q07-H2-ASTRA-TRIAGE-V2` | 0/4 casos, 7/28 aserciones | Harness²; tres respuestas truncadas por el límite de 1400 tokens. |
| `Q08-H2-ASTRA-TRIAGE-V3` | 1/4 casos, 16/29 aserciones | Harness²; hubo truncamientos con límite 2200 y fallos del contrato de evidencia. |
| `Q09-H2-ASTRA-TRIAGE-V4` | 2/4 casos, 27/29 aserciones | Harness²; mejoró el flujo, pero quedaron dos selecciones de estado incorrectas. |
| `Q10-H2-REASONING-NONE` | 1/6 casos, 25/48 aserciones; 2661 tokens | Screen sintético pareado; 0 truncamientos. |
| `Q10-H2-REASONING-LOW` | 2/6 casos, 29/48 aserciones; 7896 tokens | Screen sintético pareado; 3 truncamientos. No confirmó que `low` fuera fiable. |
| `Q11-H2-LOW-2200` | 2/6 casos, 29/48 aserciones; 12385 tokens | Subir límite 1200→2200 no añadió pases ni redujo truncamientos. |
| `Q12-H2-COMPACT-PROMPT` | 0/3 casos, 16/21 aserciones; 1640 tokens | La recomendación de un slot fue correcta 3/3; el estado exacto falló 3/3. |
| `Q13-H2-STATUS-EVIDENCE-TAXONOMY` | 0/3 casos, 3/21 aserciones; 1033 tokens | El gate de evidencia rechazó las tres salidas. |
| `Q14-H2-SEQUENCE-TAXONOMY` | 0/3 casos, 18/21 aserciones; 735 tokens | Flujo y evidencia correctos; estado incorrecto 3/3. |
| `Q15-H2-STATUS-BOUNDARIES` | 2/3 casos, 20/21 aserciones; 725 tokens | Pasó el screen; sólo habilitaba una confirmación aparte, no un cambio productivo. |
| `Q16-H2-STATUS-HOLDOUT` | 1/3 casos, 17/21 aserciones; 712 tokens | El holdout independiente no confirmó Q15; candidato cerrado. |

Los registros Harness² son resultados del mismo ASTRA IQ2_XS/Strata 0.1.41 y de fixtures sintéticos con prompts/esquemas distintos. Se rotularon como pruebas del harness, no como benchmark general de coding ni comparación de modelos. Se conservaron como cohortes separadas y se dejaron TPS/E2E como N/D cuando los recibos no los medían.

## Duplicados y exclusiones

- Q19 de contexto/JSON de 700K no se agregó como fila nueva: coincide con la huella experimental de Q56 en shards, fixture, answer key, esquema, contexto, semillas y configuración; Q56 ya contiene la reconciliación final y el postanálisis. Se evita contar una repetición/sucesión como resultado independiente.
- No se importaron intentos sin solicitudes/score, fallos de infraestructura previos a cargar modelo, ni pruebas CPU de componentes de la app como si fueran perfiles de inferencia.
- Q136/Q137 y las filas ya existentes se dejaron intactas. El retest TaskFlow 2026-10-08 se mantuvo separado del par TaskFlow 2026-10-06 ya registrado.
- No se inventaron rutas Windows, prefill/decode TPS, hash de pesos ni telemetría cuando el informe no los conservaba; esas celdas dicen N/D o aclaran la limitación.

## Verificación del Sheet

Los 15 registros se anexaron en `Resultados!A179:AF193`, con el formato del último registro: Arial 10, ajuste de texto y alineación superior. La lectura posterior coincidió exactamente en las 480 celdas; IDs, score/decisión, evidencia y métricas clave fueron verificados. No se encontraron validaciones ni chips en las filas añadidas. `Resultados` quedó con 195 filas de cuadrícula y conserva las dos filas vacías finales preexistentes.

Recibo estructurado: `receipts/google-sheet-sync.json`.
