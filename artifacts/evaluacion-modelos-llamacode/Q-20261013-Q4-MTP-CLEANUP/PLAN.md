# Plan — Q-20261013-Q4-MTP-CLEANUP

## Pedido

Retirar los dos perfiles de evaluación `Q4 · llama.cpp MTP-on` y
`Q4 · llama.cpp MTP-off` solicitados por el usuario, eliminar sólo los pesos
que pertenezcan exclusivamente a esas variantes, y conservar íntegros el
historial de ejecución, resultados, informes, recibos y huellas.

## Alcance y salvaguardas

- Inspeccionar el catálogo de perfiles, los archivos de configuración activos,
  los manifiestos de modelo y las referencias locales al GGUF base y al draft
  MTP.
- Confirmar dependencias y rutas exactas antes de borrar. No borrar ningún peso
  compartido por otro perfil que se conserve.
- Retirar las entradas activas de catálogo que representen exactamente las dos
  variantes indicadas; no borrar resultados ni archivos bajo tareas históricas.
- Respaldar los archivos de catálogo/configuración que haya que editar y guardar
  hashes/rutas de los pesos antes de eliminarlos.
- Validar JSON y escanear referencias residuales al finalizar; informar qué
  archivos fueron eliminados y cuáles se conservaron por uso compartido.

## Recursos y pruebas previstas

- Sin GPU, inferencia, benchmark ni descarga.
- Pruebas: validación sintáctica de JSON y búsqueda de referencias activas; no
  ejecutar suites de modelo.
- Reversión: recibos con copia previa de cada archivo de perfil/configuración
  cambiado y listado/hash de cada peso eliminado.

## Evidencia a preservar

`artifacts/evaluacion-modelos-llamacode/Q-20261010-UNSLOTH-MTP-AB/` se conserva
sin cambios, incluyendo los resultados negativos e incompletos.

## Hallazgos del preflight

- Los brazos `MTP-on` y `MTP-off` fueron configuraciones de evaluación guardadas
  en esa carpeta de artefactos; no hay perfiles activos con esos nombres ni una
  referencia activa al draft MTP dedicado.
- El archivo draft exclusivo es
  `/media/cristian/7CFE1E0FFE1DC1F6/models/unsloth-qwen38-flashnext-mtp/mtp-Qwen3.8-Flash-Next-Q8_0.gguf`:
  4.137.429.120 bytes, SHA-256
  `58a47d6a216307e9b97172d5bfdc3436a8994b632f5e436b9bb6edf8951da8d1`.
  No hay proceso con ese archivo abierto; la carpeta contiene sólo ese peso.
- Los cuatro shards UD-Q4_K_XL de 104 GB son compartidos por perfiles Q4
  existentes, incluidos el Q4 de Strata que completó 28×3 en 27:28 y otras
  configuraciones de Qwen3.8 Flash-Next. Se conservan para no romperlos.
- Por tanto, la limpieza retirará el draft MTP dedicado (y su carpeta vacía),
  pero mantendrá los perfiles Q4/Strata que no son esos dos brazos, y conservará
  los scripts/configs/resultados históricos para trazabilidad.

El recibo de preflight y el hash quedan en `receipts/cleanup-preflight.json`.

## Cierre

Limpieza completada: se borró el draft MTP dedicado y la carpeta vacía. No se
editó el catálogo/configuración de perfiles porque no había entradas activas
con los nombres exactos MTP-on/off ni referencias al draft. El Q4 base quedó
intacto por ser compartido. Las verificaciones posteriores y el espacio
liberado están en `receipts/cleanup-result.json`.
