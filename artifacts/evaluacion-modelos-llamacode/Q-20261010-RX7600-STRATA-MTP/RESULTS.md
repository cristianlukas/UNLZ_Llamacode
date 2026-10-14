# Evaluación del post RX 7600 / Strata gfx1102 / Qwen3.6 MTP

- **ID:** `Q-20261010-RX7600-STRATA-MTP`
- **Cierre:** 2026-10-13; auditoría documental completada. No se lanzó inferencia ni se descargaron modelos.
- **Decisión:** conservar perfiles y HarnessSpec; no promover cambios. La señal MTP es de velocidad y no mide calidad de coding/agentes.

## Qué afirma la publicación

El post separa dos pruebas. Para Qwen3.8-Flash-Next IQ2_XS en Strata 0.1.39 y RX 7600 8 GB/gfx1102 informa 24 tok/s de decode y 59,1 tok/s de prompt. Para Qwen3.6-35B-A3B Q6_K_XL en llama.cpp, informa 151 tok/s de prefill a 4K, 23,6 tok/s de decode sin MTP y 32,0 con `draft-mtp` de dos tokens, con aceptación de drafts del 98%. El autor describe respuestas greedy cortas de 320 tokens; son cifras publicadas por el autor, no una medición independiente ni una prueba de calidad.

La tabla del post y la discusión del PR #1000 difieren sobre el prefill con la tabla hipBLASLt: el PR reporta 59,1 tok/s sin tabla y 67,5 con tabla (+14%), mientras la tabla del post muestra 59,1 bajo el encabezado de la configuración con tabla. Se conserva la discrepancia; no se elige una lectura como cifra confirmada.

El post no ejecuta Qwen3.6 en Strata. El caso RX 7600 con Strata usa Qwen3.8 IQ2_XS; el caso Qwen3.6 usa llama.cpp. Son modelos, motores y pruebas distintos.

## Estado de compatibilidad upstream

- El PR [#1000](https://github.com/Niko1221/Strata/pull/1000) documenta una corrida comunitaria de Strata 0.1.39 en RX 7600 8 GB, IQ2_XS, `strata-device --selftest` aprobado y ctest 62/63 (la prueba restante requería AVX-512). El PR fue cerrado automáticamente después de un force-push de `main`, según el mantenedor; no se describe como rechazo. La tabla hipBLASLt también aparece en la discusión del PR.
- La documentación actual de Strata para AMD sí registra una corrida comunitaria distinta en RX 7600 XT de 16 GB con Qwen3.8/Swift IQ3_XXS; marca gfx1102 como compilable con advertencia y describe esa tarjeta de 16 GB, no reproduce el equipo RX 7600 de 8 GB del post. Ver [AMD_HIP.md](https://github.com/Niko1221/Strata/blob/main/docs/AMD_HIP.md) y [issue #942](https://github.com/Niko1221/Strata/issues/942).
- La compatibilidad de Qwen3.6 con Strata es trabajo aparte: el antiguo [PR #824](https://github.com/Niko1221/Strata/pull/824) proponía un engine separado y también se cerró tras el force-push; su prueba real en Tesla P40 fue una respuesta Q4_K_M con MTP apagado, sin verificación de calidad. El [PR #1402](https://github.com/Niko1221/Strata/pull/1402) sigue abierto y propone integrar Qwen3.6/Ornith al engine principal, incluyendo MTP. Eso no significa que la publicación haya usado Strata para Qwen3.6 ni que el cambio esté en `main`.
- La ficha oficial de [Qwen3.6-35B-A3B](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) documenta el uso de MTP para SGLang y vLLM. El server de [llama.cpp](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md) documenta `draft-mtp` como tipo de speculative decoding; ninguno de esos documentos valida por sí mismo los tok/s del post.

## Preflight local y evidencia ya existente

| Elemento | Observación local | Implicación |
|---|---|---|
| GPU visible | 2× NVIDIA RTX 3090; `lspci` también lista un dispositivo AMD `1002:13c0`, sin identificarlo como RX 7600. `rocminfo` no produjo inventario de arquitectura. | No se puede reproducir el caso RX 7600/gfx1102 ni atribuirle sus cifras. No se usó GPU en esta tarea. |
| GGUF Q6_K_XL del post | No apareció en el inventario de `Models` examinado. La ruta histórica `Models/llamacpp/Qwen3.6-35B-A3B-MTP` ya no existe. | Falta el artefacto exacto para el A/B publicado; no se descargó. |
| Qwen3.6 local | Sí existe el directorio AutoRound INT4 de safetensors en `Models/llamacpp/club-3090/qwen3.6-35b-a3b-autoround-int4`. La auditoría NInfer del 18 de septiembre registra el artefacto y el par MTP, pero ese archivo ya no está en la ruta histórica revisada. | Son perfiles/formatos diferentes al GGUF Q6_K_XL con llama.cpp. No se mezclan como réplica ni se afirma que el NInfer siga instalado. |
| llama.cpp | El checkout `llama-mtp` revisado está en commit `267f8afe857b7bd1a49e4fde9138ab0f7be36625` y contiene `llama-server.exe` PE de Windows; no es un binario Linux para esta medición. | No hay un runtime Linux del post fijado en ese checkout; junto con la ausencia del GGUF exacto, no se armó un A/B nuevo. |
| Medición MTP local previa | Auditoría NInfer del mismo modelo base Qwen3.6-35B-A3B: 4K, una RTX 3090, MTP3 190,08 tok/s frente a 159,66 tok/s sin MTP; diferencia descriptiva +19,05%. Artefacto `.ninfer` SHA-256 `9e8378398d2b789a77224b5110c7590adbbc6fd4accd139b918157b2b9da7163`. | Evidencia histórica de que MTP aceleró ese perfil local. Cambian runtime, formato/precisión, GPU y número de drafts; no es comparable directamente con 32,0 vs 23,6 tok/s del post ni prueba calidad. Ver [auditoría NInfer](../../../docs/ninfer-qwen35-3090-concurrency-vision-audit-20260918.md). |

El resultado local histórico equivale a +30,42 tok/s (+19,05%) para su perfil NInfer, pero no se repitió aquí: el fingerprint ya tiene una medición apareada y no se encontró un control nuevo que justificara repetirla. El perfil QWEN35-A3B/vLLM y los resultados de NInfer son evidencia contextual, no brazo de control de llama.cpp.

## Alcance, conclusión y condición para reabrir

Esta tarea fue documental. No se midieron calidad, coding/agente, herramienta ejecutada, Computer Usage, visión, audio, contexto efectivo ni throughput nuevo. No se cambió perfil, modelo, HarnessSpec ni default. SOL no intervino y no se descargó ningún modelo.

Para repetir exactamente la señal del post hacen falta una Radeon RX 7600 8 GB/gfx1102 disponible, el GGUF Qwen3.6-35B-A3B Q6_K_XL con su MTP, y una build Linux de llama.cpp fijada. Con esos componentes se puede medir primero velocidad con y sin MTP en el mismo perfil; la calidad de agente requiere luego un A/B separado con verificadores independientes y al menos tres pares válidos. Un benchmark en las RTX 3090 con un artefacto distinto sería una evaluación de perfil completo diferente.

## Fuentes

- [Publicación original r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1wynz8o/rx_7600_8_gb_on_linux_qwen38flashnext_125b_at_24/)
- [PR Strata #1000: gfx1102/RX 7600](https://github.com/Niko1221/Strata/pull/1000)
- [Strata issue #942: RX 7600 XT 16 GB](https://github.com/Niko1221/Strata/issues/942)
- [PR Strata #824: engine Qwen3.6 separado](https://github.com/Niko1221/Strata/pull/824)
- [PR Strata #1402: Qwen3.6 en el engine principal](https://github.com/Niko1221/Strata/pull/1402)
- [Model card oficial Qwen3.6-35B-A3B](https://huggingface.co/Qwen/Qwen3.6-35B-A3B)
- [Opciones MTP del server llama.cpp](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
