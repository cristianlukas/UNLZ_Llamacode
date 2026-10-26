# Q146 · Auditoría histórica de Resultados y ampliación de la pestaña · 2026-10-26

## Objetivo
Contrastar informes y recibos locales antiguos con el workbook completo “Listado” y anexar a `Resultados` los resultados locales útiles que aún no estén representados.

## Alcance y método
- Releí las instrucciones del repo, README, cola y lock Q146. Lock vigente: `2242863e-c78e-4fa9-9649-c1d1541f3919`.
- Inspeccioné metadata/rangos usados de las 18 pestañas del workbook. Para deduplicación volví a leer los 289 IDs previos de `Resultados!A2:A290`, sus columnas de identificación, y el header/formato real de `Resultados!A1:AF1).
- Revisé informes locales con evidencia de Mica, MiMo, Opti, Laya, LFM2.5-VL DSpark, Qwen3.8 throughput/HumanEval, Flash-Next IQ1_S, NInfer Qwen3.6-35B, ExLlamaV3 Flash-Next, BeeLlama KVarN5/KVarN4 y Ling 3.0 Tiny.
- Se anexan sólo perfiles con resultado local verificable, incluyendo controles necesarios, contexto/throughput, tests parciales y fallos de configuración cuando cambian la interpretación.
- No se derivan scores ni TPS no informados. Las celdas sin dato medido usan `N/D`; los perfiles/suites incompatibles quedan en cohortes distintas.
- No se agregan afirmaciones externas como resultados locales, campañas sin salida puntuada, benchmarks incompletos sin evidencia de resultado, ni duplicados ya registrados en Q135–Q145 / ledger histórico.

## Escritura y verificación
- Filas nuevas: `Resultados!A291:AF346` (56 filas × 32 columnas, 1.792 celdas), append-only después de las 289 filas anteriores.
- IDs: prefijo único `Q146-HIST-`; 56 únicos, sin repetidos internos ni colisión con IDs previos.
- Inserción con herencia de formato de fila anterior y escritura de texto literal en `userEnteredValue`.
- Readback realizado: 56×32 valores exactos, 0 diferencias; 56 IDs nuevos y únicos; 0 fórmulas, chips o validaciones. Se conservaron WRAP/TOP/Arial 10 y paneles congelados (fila 1, columnas A:D); metadata final: 346 filas en la grilla.

## Límites
Los resultados históricos conservan los límites de su propio informe: muestras pequeñas, targets model-only vs agent, distintas builds/hardware/cuants, pruebas de humo, fallos de loader/infraestructura y métricas no comparables. La pestaña permite encontrarlos y comparar dentro de cada cohorte; no constituye un ranking global ni cambia defaults.
