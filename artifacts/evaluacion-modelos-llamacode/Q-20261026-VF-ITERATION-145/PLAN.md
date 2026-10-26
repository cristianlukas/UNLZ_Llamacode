# Q145 · Reconciliar resultados históricos locales con Resultados

## Objetivo
Revisar resultados de modelos/harness guardados fuera de la campaña central y las 18 pestañas del Google Sheet; añadir a `Resultados` solamente pruebas locales con recibo legible, cohorte/configuración identificable y valor histórico útil.

## Límites
- Solo documentación y Google Sheets. Sin benchmark, inferencia, build, descarga, servicios ni GPU.
- No modificar ASTRA, SOL, Flash-Next productivo ni perfiles.
- No mezclar cuantizaciones, engines o harnesses con cohortes distintas.
- Marcar muestras cortas/sintéticas y resultados incompletos; usar N/D si la fuente no lo informa.
- Evitar duplicados por ID, modelo/revisión, suite, fingerprint y recibo.

## Fuentes revisadas
- Workbook completo “Listado” (18 pestañas), con foco en IA local, Evaluaciones LlamaCode, Inventario de modelos, Accionables, Enlaces revisados y Resultados.
- Informes/recibos locales seleccionados fuera de la tabla principal: Swift Genesis; Qwen3.8 Coder IQ1_M paired; QwFN-hybrid; Strata Q2_0, Strata-DualGPU 0.1.38 y contexto 262K; WebBrain browser cancellation; WebBrain/LFM vision smoke; DeepSeek short-smoke matrix.
- Historial central y filas existentes para comprobación de duplicados. No se migraron resultados ya representados.

## Operación de Sheet
Añadir 22 filas append-only a `Resultados`, conservar los 32 campos, copiar formato desde la última fila y verificar readback exacto, IDs únicos, WRAP/TOP/Arial 10 y panes congelados.
