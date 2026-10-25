# Q136 — Resultados históricos añadidos a Resultados

## Resultado

Se añadieron 12 perfiles históricos únicos en `Resultados!A17:AF28`. La pestaña ahora contiene 27 registros de resultados debajo del encabezado. Se revisaron las 18 pestañas del libro y se indexaron 191 archivos locales de resultados/informes relacionados; los seis informes con evidencia de modelo utilizable fueron ampliados a filas individuales por perfil.

| Cohorte local | Filas añadidas | Qué mide |
|---|---:|---|
| Q-20261010-FRONTIER-MULTITASK-AB | 3 | Tool-Eval Hard Mode, 28 casos y 3 semillas para Q4, ASTRA IQ3_S y SOL |
| Q-20261009-STRATA-QWEN38-27B-AB | 1 | IQ2_XS/Strata, suites de coding/agentes y Hard Mode de 3 semillas |
| Q-20261010-R9700-TOOLEVAL | 3 | Tool-Eval estándar y Hard Mode v2.7 para Q4, ASTRA y SOL |
| Q-20261010-UNSLOTH-MTP-AB | 2 | Flash-Next Q4 con MTP apagado/encendido |
| Q-20261010-SALUKI-27B-EVAL | 1 | Saluki 27B IQ2-mix, dos semillas válidas |
| Q-20261014-IQ2XS-MISSING-MODALITIES | 2 | Flash-Next IQ2_XS y Qwen3.8-27B Q4_K_M en recuperación, velocidad, uso de escritorio y visión |

Cada registro incluye rutas Linux disponibles, perfil/modelo, hardware dual RTX 3090 cuando está confirmado, versión de motor, configuración y harness recibidos, resultados por semilla, seguridad/fallos y recibos locales. Las rutas Windows y las métricas no registradas quedaron como N/D.

## Lectura de comparaciones

- En Tool-Eval 2.8 Hard Mode, Q4 logró 77.38, ASTRA IQ3_S 71.43 y SOL 66.07 en el mismo grupo de tres semillas. Las herramientas son simuladas; los resultados no establecen superioridad general.
- El IQ2_XS/Strata registró 77.98 en el mismo tamaño de suite, pero falló TC-92 y TC-74 en las tres semillas. Sus otras suites incluyen reparaciones; la primera pasada se conserva en las notas.
- En Tool-Eval v2.7, Q4, ASTRA y SOL lograron respectivamente 86.67/75.33/58.00 en Hard Mode y 90.67/87.67/25.67 en Standard. Las dos versiones no son comparables numéricamente: cambiaron suite y temperatura. El informe del runner dice T=1.0; los JSON de configuración base muestran T=0.6, discrepancia señalada en las filas.
- MTP subió el decode del prompt corto de 21.22 a 30.80 tok/s, con prefill casi igual (116.25/115.38). Todas las corridas Hard Mode individuales superaron el corte de 30 minutos por perfil, así que no se promovió.
- Saluki obtuvo 76.79 con dos semillas, no tres, y falló TC-74 y TC-84 ambas veces; TC-92 filtró datos en una semilla. No se recomienda para agentes con acciones.
- En Q14, ambos perfiles recuperaron 7/7 hechos y contaron correctamente la imagen sintética, pero Computer Usage E2E fue 0/3 en ambos. IQ2_XS tuvo decode mayor y Q4_K_M prefill mayor en esa configuración cruzada; runtime y arquitectura cambiaron, así que no es una comparación de pesos aislada.

La columna “Calidad / velocidad (descriptivo)” usa `score medio / duración media por corrida` sólo cuando una suite permite ese cálculo. No es una métrica oficial y sólo debe consultarse dentro de la misma cohorte. No se calculó para las suites v2.7 mezcladas ni para las pruebas multimodales Q14.

## Filtrado y selección

No se incorporaron claims externos como si fueran mediciones locales. También se dejaron fuera fingerprints ya presentes, intentos inválidos por infraestructura, campañas incompletas sin score válido y pruebas de componentes (por ejemplo retrieval/embeddings/OCR) que no producen un resultado de perfil de modelo comparable. Los registros existentes de ASTRA, SOL y Flash-Next se conservaron intactos.

## Verificación

Se leyó de vuelta `Resultados!A17:AF28`: 12 IDs esperados, 32 columnas por fila y datos numéricos en los campos medidos. El formato nuevo coincide con las filas adyacentes (Arial 10, texto envuelto, alineación superior). No se ejecutó ningún benchmark, inferencia, descarga, build ni uso de GPU. El recibo conserva el payload exacto de las 12 filas y el resumen de auditoría.
