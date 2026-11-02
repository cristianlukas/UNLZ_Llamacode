# Q182 — Resultado de revisión de gates

**Estado:** revisión cerrada; candidato Linux registrado como pendiente condicionado. **No se descargó, compiló ni ejecutó modelo alguno.**

## Hallazgos

- La sesión no encontró un inference server activo ni procesos CUDA de cómputo. El usuario confirmó que detuvo el servidor Qwen3.5-9B.
- No se repitió Q172: Q179 ya completó el perfil Flash-Next/NInfer-all dual con 80/100 (45/56) y una fuga cross-tenant en TC-92. El gate de seguridad falla.
- El DeepSeek T16 de Q172 es otro archivo y runtime que el modelo `nazeshinjite ds4 Q2` del post. Su score 89/100 (una semilla) frente a ASTRA 73/100 también quedó bloqueado por la fuga de TC-92; no se midieron los 41 tok/s del post.
- Se encontró una alternativa Linux actual: Xolotl documenta ISTA-DASLab GSQ-RCO IQ2_XS. Sus pesos, Engram y drafter requieren cerca de 274 GB. Los dos NVMe disponen juntos de 267,3 GB y el HDD extra no satisface el requisito de almacenamiento rápido. La instancia local ya tuvo un SIGSEGV de Xolotl dual antes del primer token, y el issue público sigue mostrando fallos de corrección/estabilidad multi-GPU.

## Decisión

No hay una nueva inferencia habilitada ahora. El siguiente test queda condicionado a **300 GB libres en NVMe** y una versión/configuración dual que pase el smoke de 3/3 oracles en estas dos RTX 3090. Mantener Qwen Flash-Next ASTRA, SOL y el resto de perfiles productivos intactos. No atribuir al quant ISTA IQ2_XS el rendimiento publicado del `nazeshinjite ds4 Q2`.

## Evidencia

- Q172 DeepSeek local: `artifacts/evaluacion-modelos-llamacode/Q-20261027-VF-ITERATION-172/RESULTS.md`.
- Q179 Flash-Next dual: `artifacts/evaluacion-modelos-llamacode/Q-20261028-VF-ITERATION-179/RESULTS.md`.
- Fallo de Xolotl dual local: fila histórica `IA local!A73:O73` y recibos Q172.
- Revisión y sincronización: `receipts/evidence-review.json`, `receipts/google-sheet-q182-sync.json`.

## Sincronización de la cola y el Sheet

- Se agregó el candidato como material #70 en `data/inbox.json`, con estado bloqueado y condiciones concretas; se corrigió en #69 una instrucción vieja que pedía detener servidores globalmente y repetir Q180, que ya está completo.
- `IA local!E75/I75/L75` ahora refleja el resultado final de DSX T16. Se añadió el registro ISTA/Xolotl en `IA local!A77:O77` y el accionable bloqueado en `Accionables!A49:N49`.
- Readback confirma valores, enlace a la documentación de Xolotl y formato Arial 10, WRAP y TOP. Detalle en `receipts/google-sheet-q182-sync.json`.

## Q187 storage recheck — 2026-10-29T13:06:52Z

Q187 verificó que el GGUF Qwen3.6-35B-A3B UD-Q4_K_XL de Q180 no está configurado en PeritoSoft, lo copió al HDD y comparó tamaño (22.853.663.008 B) y SHA-256 antes de retirar el original de D. Se liberaron 22,853,664,768 B en D. El espacio libre combinado de los dos NVMe ahora es **290,122,383,360 B**; todavía faltan **9,877,616,640 B** para el gate de 300.000.000.000 B. El HDD extra sigue excluido. Xolotl dual no está calificado; Q182 continúa bloqueado, sin descarga/build/inferencia/GPU. Evidencia: `artifacts/evaluacion-modelos-llamacode/Q-20261029-VF-ITERATION-187/receipts/archive.json` y la fila actualizada de Accionables.

## Revalidación de gates — 2026-11-02

df -B1 -P a 10,927,116,288 B libres en C y 87,414,194,176 B en D; C+D=98,341,310,464 B, déficit=201,658,689,536 B para el gate de 300,000,000,000 B. HDD extra tiene 264,550,998,016 B pero no cuenta como NVMe del gate. Revisión upstream del issue #2: el reporte del 26/10 en 2×RTX 5060 Ti PHB describe guards locales que quitan dos fallos, pero la salida dual resultó incorrecta 0/3, con una respuesta vacía y deriva a texto roto; `restore()` no fue verificado. Otro reporte en 4×RTX 3090 sigue mostrando SIGSEGV al primer prompt incluso en d4f65068. No hay fix dual upstream validado. La guía mantiene sus métricas principales en 1×RTX 4090. No descargar/compilar hasta que C+D tenga ≥300,000,000,000 B libres y exista un fix Xolotl dual upstream con smoke funcional en PHB/Ampere comparable, con commit y artefactos exactos. El reporte 2×5060 Ti evitó crashes con guards locales pero tuvo 0/3 salidas correctas y no validó restore; el reporte 4×3090 aún segfaultea. Sin inferencia ni GPU en este host. Q182 sigue bloqueado por storage y runtime: hay 201,658,689,536 B menos que el gate NVMe; la evidencia dual disponible contiene salidas incorrectas y SIGSEGV. No inferir ni borrar/cambiar otros perfiles. Reabrir sólo con NVMe suficiente y fix upstream validado con salidas correctas en arquitectura PCIe/PHB comparable. Accionables de Sheets, fila 49 (`D49:K49`, `M49:N49`), actualizado y leído de vuelta; WRAP preservado. No hubo prueba, descarga, build ni uso de GPU. Recibo `artifacts/evaluacion-modelos-llamacode/Q-20261102-VF-RESUME-191/receipts/q182-xolotl-gate-revalidation-20261102.json`.
