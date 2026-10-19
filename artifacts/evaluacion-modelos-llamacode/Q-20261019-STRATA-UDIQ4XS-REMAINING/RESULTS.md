# Resultados — Q-20261019-STRATA-UDIQ4XS-REMAINING

**Estado: bloqueada antes de inferencia; 0 pruebas nuevas.** El usuario pidió completar las pruebas pendientes del screening UD-IQ4_XS. No se inició el servidor ni se cargó el modelo porque las dos RTX 3090 mostraron actividad sostenida durante el preflight.

## Preflight

- 2026-10-19T20:47–20:49Z: GPU0 osciló entre 9% y 67% de SM; GPU1 entre 16% y 52% en las muestras recogidas. Los snapshots finales mostraron 33% y 22% (GPU0/GPU1). `nvidia-smi --query-compute-apps` no enumeró procesos de cómputo. No se intentó atribuir ni detener la carga.
- MemAvailable: 122.283.760 KiB; swap libre: 8.589.930.496 bytes.
- HDD de evaluación: 236.197.289.984 bytes libres. Los tres shards GGUF y el pack MTP aparecen en el directorio dedicado; los hashes no se repitieron en este preflight.
- Puertos 18354, 8354 y 8350: sin listeners en la comprobación.
- No hubo descarga, build, servidor, inferencia, benchmark nuevo ni cambio de perfil/producto. Por eso no corresponde correr `scripts/tests-linux.sh Release`.

## Cobertura

HE20, BCB8 y TaskFlow ULTRA siguen sin ejecutar. Se conservan sin cambios los resultados previos de API, speed screen y HE0 de `Q-20261010-STRATA-UDIQ4XS-POST`; no cuentan como cobertura de la escalera restante. Computer Usage, visión, audio y retrieval poblado requieren campañas separadas.

## Reanudación

Esperar a que GPU0 permanezca ociosa al menos 60 s, confirmar que no hay inferencia ajena, adquirir un lock nuevo y revalidar hashes/runtime/puertos. Entonces ejecutar HE20 → BCB8 → TaskFlow ULTRA en serie y guardar cada resultado, incluidos fallos y tiempos. No iniciar otra tarea del repo automáticamente: `WORK_QUEUE.md` es una cola manual.
