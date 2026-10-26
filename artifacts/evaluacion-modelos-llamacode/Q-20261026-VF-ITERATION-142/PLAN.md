# Q142 — conciliación de resultados locales con `Resultados`

**Estado:** completada; reconciliación del Sheet verificada y recibos locales guardados.

## Alcance

Revisar informes de evaluación antiguos y las 18 pestañas del workbook para hallar mediciones locales de modelos/perfiles que sigan sin una fila propia en `Resultados`. No ejecutar modelos, benchmarks, builds ni GPU. No modificar otras pestañas del Sheet ni datos productivos.

## Revisión de cobertura

- Leídos `AGENTS.md`, `README.md`, `WORK_QUEUE.md` y `WORK_QUEUE.lock`; lock Q142 creado con O_EXCL.
- Leídos metadatos de las 18 pestañas, `Resultados!A1:AF225`, las pestañas IA local, Evaluaciones LlamaCode, Inventario de modelos, Accionables y Panel; búsqueda acotada por `Qwen` y `prefill` en las 18 pestañas.
- Inventariados 196 archivos locales `RESULTS.md` (193 en el nivel raíz del directorio de evaluaciones). El Sheet tenía 224 filas de datos, todas con ID único. Los IDs nuevos se comprobarán de nuevo justo antes de escribir.

## Filas candidatas para añadir

1. `Q10-P100-UDQ4KXL-LCH1`: Flash-Next UD-Q4_K_XL, LC-H1 + ADV, una sola corrida.
2. `Q10-EG2-*` (5 filas): control BM25 y cuatro condiciones de EmbeddingGemma 2 en el screen de recuperación de 21 consultas. Cohorte separada del holdout posterior Q44.
3. `Q15-ANYJEV-RAW` y `Q15-ANYJEV-L0`: clasificación sintética de routing; perfiles de decisión separados, no calidad general ni autoridad para acciones.
4. `Q14-IQ3XXS-MODALITIES`: recuperación a 115K, visión sintética y Computer Usage; se añade la evidencia de seguimiento Q15 con su intento de editor fallido separado.
5. `Q15-ASTRA-IQ3S-VISION`: control visual de una corrida sobre fixture sintético.
6. `Q19-UDIQ4XS-HE20`: HumanEval20 válido 20/20; BCB/ADV/TaskFlow incompletos, sin score.

Son 11 filas previstas. Se conservarán cohortes y suites separadas, se usarán N/D para métricas no medidas y se anotará el alcance exploratorio.

## Exclusiones y deduplicación

- Q19 JSON Schema ~680K no se copia: la auditoría Q141 determinó que la huella/fixture ya está representada por Q56.
- Saluki Hard Mode, ASTRA 1M/Q35, Q14 modalidades IQ2XS/Q4, Q09 IQ3XXS, Q10 Frontier y Q130 trim ya tienen filas.
- Sin score, abortos antes de inferencia, auditorías documentales de claims externos y pruebas de software/harness sin evaluación de modelo no se convierten en scores de modelo.
- EmbeddingGemma Q10 y Q44 se mantienen en cohortes distintas: fixtures de 21 consultas diferentes, no se comparan métricas entre ambos.

## Escritura y verificación

Releer `Resultados!A1:AF225` y los metadatos inmediatamente antes de escribir; insertar 11 filas al final (`A226:AF236`) sin sobrescribir. Copiar formato de la última fila, escribir valores, leer de vuelta 352 celdas, comprobar IDs únicos, formato wrap/Arial 10/TOP y freeze panes 1 fila + 4 columnas.
