# Q183 · Resultados de reconciliación documental

Fecha: 2026-10-29 · Estado: completado. No se ejecutaron benchmarks, inferencia, builds ni uso de GPU; los pendientes relevantes siguen bloqueados por condiciones externas concretas.

## Cambios realizados

- Harness² dejó de figurar como prueba completada. Q181 se conserva como evidencia relacionada: tres tareas, tres pasadas intercaladas, ASTRA Flash-Next RCO IQ2_XS/Strata en 2×RTX 3090. Básico aprobó 3/3 pasadas (11/11 cada una); Intermedio 2/3 y falló `test_negative_and_signed_tokens` (esperado -3, obtenido -43). Medianas E2E: 76,726 s frente a 86,613 s; reparaciones: 0 frente a 1. Esto no demuestra que Harness², como integración separada, se haya ejecutado.
- Se consolidaron las fuentes VF-20261019 #20, #21 y #24 bajo el experimento preregistrado `VF-20261019-01-S20-ROUTE-AB`. Sigue bloqueado antes de cualquier llamada externa: faltan proveedor/modelo y versión efectivos, `keyRef`, límite de gasto y frontera de datos/egress. Se anotó la declaración del usuario de uso no comercial, open source y donado a UNLZ; no se interpretó como autorización de egress ni configuración de credenciales.
- Se agregó el gate de compatibilidad NInfer-3090 Flash-Next Linux dual. La documentación revisada anuncia el preview Flash-Next en Windows/una RTX 3090; no se localizó calificación de Flash-Next en Linux dual/TP2. No se descargó ni se midió nada.
- El inbox VF-20261019-01 conserva 70 entradas. `actionables.json` queda con 40 entradas, incluyendo Q182; se actualizaron respaldos antes de la edición.
- Google Sheets `Accionables`: se corrigió la fila 35 y se agregaron S20 en fila 50 y el gate NInfer en fila 54. Filas existentes Q182 (49), Q176 (52) y Q180 (53) se conservaron. Lectura posterior confirmó los valores y formato Arial 10, ajuste WRAP y alineación TOP.

## Pendientes AI y gates para reanudar

- **A/B híbrido S20:** configurar proveedor/modelo+versión, `keyRef`, gasto máximo y política/frontera de datos; después usar únicamente mini-repos sintéticos ya preregistrados.
- **Harness²:** fijar integración y commit exactos, endpoint local, copia desechable, holdout no público, secretos falsos y bloqueo de egress a nivel de host.
- **NInfer Flash-Next Linux dual:** soporte upstream explícito del modelo en Linux dual/TP2, con release/commit/artifact exactos; empezar por smoke de carga/API.
- **Xolotl/ISTA IQ2_XS (Q182):** liberar ≥300 GB de NVMe rápido y disponer de un runtime dual corregido; el espacio auditado era 267,3 GB frente a ≈274 GB de componentes antes de margen.
- Otros ítems que ya fallaron gates o no tienen una diferencia de configuración/fingerprint que cambie una decisión no se repitieron. Los candidatos que dependen de Windows siguen bloqueados por host.

## Integridad y límites

No se cambiaron los perfiles productivos ASTRA/SOL ni PeritoSoft. No se ejecutó prueba de modelo en esta iteración; el trabajo fue reconciliación de estados y verificación del Sheet. Evidencia estructurada en `receipts/`.
