# Q162 · Revisión de PeritoSoft y gates de pruebas

- **Fecha:** 2026-10-27T04:25:08Z.
- **Lock:** se reutilizó el lock paraguas Q146 `2242863e-c78e-4fa9-9649-c1d1541f3919`.
- **Solicitud:** cerrar la app PeritoSoft y sus llama-servers si estaban activos, y continuar las pruebas.
- **Resultado de procesos:** el escaneo de `/proc` no encontró procesos PeritoSoft, `llama-server`, `llama_server` ni servidores Strata/Qwen. No hubo listeners relevantes en 32100, 32101 o 8033 ni contenedores Docker coincidentes. No se envió ninguna señal.
- **GPU:** ambas RTX 3090 visibles, 0% de cómputo; memoria informada 890 MiB y 110 MiB. Esa memoria no se interpretó como inferencia activa.
- **Pruebas:** no se inició inferencia ni benchmark porque la cola local no tiene un test habilitado en este executor. Los pendientes identificados requieren Windows nativo, una identidad/política confiable, un workflow y holdout fijos, la fuente primaria faltante, demostrar un defecto parser/runtime o una traza real de presión crítica. El gate Q119 no se reabre por memoria usada alta: ASTRA 1M y SOL ya completaron sin crash; no se observó presión crítica real.
- **Estado:** ASTRA, SOL y los datos/configuración de PeritoSoft permanecen intactos. No cambió ningún resultado, accionable ni fila del Sheet.
- **Detalle:** `receipts/peritosoft-stop-and-test-gates.json`.
