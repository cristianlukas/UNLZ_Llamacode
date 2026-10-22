# Q43 · Reconciliación de pendientes y preflight de búsqueda local

Fecha: 2026-10-22T17:54:04Z. Lock `b46bfeb6-5de2-4dc8-9f6d-d7aba731a510`.

## Resultado

- Se corrigió el P0 obsoleto en la app local y en `Accionables`: Q41 ya protege `tools/kv_cache_ab.py` y matrices dependientes; Q42 protege `scripts/run-astra-strata.sh`. Sus pruebas CPU-only pasaron. El P0 global permanece abierto por `tools/meter_system_profiles.py` y los entrypoints PowerShell que aún requieren Job Objects verificados en Windows.
- El P1 local de Flash-Next NInfer decía que faltaba convertir los artefactos. Eso ya lo completó C39-01: el contenedor NInfer v3 y volumen n-gram están preparados y validados. Se corrigió el accionable; el único bloqueo actual es ejecutar C39-02 desde un runner Windows nativo. Esta sesión sigue siendo Ubuntu 24.04.5, sin PowerShell/cmd, aunque el usuario informó que reparó Windows.
- El comparador PlumbSearch/SearXNG no se ejecutó: `127.0.0.1:7586` y `127.0.0.1:8080` rehusaron conexión. Se enviaron 0 consultas, no se iniciaron servicios y no se contactaron nodos públicos.
- La inspección del inbox encontró 58 entradas y `analysis.status` presente en todas. El resumen detallado queda en `receipts/pending-tests-audit.json`.

## Pruebas y recursos

No se inició benchmark, inferencia, build ni uso de GPU en Q43. No había inference server ni listener de evaluación. ArtCraft seguía usando 205 MiB de VRAM como aplicación gráfica y quedó intacta. ASTRA, SOL, Flash-Next productivo, PeritoSoft, sus perfiles y pesos no cambiaron.

El Sheet `Listado de Juegos` fue actualizado y leído de vuelta en `Accionables` filas 2, 25 y 49. Se verificaron los IDs, estados, condiciones, timestamps y formato TOP/WRAP; detalle en `receipts/sheet-reconciliation.json`.

## Reanudación

1. Ejecutar C39-02 cuando esta tarea tenga acceso a Windows nativo y runtime NInfer v0.16.1, usando los artefactos ya preparados.
2. Ejecutar el holdout de búsqueda local sólo después de que ambos endpoints loopback estén disponibles.
3. Completar P0 Windows/Job Objects en sesión nativa antes de declarar la cobertura de launchers global.

La cola de pruebas justificadas sigue activa; Q43 sólo cerró la reconciliación y registró las condiciones externas verificadas.
