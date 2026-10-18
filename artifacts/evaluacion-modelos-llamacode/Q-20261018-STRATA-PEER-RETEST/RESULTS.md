# Resultados — Q-20261018-STRATA-PEER-RETEST

## Estado

**Bloqueado por infraestructura; no se ejecutó inferencia ni benchmark.** Se completó un preflight nuevo, de sólo lectura, y se revisaron las fuentes primarias vinculadas al post y a sus alternativas.

## Qué se comprobó

- Dos RTX 3090, driver 610.57.04. Conexión GPU0–GPU1 `PHB`; NVLink aparece inactivo en ambas tarjetas.
- `nvidia-smi topo -p2p p` devuelve `NS`; las capacidades P2P read/write devuelven `GNS` en ambos sentidos. No hay ruta CUDA P2P usable.
- GPU1 está siendo usada por Xorg, Compiz y el navegador/escritorio (18% de utilización en la muestra). No se detuvo ningún proceso. RAM disponible 115 GiB; swap configurada 8 GiB, sin uso; PSI de memoria avg10 0.
- La documentación fijada de Strata 0.1.41 coincide con el runtime local: `--peer-device` requiere transferencias NVLink u otra ruta P2P. La rama `main` upstream más nueva describe un fallback por memoria host, pero cambiar a esa rama sería otra prueba y otro fingerprint; no la compilé.
- La alternativa `DominikBucko/qwen38-flash-next-2x3090` es otro runtime/quant/checkpoint (W4A16/FP8-PLE), no el IQ3_S del post; su perfil rápido pide P2P bidireccional y al menos 32 GiB de swap, frente a 8 GiB configurados aquí.

## Pruebas solicitadas y estado

| Prueba | Estado | Motivo |
|---|---|---|
| Preflight hardware/topología/procesos | Ejecutado | Recibo: `receipts/local-preflight.json`. |
| Gate de exactitud del fork | No ejecutado | Requiere la ruta peer y los artefactos fijados; no hay NVLink/P2P y GPU1 está ocupada. |
| `flashbench` A/B contra Strata local | No ejecutado | El perfil publicado es NVLink-específico; ejecutar sobre topología distinta no probaría la afirmación. No hay hashes crudos del post ni se fijaron artefactos del fork. |
| Calidad coding/agentes, Computer Usage, visión, contexto/audio | No evaluado en esta campaña | El post no aporta harness/resultados para esas modalidades y no se cargó un modelo. |
| Cambio de perfil/HarnessSpec o promoción | Ninguno | Sin prueba comparable ni evidencia local de mejora. |

No se descargaron modelos, no se compiló el fork, no se iniciaron servicios ni se generó fingerprint de inferencia.

## Decisión

Mantener los perfiles actuales. No se confirma una mejora transferible a LlamaCode: la velocidad del post no es reproducible en el host actual y no aporta evidencia de calidad de agente. La decisión previa de no agregar `--peer-device` permanece, ahora con un preflight nuevo que confirma el mismo bloqueo.

**Para reanudar la prueba original:** disponer de NVLink activo entre las dos tarjetas; además, dejar GPU1 libre del navegador/escritorio; fijar el commit del fork y los hashes exactos del modelo/runtime antes de compilar. Sólo entonces ejecutar primero el gate de exactitud y luego el A/B preregistrado de tres semillas dentro del corte de 30 minutos por perfil. Si se quiere evaluar el fallback por memoria host de upstream `main`, tratarlo como experimento aparte, con runtime y huella nuevos, y no atribuirlo al post de NVLink.

## Fuentes y recibos

- [Post y discusión provistos por el usuario](https://www.reddit.com/r/LocalLLM/comments/1wytq4f/qwen38flashnext_dual_rtx_3090s_nvlink_3200_ts/)
- [Strata 0.1.41: second GPU](https://github.com/Niko1221/Strata/blob/v0.1.41/docs/SECOND_GPU.md)
- [Strata v0.1.41 release](https://github.com/Niko1221/Strata/releases/tag/v0.1.41)
- [Strata upstream main: second GPU](https://github.com/Niko1221/Strata/blob/main/docs/SECOND_GPU.md)
- [Fork original del post](https://github.com/q8atnight/strata-dual-3090)
- [Fork alternativo 2×3090 de los comentarios](https://github.com/DominikBucko/qwen38-flash-next-2x3090)
- [Preflight local](receipts/local-preflight.json)
- [Revisión de fuentes](receipts/source-review.json)
