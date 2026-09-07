# Pendiente: ExLlamaV3 para Qwen3.8 Flash-Next en Ubuntu

Estado: pendiente para una futura prueba. La descarga fue cancelada por el tamaño del quant y no se promovió ningún cambio.

## Qué se evaluó

- Repositorio de quant: `turboderp/Qwen3.8-Flash-Next-exl3`.
- Variante considerada: `4.05bpw_h6_ng6`.
- Tamaño publicado: aproximadamente 107 GB; incluye una tabla n-gram de varias decenas de GB.
- Backend preparado en un entorno aislado: TabbyAPI + ExLlamaV3 1.4.8 + PyTorch CUDA 12.8.
- Las dos RTX 3090 fueron detectadas correctamente por PyTorch.

## Resultado de esta sesión

La descarga llegó a aproximadamente 26 GB y fue cancelada antes de completar el modelo. Los archivos parciales fueron eliminados para recuperar espacio. No se inició TabbyAPI, no se midió TPS/BCB y no se creó ni modificó un perfil de LlamaCode.

Los perfiles ASTRA, SOL, TERRA, LUNA y METEOR quedan sin cambios; Windows tampoco fue alterado.

## Cómo retomarlo

1. Confirmar que haya al menos 120 GB libres en `/media/cristian/Disco local`.
2. Descargar nuevamente `4.05bpw_h6_ng6` en `Models/llamacpp/Qwen3.8-Flash-Next-exl3/`.
3. Arrancar TabbyAPI en loopback con ExLlamaV3 y comparar, en este orden:
   - sin drafter, CPU-offload de expertos, 196K, tabla n-gram en disco;
   - misma configuración con `ngram_ram`;
   - MTP/n-gram especulativo si la carga base es estable.
4. Medir carga, prefill, decode, contexto y BCB completo, además de tool-calling del harness.
5. Promoverlo sólo si supera a ASTRA en velocidad y mantiene la calidad/estabilidad requerida. La integración debe usar `platformBackendIds.linux`, conservando la ruta Windows original.

## Referencias

- ExLlamaV3: https://github.com/turboderp-org/exllamav3
- TabbyAPI: https://github.com/theroyallab/tabbyAPI
- Quant EXL3: https://huggingface.co/turboderp/Qwen3.8-Flash-Next-exl3/tree/4.05bpw_h6_ng6
