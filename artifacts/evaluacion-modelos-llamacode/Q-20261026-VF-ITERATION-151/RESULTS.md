# Q151 — retiro de variantes de modelos no elegidas

**Estado:** completado · 2026-10-26. Se atendió la instrucción de retirar las 20 variantes de la lista comparativa, preservando SOL Qwen3.8-27B AutoRound INT4/W4A8 y ASTRA Qwen3.8 Flash-Next RCO IQ2_XS.

## Resultado

- Se quitaron **139 archivos y enlaces simbólicos** de los 20 grupos descartados, con **861.385.845.611 bytes** de tamaños de archivo (861,386 GB decimales) y cero errores.

| Volumen | Archivos/enlaces retirados | Bytes retirados | Libre antes | Libre después |
|---|---:|---:|---:|---:|
| C | 12 | 127.711.119.296 | 27.693.899.776 | 155.404.980.224 |
| D | 69 | 455.775.333.159 | 44.374.118.400 | 500.149.567.488 |
| HDD extra | 58 | 277.899.393.156 | 35.352.924.160 | 313.252.384.768 |

Los bytes retirados son la suma de tamaños de archivo. El espacio libre observado por `df` puede diferir levemente por bloques/metadata y actividad del sistema.

- SOL, ASTRA IQ2_XS y el MTP compartido con ASTRA siguen presentes. Las rutas exactas están en el recibo local y en la planilla privada del usuario.
- No se tocaron métricas históricas, resultados, configuraciones, tokenizers, índices, logs, runtime ni drafters auxiliares fuera de la lista.
- PeritoSoft estaba cerrado por indicación del usuario; el preflight no encontró referencias actuales a las variantes retiradas. No se encontró un servidor de inferencia activo.

## Inventario

Se actualizó el Google Sheet **Listado**:

- `Modelos locales por peso`: las 20 variantes retiradas figuran con 0 bytes, estado retirado, ruta previa y peso anterior. ASTRA IQ2_XS y SOL conservan ubicación, peso y métricas. El encabezado aclara que el orden es el ranking anterior al borrado.
- `Inventario de modelos`: las filas existentes correspondientes a modelos retirados se marcaron sin sobrescribir resultados ni métricas; el resumen ya refleja Q151.
- Readback: 20/20 filas retiradas muestran `Retirado` y 0 bytes; los dos supervivientes mantienen sus valores. Se actualizaron valores de celda solamente y se preservó el formato.

## Evidencia

- Prerregistro con rutas, tamaños, dispositivos e inodos: `receipts/storage-cleanup-preregistration.json` (recibo local; no se publica al remoto).
- Cierre local con verificación de supervivientes y rutas: `receipts/storage-cleanup-completion.json` (recibo local; no se publica al remoto).
- Resumen sin rutas locales: `receipts/storage-cleanup-public-summary.json`.
- Los pesos grandes no se hashearon durante el borrado para evitar releer cientos de GB; cada archivo regular se verificó por dispositivo/inodo/tamaño/enlace único justo antes del unlink. Ningún candidato estaba abierto en el preflight.
- No se ejecutó inferencia, benchmark, build ni uso de GPU.
