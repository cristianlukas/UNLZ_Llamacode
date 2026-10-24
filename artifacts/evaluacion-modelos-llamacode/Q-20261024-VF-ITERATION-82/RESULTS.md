# Q82 — Reconciliación de la cola y siguiente prueba

## Decisión

La cola local ya refleja los cierres de OpenJet/Qwen3.8-27B, Swift 1.5 y MTP Q4. No hay una nueva prueba de GPU desbloqueada en este host Linux. No lancé inferencias, benchmarks, builds ni descargas.

## Auditoría de resultados

- **OpenJet Qwen3.8-27B:** Q71 validó una señal candidate-only de velocidad para `qwen38-perf` d4 frente al control en 18 pares y tres workloads. Q71 d4-vs-d7 completó 18 pares y d7 no cumplió su gate. Q74 terminó 12/12 ejecuciones técnicas pero aprobó 7/12 conductuales: TC-74 0/3, TC-84 1/3, TC-92 3/3 con fixture sintética. No adoptar para agentes ni repetir esta huella.
- **Swift 1.5 Flash-Next IQ2_XS:** Q72 dio 1/8 a Swift y 1/8 a ASTRA; el gate de Swift era ≥3/8. El E2E de una pasada fue 17,55 s frente a 17,69 s y las tasas TPS fueron descriptivas, sin semillas/holdout suficientes para afirmar ventaja. No abrir el follow-up 28×3 ni adoptar.
- **MTP Q4:** Q81 MTP-off cerró con 2/13 checks y cobertura incompleta; 21,1858 TPS y TTFT 150,8235 s son mediciones de esa corrida, no una comparación aprobada. MTP-on terminó por hard-timeout a 1.801,104 s con 4/13 checks aprobados, sin score/TPS/TTFT válidos y con HE0/HE20/BCB pendientes. Mantener MTP-off. Un nuevo estudio necesita corregir el paquete generado (faltó `service.py`; compile/unit/self-test fallaron) y un preregistro nuevo.
- **Contexto ASTRA:** Q35/Q37 ya probaron 131K–1M con tres semillas y una plantilla sintética. A 1M se recuperaron 8/8 valores en las tres semillas, pero no hubo ganancia demostrada sobre los casos completos a 131K; la latencia fue ~10,6× y bajó prefill/decode. Mantener el default en 131K y habilitar más contexto sólo si el workload lo exige. El smoke S57 sólo confirmó que ASTRA puede iniciar a 1.048.576; no se extrapola a otros perfiles.

## Próximas pruebas y bloqueos

- Flash-Next/NInfer C39-02 requiere sesión Windows nativa. Este host informa Linux x86_64 y no tiene `pwsh`, PowerShell ni `cmd.exe`; no hay equivalencia válida que sustituya ese gate.
- Swift/NInfer sigue condicionado por compatibilidad verificada de formato MTP/runtime y hashes del artefacto.
- OpenJet sólo se reabre tras un cambio material de modelo, runtime, orquestador/backend o un workload distinto preregistrado.
- MTP sólo se reabre después de reparar el paquete TaskFlow y validar compile, unit tests y self-test antes de reservar GPU.
- No hay ninguna prueba pendiente cuyo gate se satisfaga sólo porque PeritoSoft se cerró.

## Procesos y sincronización

El inventario de procesos de las 13:30:18 UTC no encontró `llama-server`, vLLM, NInfer, OpenJet ni PeritoSoft. No se terminó ningún proceso. Se actualizaron los tres accionables locales que aún mostraban estados pendientes y la entrada VF-20261019-01 secuencia 54. Sus snapshots previos y hashes están en `receipts/local-reconciliation.json`.

La fila `Evaluaciones LlamaCode!C304:J304` del Sheet recibió este cierre Q82. El readback coincidió con los ocho valores escritos y confirmó formato WRAP. Ver `receipts/google-sheet-sync-q82.json`.

## Reanudación

El siguiente trabajo de inferencia es el gate NInfer en un host Windows nativo. En este host, esperar a que cambie una condición externa; no repetir fingerprints cerrados ni inferir superioridad desde los screens descritos arriba.
