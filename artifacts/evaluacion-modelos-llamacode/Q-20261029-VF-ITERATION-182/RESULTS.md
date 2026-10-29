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
