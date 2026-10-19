# Continuación de pruebas pendientes — Strata UD-IQ4_XS

- **ID:** `Q-20261019-STRATA-UDIQ4XS-REMAINING`
- **Estado:** bloqueada antes de inferencia por actividad sostenida en ambas GPU.
- **Solicitud:** el usuario pidió ejecutar las pruebas que quedaron pendientes. Se entiende que esta instrucción amplía el screening del 2026-10-18 para intentar completar la escalera restante.
- **Candidato y runtime:** Qwen3.8-Flash-Next Unsloth UD-IQ4_XS ya instalado en el HDD dedicado; Strata 0.1.41. Reutilizar el runtime aislado y los fingerprints del screening del 2026-10-18. Revalidar hashes y configuración antes de reanudar.
- **Evidencia previa que se conserva:** API `READY`, tres solicitudes sintéticas HTTP 200 con mediana de 56,7 tok/s decode y HumanEval/0 aceptado 1/1 con revalidación independiente de su código/tests. Estos resultados son screening, no una promoción.
- **Cobertura pendiente solicitada:** HumanEval/20, después BCB8 y TaskFlow ULTRA; detenerse ante fallos de infraestructura o guards del harness y registrar resultados parciales sin convertirlos en scores válidos. No repetir HE0 ni el speed screen salvo que la revalidación de runtime indique que hace falta.
- **Fuera de la escalera local actual:** Computer Usage, visión, audio y retrieval poblado requieren fixtures/campañas independientes; el post y el runtime fijado no aportan una ruta E2E de visión/audio. No inferir resultados para esas modalidades.
- **Criterio de inicio:** GPU0 debe permanecer ociosa durante 60 s de observación, sin inferencia de terceros; puertos 18354/8354/8350 libres; hashes/runtime/perfil confirmados. No detener procesos ajenos.
- **Preflight 2026-10-19:** GPU0 fluctuó 9–67% y GPU1 16–52% en dos ventanas breves; el último snapshot marcó 33%/22%. `nvidia-smi` no enumeró procesos compute. Como las GPU no estaban ociosas, no se reservó ninguna ni se arrancó servidor. MemAvailable 122.283.760 KiB; swap libre 8 GiB; HDD libre 236.197.289.984 bytes; shards y MTP ya están en el destino dedicado; puertos consultados libres.
- **Próximo paso exacto:** cuando GPU0 quede ociosa durante 60 s y siga libre el endpoint, adquirir un lock nuevo, verificar los tres hashes contra el recibo del 2026-10-18 y ejecutar HE20 → BCB8 → TaskFlow ULTRA de forma serial. No usar GPU1 sin preflight separado.
