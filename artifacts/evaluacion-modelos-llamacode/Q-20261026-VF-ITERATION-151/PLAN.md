# Q151 — retirar variantes de modelos no elegidas

## Solicitud y alcance

Por instrucción del usuario, eliminar las 20 variantes de la lista comparativa salvo SOL Qwen3.8-27B AutoRound INT4/W4A8 y ASTRA Qwen3.8 Flash-Next RCO IQ2_XS. No tocar la copia activa del MTP compartido que necesita ASTRA IQ2_XS. Conservar métricas, resultados, recibos, configuraciones y documentación histórica.

## Preflight

- Lock vigente del lote VF: `2242863e-c78e-4fa9-9649-c1d1541f3919`.
- PeritoSoft está cerrado por el usuario; sus `.env` actuales apuntan a Qwen2.5, Qwen2.5-VL y Nomic, no a las variantes de esta lista. BigBang sólo aparece como asignación en un benchmark histórico, sin ruta/config actual.
- No se observó proceso de inferencia activo.
- ASTRA IQ2_XS, SOL y el árbol de MTP compartido están explícitamente excluidos del borrado.
- UD-IQ4_XS comparte manifiesto, inventario y los artefactos runtime del MTP con la copia que se conserva para ASTRA. UD-Q4_K_XL comparte los tres artefactos runtime comprobados por SHA-256.

## Método

El recibo `receipts/storage-cleanup-preregistration.json` enumera cada ruta exacta, tamaño, dispositivo, inodo y número de enlaces; la suma previa está separada por dispositivo. Antes de borrar se volverá a comprobar que ningún proceso tiene abierto un archivo candidato, que su identidad no cambió y que las dos variantes protegidas siguen fuera del manifiesto. Sólo se retirarán pesos, sidecars de modelo, packs exclusivos, MTP duplicado asociado a candidatos descartados y fragmentos `.incomplete` dentro de las rutas del target W8A16. Se conservan manifests, tokenizers, índices, configs, logs, recibos, benchmarks, runtime y drafters auxiliares separados.

## Pruebas de cierre

Reconciliar cada ruta borrada, revisar nuevamente los directorios de los dos supervivientes, confirmar ausencia de procesos consumidores, comprobar `df` por volumen y actualizar el inventario del Google Sheet preservando resultados y rutas previas como historia. No ejecutar inferencia, benchmarks ni GPU.


## Cierre

El borrado se completó con 139/139 rutas retiradas, 0 errores y 861.385.845.611 bytes de archivos. La verificación postflight confirmó que no queda ninguna ruta candidata y que SOL, ASTRA IQ2_XS y el árbol MTP compartido siguen presentes. El Google Sheet quedó actualizado en las pestañas `Modelos locales por peso` e `Inventario de modelos`; los resultados históricos se conservaron. Ver `RESULTS.md` y `receipts/storage-cleanup-completion.json`.
