# Resultados — Q-20261013-MUSE-CU-E2E

**Cierre:** 2026-10-13.

**Estado:** screening E2E completado; comparación provisional e incompleta.

**Lock:** token propio 9c0b9b2c-9b75-402f-a0f7-2c9dc134e00f; se liberó al registrar el cierre en WORK_QUEUE.md.
**Evaluación estructurada:** receipts/assessment.json. Cada intento tiene una sección review añadida a su run.json; screenshots, OCR, logs y configs se preservan junto a los recibos.

## Resultado efectivo

| Modelo | Brazo base | Brazo overlay | Celdas completas |
|---|---:|---:|---:|
| ASTRA IQ3_S calibrado | 2/3 | 3/3 | 5/6 |
| Flash-Next Q4 UD-Q4_K_XL | 2/3 | 3/3 | 5/6 |
| **Total** | **4/6** | **6/6** | **10/12** |

Las 10 celdas completas pasaron la secuencia de tres tareas. Calculator confirmó 1387 y 1363. Text Editor mostró visualmente la línea inglesa exacta, con el documento sin guardar (Draft); en la tarea final se verificó “Resultado verificado: 1363”. Las capturas de editor se revisaron manualmente. AT-SPI expuso título/estado del documento, pero no el cuerpo.

Las réplicas 2 de ambos brazos base no pudieron cerrarse. En ASTRA base, el primer intento se trabó con snapshots AT-SPI vencidos y el segundo no abrió Calculator, aunque sí dejó visible la línea del editor; la tercera tarea no se verificó. En Q4 base, el primer intento llegó al editor con la línea visible pero expiró antes de la tercera tarea; el reintento calculó 1387, abrió un documento en blanco y expiró. No se cuentan como celdas completas. ASTRA overlay réplica 1 tuvo un primer intento incompleto por snapshots obsoletos y un segundo intento completo.

Los diez runs que terminaron informan 2/3 éxitos automáticos: el OCR no transcribe de manera fiable el texto del editor. Ese contador crudo no sustituye la inspección visual manual ni se presenta como 10/12 OCR-success. La evaluación efectiva registra separadamente resultado de cada tarea, evidencia visual y OCR.

## Qué no se puede concluir

La diferencia 6/6 vs 4/6 no demuestra que el overlay mejore Computer Usage: las dos réplicas faltantes están en el brazo base y el contraste no está balanceado. No hay potencia ni comparación estadística para un ganador. El A/B textual previo mantuvo 100% en ambos brazos, pero su mediana de latencia aumentó 6,83% en ASTRA y 9,87% en Q4, superando el gate de +5%; no se promovió el overlay.

El endpoint declaró modalidades text-only. Aunque el agente manejó apps reales mediante herramientas desktop y se conservaron capturas, el modelo no recibió imágenes. Visión no fue probada. Tampoco se probaron audio/Ingi-Charla, coding/agentes, contexto largo ni velocidad de servidor independiente. El contexto configurado de 131072 no convierte estas tareas cortas en una prueba de recuperación larga. No se ejecutó una suite dedicada de prompt injection.

## Fallos y reintentos conservados

- ASTRA base r1: Strata no anunció READY en 900 s; cero requests GUI.
- ASTRA base r1, intento 2: fallo de captura xwd/BadColor por herencia de DISPLAY; sin score.
- ASTRA base r2, intento 1: timeout de 300 s y acciones AT-SPI sobre snapshots obsoletos después de la tarea del editor.
- ASTRA base r2, intento 2: la calculadora no apareció; falló la tercera tarea.
- ASTRA overlay r1, intento 1: cinco acciones sobre snapshots obsoletos; retry completo conservado como ASTRA overlay r1 intento 2.
- Q4 base r2, intento 1: expiró en el editor tras stale snapshots; tercera tarea no intentada.
- Q4 base r2, intento 2: timeout de 300 s con documento vacío; no se verificó escritura ni tercera tarea.

No hubo más reintentos después de registrar estos resultados. Los servidores propios fueron detenidos; se verificó que no quedaran procesos del ensayo, Xvfb :97 ni listeners en 8350/8898. La GPU volvió a su nivel de escritorio, aproximadamente 1424 MiB en GPU0 y 108 MiB en GPU1.

## Decisión

No promover el overlay ni cambiar perfiles, prompts globales, HarnessSpec o código de producto. Se obtuvo evidencia útil de manejo E2E de dos apps, pero no un A/B completo. Para reabrir la pregunta, usar una app/fixture holdout distinto o corregir el problema de observabilidad del editor antes de preregistrar una comparación balanceada.

No se corrieron build ni tests del repositorio: no hubo cambios en C++, QML, core ni harness de producto. La evaluación ejecutó tareas E2E reales dentro del escritorio aislado y validó sus estados con recibos, capturas y OCR donde aplicaba.
