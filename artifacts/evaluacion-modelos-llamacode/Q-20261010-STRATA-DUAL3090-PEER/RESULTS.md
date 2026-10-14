# Resultados — Q-20261010-STRATA-DUAL3090-PEER

## Resultado

**Auditoría documental completa; perfil no aplicable al host en su estado actual.** No se descargaron modelos, no se compiló el fork y no se inició inferencia.

El autor describe Strata v0.1.38 más 29 commits, Qwen3.8-Flash-Next GSQ-RCO IQ3_S y dos RTX 3090 con puente NVLink. En `flashbench`, greedy y mediana de tres, reporta prefill 2.908/3.231/3.186 tok/s y decode 116/113/111 tok/s para prompts de 8K/32K/128K, a contexto 262K. Declara single-stream, y separa su rama peer de layer-split. La publicación y README no incluyen hashes del modelo ni recibos crudos reproducibles.

El tier de expertos `--peer-device` fue incorporado a Strata 0.1.38 como opción; el fork del post añade trabajo adicional de prefill y afinación específica. El peer puede usar NVLink u otra ruta CUDA P2P: por eso el obstáculo práctico local es que `nvidia-smi topo -m` marca PHB entre GPU0/GPU1, `nvidia-smi nvlink --status` dice que todos los enlaces están inactivos y `nvidia-smi topo -p2p p` devuelve NS en ambas direcciones. No hay ruta peer utilizable que permita reproducir esa configuración. GPU0 también tiene ArtCraft y el escritorio activos. No se tocó ningún proceso.

El issue y PR del proyecto upstream muestran que el mantenedor pidió que el peer tier fuera opt-in, mantuviera la salida predeterminada byte a byte y pasara una prueba de exactitud; también pidió incluir `--gpu1-experts` como baseline. El tier básico llegó a Strata 0.1.38; la división adicional de GDN/prompt del post sigue siendo trabajo específico de la rama del autor. Esto refuerza que el post mide un perfil particular, no “Strata dual GPU” en general.

## Decisión

- No añadir el fork peer a los perfiles locales ni modificar defaults.
- Mantener como evidencia local de dos GPU los perfiles Strata ya medidos, sin atribuir sus resultados a NVLink.
- Reabrir sólo si la pareja ofrece una ruta CUDA P2P utilizable y GPU0 queda libre; entonces fijar commit, hashes y comparación con stock, layer-split y `--gpu1-experts`. Aplicar al perfil la regla del usuario: la suite completa de tres semillas debe quedar dentro de 30 minutos para resultar interesante.

## Evidencia

- [Fuente comunitaria](https://www.reddit.com/r/LocalLLM/comments/1wytq4f/qwen38flashnext_dual_rtx_3090s_nvlink_3200_ts/)
- [README del fork](https://github.com/q8atnight/strata-dual-3090/blob/main/dual3090/README.md)
- [Discusión upstream de Strata](https://github.com/Niko1221/Strata/issues/204)
- [Recibo de revisión de fuentes](receipts/source-review.json)
- [Preflight local de topología y recursos](receipts/local-preflight.json)

## Clasificación

**Auditoría documental completa; benchmark local no aplicable con la topología actual.** No es una comparación de calidad de modelo ni una validación independiente de la velocidad publicada.
