# Continuación de pruebas pendientes — Strata UD-IQ4_XS

- **ID:** `Q-20261019-STRATA-UDIQ4XS-REMAINING`
- **Estado:** completa como screening parcial; sin promoción.
- **Solicitud:** el usuario pidió ejecutar las pruebas que quedaron pendientes. Se entiende que esta instrucción amplía el screening del 2026-10-18 para intentar completar la escalera restante.
- **Candidato y runtime:** Qwen3.8-Flash-Next Unsloth UD-IQ4_XS ya instalado en el HDD dedicado; Strata 0.1.41. Reutilizar el runtime aislado y los fingerprints del screening del 2026-10-18. Revalidar hashes y configuración antes de reanudar.
- **Evidencia previa que se conserva:** API `READY`, tres solicitudes sintéticas HTTP 200 con mediana de 56,7 tok/s decode y HumanEval/0 aceptado 1/1 con revalidación independiente de su código/tests. Estos resultados son screening, no una promoción.
- **Cobertura pendiente solicitada:** HumanEval/20, después BCB8 y TaskFlow ULTRA; detenerse ante fallos de infraestructura o guards del harness y registrar resultados parciales sin convertirlos en scores válidos. No repetir HE0 ni el speed screen salvo que la revalidación de runtime indique que hace falta.
- **Fuera de la escalera local actual:** Computer Usage, visión, audio y retrieval poblado requieren fixtures/campañas independientes; el post y el runtime fijado no aportan una ruta E2E de visión/audio. No inferir resultados para esas modalidades.
- **Criterio de inicio:** GPU0 debe permanecer ociosa durante 60 s de observación, sin inferencia de terceros; puertos 18354/8354/8350 libres; hashes/runtime/perfil confirmados. No detener procesos ajenos.
- **Preflight 2026-10-19:** GPU0 fluctuó 9–67% y GPU1 16–52% en dos ventanas breves; el último snapshot marcó 33%/22%. `nvidia-smi` no enumeró procesos compute. Como las GPU no estaban ociosas, no se reservó ninguna ni se arrancó servidor. MemAvailable 122.283.760 KiB; swap libre 8 GiB; HDD libre 236.197.289.984 bytes; shards y MTP ya están en el destino dedicado; puertos consultados libres.
- **Próximo paso exacto (histórico):** reanudar bajo lock propio después de que el usuario aclarara que la actividad GPU0/GPU1 era de sus monitores y autorizara usar GPU0. GPU1 se reservó sólo para monitores.

## Cierre bajo autorización explícita — 2026-10-20 UTC

- Lock utilizado y liberado tras guardar resultados e informe: `1eb051fa-9d06-4c42-81d3-c1683249cc6d` (`Q-20261019-STRATA-UDIQ4XS-REMAINING`).
- Perfil/runtime: `q14-udiq4xs-he0`, fingerprint `185d554a488e661980a6500e64b2752fc86a863c5d666eb570a2d7c0db0bdc47`; HarnessSpec `sha256:cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef`; `agent-maximo`, seed 4242, temperatura 0.1; Strata 0.1.41, contexto 32768, KV int8, MTP spec4, inferencia sólo GPU0. GPU1 quedó para los monitores del usuario.
- HE20 completado válidamente 20/20, 4705.197 s, sin timeout ni reparaciones.
- BCB8: intento 1 con timeout de 1800 s y probe parcial 3/8; intento 2 con timeout duro de 7200 s y JSON `invalid=true`/`timedOut=true`/0 de 0, tras superar 7200 s. No hay score válido; no repetir el mismo fingerprint en esta campaña.
- ADV v1: suite `intelligence_adversarial_v1`, SHA-256 `e5888f337ac279a0b3bf9de569054781b043d6c3086f5446dbaefbf1f1b285d5`. Se canceló tras 989.237 s, atascada en el primer caso `ttl_cache_clock`; no existe EVAL final.
- TaskFlow ULTRA: suite `qwen38_taskflow_ultra_ast_vs_sol_20261006`, SHA-256 `f04febb440208d5bf74c01e84d78f5127e57c164fabece2acbfb346215dc0c17`. Primer pase: 6/10 archivos exactos, cuatro ausentes, fallo de `py_compile` y `unittest` sin tests. El estado siguió activo al superar el corte operativo de 1800 s; cancelado por API local a los 2117.136 s. Sin JSON EVAL final y sin score final.
- Resultado general: una suite válida (HE20); BCB8 dos veces incompleto por timeout; ADV y TaskFlow sin resultado final. No se promovió el modelo ni se modificó código/producto. No correspondían build ni tests C++/QML/core. No se lanzó otra campaña del repo en paralelo.
- La cola del repositorio es manual. Después de cancelar TaskFlow, la API local informó benchmark detenido y `agentQueuedCount=0`. Los resultados, metadatos, definiciones de suite y eventos están preservados en [recibos con hashes](receipts/runs/README.md); los workspaces completos continúan en el runtime de la campaña previa enlazado desde `RESULTS.md`.
