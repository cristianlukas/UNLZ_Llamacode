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


## Q186 follow-up gate revalidation — 2026-10-29 12:46 UTC

Rechecked the primary Xolotl documentation and issue #2. The current docs still describe the measured DeepSeek route on one RTX 4090. The issue remains open; its latest relevant report (26 Oct) says that a 2×RTX 5060 Ti layer split could load after two guards but produced incorrect/corrupt simple answers (0/3), an empty answer and language drift. The author did not identify the cause. The separate 4×RTX 3090 report still describes a first-prompt segfault on its tested commit. These machines are not this host, but the reports do not establish a corrected runtime for our 2×RTX 3090.

Fresh `df` read: NVMe free is 267,269,193,728 bytes combined, 32,730,806,272 bytes below the 300 GB gate; HDD extra has 30,834,577,408 bytes and is excluded. No download, build, inference or GPU test was started. Q182 remains blocked on both storage and dual-runtime correctness; the latest source review did not enable its smoke test.


## Q187 storage recheck — 2026-10-29T13:06:52Z

Q187 verificó que el GGUF Qwen3.6-35B-A3B UD-Q4_K_XL de Q180 no está configurado en PeritoSoft, lo copió al HDD y comparó tamaño (22.853.663.008 B) y SHA-256 antes de retirar el original de D. Se liberaron 22,853,664,768 B en D. El espacio libre combinado de los dos NVMe ahora es **290,122,383,360 B**; todavía faltan **9,877,616,640 B** para el gate de 300.000.000.000 B. El HDD extra sigue excluido. Xolotl dual no está calificado; Q182 continúa bloqueado, sin descarga/build/inferencia/GPU. Evidencia: `artifacts/evaluacion-modelos-llamacode/Q-20261029-VF-ITERATION-187/receipts/archive.json` y la fila actualizada de Accionables.


## Revalidación Q188 — 2026-10-29

Q188, 2026-10-29: comprobación sin inferencia. `df -B1` da C: 121,910,718,464 B libres; D: 168,210,841,600 B; total de los dos volúmenes destinados a modelos 290,121,560,064 B. La partición raíz del mismo NVMe tiene 6,421,360,640 B libres, pero no se contó como volumen de modelos. HDD extra: 7,980,912,640 B, excluido para modelos rápidos. No se encontraron procesos/listeners llama-server, Xolotl, Strata o Project Maya ni CUDA compute apps; la GUI de PeritoSoft puede seguir abierta y no se trató como servidor. `nvidia-smi` mostraba ambas RTX 3090, sin app de cómputo registrada.

Revisión primaria actual: la documentación de Xolotl anuncia multi-GPU layer-split y dice que ISTA GSQ-RCO IQ2_XS carga/produce chat correcto en una RTX 4090; sus cifras principales son de una RTX 4090. El issue #2 documenta, en cambio, un segfault al primer prompt reproducido en 4×RTX 3090 aun en commit d4f65068; en 2×RTX 5060 Ti, dos guards dejaron al servidor responder 0/3 correctamente. Ninguna es una medición en nuestro host, pero no acredita que el split dual sea correcto. El gate Q182 de ≥300,000,000,000 B sigue sin alcanzarse en C+D: déficit 9,878,439,936 B. No se descargó, compiló, ni usó GPU.

Nueva ruta encontrada, separada de Q182 y del Reddit Delta/Q2: Project Maya v1.1.37 declara DeepSeek Maya-XS en cinco archivos GGUF por 276.6 GB, con drafter XS opcional de 4.3 GB; el modo sin visión evita un sidecar de 1.1 GB. Project Maya acepta uso de archivos locales (`--model-dir`), escribe el pack dentro de esa carpeta y permite seleccionar varias GPU. Con C+D libres actuales, Maya-XS sin drafter deja 13,521,560,064 B antes del pack; con el drafter deja 9,221,560,064 B. Es un margen estrecho para staging/build, no un gate de descarga aprobado todavía. El modelo, quant IQ1_S, runtime, cifras públicas y hardware son distintos del GGUF `nazeshinjite ds4 Q2` + Delta/Windows del post, y del ISTA/Xolotl de Q182. La prueba de Maya-XS 2×RTX 4090 publicada por el proyecto no se transfiere a estas 3090. Se abrirá Q189 con preregistro propio y un preflight de layout, build y espacio antes de descargar pesos.


## Revalidación de gates — 2026-11-02

df -B1 -P a 10,927,116,288 B libres en C y 87,414,194,176 B en D; C+D=98,341,310,464 B, déficit=201,658,689,536 B para el gate de 300,000,000,000 B. HDD extra tiene 264,550,998,016 B pero no cuenta como NVMe del gate. Revisión upstream del issue #2: el reporte del 26/10 en 2×RTX 5060 Ti PHB describe guards locales que quitan dos fallos, pero la salida dual resultó incorrecta 0/3, con una respuesta vacía y deriva a texto roto; `restore()` no fue verificado. Otro reporte en 4×RTX 3090 sigue mostrando SIGSEGV al primer prompt incluso en d4f65068. No hay fix dual upstream validado. La guía mantiene sus métricas principales en 1×RTX 4090. No descargar/compilar hasta que C+D tenga ≥300,000,000,000 B libres y exista un fix Xolotl dual upstream con smoke funcional en PHB/Ampere comparable, con commit y artefactos exactos. El reporte 2×5060 Ti evitó crashes con guards locales pero tuvo 0/3 salidas correctas y no validó restore; el reporte 4×3090 aún segfaultea. Sin inferencia ni GPU en este host. Q182 sigue bloqueado por storage y runtime: hay 201,658,689,536 B menos que el gate NVMe; la evidencia dual disponible contiene salidas incorrectas y SIGSEGV. No inferir ni borrar/cambiar otros perfiles. Reabrir sólo con NVMe suficiente y fix upstream validado con salidas correctas en arquitectura PCIe/PHB comparable. Accionables de Sheets, fila 49 (`D49:K49`, `M49:N49`), actualizado y leído de vuelta; WRAP preservado. No hubo prueba, descarga, build ni uso de GPU. Recibo `artifacts/evaluacion-modelos-llamacode/Q-20261102-VF-RESUME-191/receipts/q182-xolotl-gate-revalidation-20261102.json`.


## Reauditoría Q192 de tests abiertos — 2026-11-02T01:59:57Z

- La pestaña `Modelos locales por peso` tiene 21 perfiles LLM/VLM no retirados; ninguno carece de Prefill, Decode o Q172. Los 19 registros LLM/VLM con una o más métricas vacías están marcados `Retirado`, así que no son candidatos locales para otro benchmark.
- `df -B1 -P`: C NVMe 10,922,586,112 B libres; D NVMe 87,414,194,176 B; total 98,336,780,288 B. Gate Q182: 300,000,000,000 B; faltan 201,663,219,712 B. El HDD extra (264,550,998,016 B libres) no satisface el gate NVMe.
- Preflight no halló proceso/puerto de inferencia ni CUDA compute app. GPU0: 820/24576 MiB, 9%; GPU1: 108/24576 MiB, 41%. No se lanzó test, descarga, build ni servidor.
- Revisión primaria actual del issue [#2](https://github.com/Indras-Mirror/Xolotl/issues/2): sigue abierto y sin PR/branch; el último reporte relevante es del 26-10. Los guards locales comunicados para 2×5060 Ti PHB dejan el split en 0/3 respuestas correctas y no ejercitan restore; el caso 4×3090 sigue fallando con SIGSEGV al primer prompt en d4f65068. La guía [DeepSeek V4.1](https://github.com/Indras-Mirror/Xolotl/blob/main/docs/DEEPSEEK_V41.md) mantiene resultados principales en una RTX 4090. Q182 no pasa ninguno de los dos prerequisitos: storage suficiente y split dual correcto.
- El inventario activo no aporta otro test P/D/Q172 habilitado; los accionables restantes siguen sujetos a gates externos definidos en la cola. No se cambia ASTRA, SOL ni PeritoSoft. Receipt: `artifacts/evaluacion-modelos-llamacode/Q-20261102-VF-RESUME-192/receipts/pending-ai-tests-gate-audit-20261102.json`.
