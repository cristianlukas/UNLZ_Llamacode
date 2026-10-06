# Recorte local de Qwen3.8-27B — 2026-10-06

Se retiraron únicamente artefactos del disco D con el lock de la tarea **Q-20261006-ASTRA-SOL-COMPLEX** activo. No se tocó el SOL AutoRound, AP-Q3 válido ni Swift Flash-Next.

- **UD-Q3_K_XL**: retirado junto con su caché de descarga incompleta (~5,1 GB). AP-Q3 tiene PPL menor en mixedweb (11,0283 vs 11,0631) y Wiki del proyecto (6,0887 vs 6,1278), con velocidad prácticamente igual; no hay evidencia de que UD-Q3 mejore a SOL en el harness.
- **UD-Q6_K_XL + MTP**: retirado (~26,7 GB). Medición histórica 65,1/45,3 tok/s y BCB8 directo 1/8; SOL tiene 102 tok/s en coding y BCB8 LC-H1 8/8. La receta no fue una A/B idéntica, por lo que la decisión es por espacio/flujo operativo, no por una afirmación absoluta sobre capacidad del modelo.
- **AP-Q3_K_XL.sha256-mismatch**: retirado (~13,1 GB); tenía el mismo tamaño que el AP válido pero hash distinto. AP válido coincide con el hash registrado del benchmark.

**Se conserva AP-Q3 válido** (~13,1 GB + mmproj): mejor fidelidad PPL local que UD-Q3, y todavía sin comparación agentiva directa contra SOL. No hay evidencia suficiente para clasificarlo como peor que SOL.

**Flash-Next**: Swift era el único checkpoint retenido; ASTRA IQ3_S calibrado se está re-descargando para el A/B complejo solicitado. Los otros Flash-Next/Strata ya estaban retirados por la decisión previa de conservar uno; sus resultados incompletos no prueban inferioridad global.

Los hashes, rutas, bytes retirados y `df` antes/después están en [`cleanup-receipt.json`](cleanup-receipt.json).


## Re-descarga de ASTRA y comparación — 2026-10-06

ASTRA IQ3_S calibrado volvió a D en `/media/cristian/Disco local/Models/ASTRA-IQ3_S-calibrated-20261006` (93.000.847.852 B, 56 archivos). A/B TaskFlow ULTRA: una pareja válida, ASTRA 12/13 en 177,390 s y SOL 11/13 en 589,364 s; ambos fallan undo/complete. ASTRA disparó el guard pre-tool en dos intentos extra, excluidos como infraestructura. No es base suficiente para llamar a Swift u otros checkpoints inferiores globalmente; ver `../qwen38-astra-sol-complex-20261006/report.md`. D conserva ahora 276,875 GiB libres.
