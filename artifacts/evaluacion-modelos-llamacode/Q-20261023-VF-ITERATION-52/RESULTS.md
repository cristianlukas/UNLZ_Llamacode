# Resultados Q52

## Decisión
No se habilitó ninguna inferencia ni descarga. La revisión actualizó la evidencia de cuatro fuentes, pero ninguna ofrece a la vez un target local compatible y un protocolo comparativo que pueda cambiar una decisión. Los cuatro registros permanecen bloqueados con condiciones concretas. No se tocó producción ni pesos.

## #26 — cartuchos numéricos CUT3
El post de r/LocalLLM enlaza repositorio, script y logs. `MAM_LOG1_QWEN_72B.log` informa una sesión Qwen2.5-72B sobre A100-80GB: 11/11 trials físicos, 17/17 engine checks, 8/8 verificaciones de append y pico reportado de 57,66 GiB. A la vez, el script público `MAM_full_QWEN_72B.py` aún dice “candidate v1.5 — NOT a published release” y “NOT executed on a GPU by its author (CPU simulation only)”. El registro presenta por tanto una contradicción interna de procedencia. Los logs separan integridad/mecánica física de semántica no puntuada como calidad general. Esto no demuestra una extensión nativa de contexto ni se transfiere a Qwen3.8 Flash-Next/MoE; no existe target local equivalente a Qwen2.5-72B/A100. Bloqueo actualizado: discrepancia de evidencia + modelo/runtime no compatible.

## #28 — migración Flutter→SwiftUI Qwen vs Opus
El enlace directo está accesible. El contenido sigue siendo un único relato: ~60 min local frente a ~50 min Opus, “pretty identical” con más pulido pendiente. No ofrece snapshot, diff, prompts íntegros, hashes, pruebas independientes ni rúbrica. No se llamó API ni se usó código productivo. Reabrir sólo con fixture sintético/autorizado, aceptación independiente y condiciones idénticas de harness, tiempo, permisos y gasto.

## #31 — DeepSeek V4.1 ROCm
El repo actual se identifica como Linux/ROCm/HIP para RX 7900 XTX `gfx1100`; la ficha declara 128 GiB RAM y ~570 GB de almacenamiento para modelos/tablas. No hay soporte CUDA/SM86 declarado, de modo que no aplica al host RTX 3090. Sin clone, download, build ni GPU. Reabrir sólo con port CUDA/SM86 explícito y comprobado y almacenamiento suficiente.

## #32 — Instagram
El intento de abrir el Reel vuelve a fallar (`Cache miss`). No hay caption, transcripción ni mirror atribuible; no se inventa un claim ni se diseña un test a partir de una promoción no verificable. Reabrir con evidencia primaria legible.

## Preflight de ejecución
Proceso de auditoría: Linux. Detección por nombre exacto y listeners de inferencia en puertos locales usuales: ninguno. No se lanzaron procesos, no se detuvo nada, no se usó GPU ni se descargaron artefactos.

## Efecto en la cola
El lote tiene 58 entradas guardadas; las #26/#28/#31/#32 continúan como bloqueadas con causa concreta. Qwen3.8 Flash-Next 1M ya tiene una prueba local registrada; Swift Flash-Next sigue pendiente de aclaración de licencia; C39 sigue pendiente de sesión Codex Windows nativa. No se marca el lote completo.
