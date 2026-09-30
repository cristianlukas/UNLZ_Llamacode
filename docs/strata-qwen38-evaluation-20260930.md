# Evaluación de Strata para Qwen3.8-Flash-Next

Fecha de revisión: 2026-09-30. Esta nota registra la investigación y evita
repetir la corrida Q2_0 ya hecha el 2026-09-29.

## Decisión

**No promover Strata ni cambiar perfiles/harness con la evidencia actual.** El
resultado anterior muestra una mejora grande de velocidad, pero sólo 1/8 en
BigCodeBench-Hard. La nueva variante Coder de Strata es otra candidata y no se
considera validada por ese resultado: necesita su propia corrida con el mismo
paquete de coding y una evaluación de herramientas antes de compararla con los
perfiles del proyecto.

## Fuentes y cambios del upstream

- El README y `setup.py` actuales de Strata describen Qwen3.8-Flash-Next, Swift
  1.5 y una variante **Coder** de ISTA-DASLab. El Coder retiene 256 de los 512
  expertos por capa, está orientado a código, herramientas e imágenes, y usa el
  tamaño IQ1_M (aprox. 58,4 GB de descarga). La versión actual también ofrece
  reparto de capas entre varias GPU. Estos son datos del proyecto upstream, no
  resultados de LlamaCode.
- El setup actual admite NVIDIA y AMD experimental; esta notebook tiene dos RTX
  3090 de 24 GB, driver 610.57.04 y 124 GB RAM. La CPU compila el engine CUDA
  para SM86 si no hay un release prebuilt utilizable.
- Strata documenta que el redondeo de la caché de expertos en GPU puede cambiar
  levemente las respuestas frente a una corrida sin esa caché. No se debe
  afirmar equivalencia token por token sólo a partir de igualdad de parámetros.

Referencias consultadas: [repositorio y guía de Strata](https://github.com/Niko1221/Strata),
[detalles técnicos de Strata](https://github.com/Niko1221/Strata/blob/main/docs/DETAILS.md),
[GGUF GSQ-RCO de Qwen3.8-Flash-Next](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF).

## Prueba ya realizada: Q2_0, 2026-09-29

No volver a ejecutar esta misma matriz para confirmar el resultado:

| Elemento | Configuración / resultado |
|---|---|
| Modelo | Qwen3.8-Flash-Next GSQ-RCO Q2_0, engine Strata 0.1.20 |
| Equipo | 1× RTX 3090 (GPU 1), Ryzen 9 9950X3D, 124 GB RAM |
| Runtime | CUDA 12.8, contexto 131072, KV int8 con 32768 tokens residentes, MTP4 |
| Coding | BigCodeBench-Hard-8: **1/8**, repetido con sampling conservador y thinking apagado: **1/8** |
| Sampling repetido | temp 0.6, top_p 0.95, top_k 20, min_p 0, repetition 1.0, presence 0 |
| Velocidad observada | Muchas tareas cortas: aprox. 92–104 tok/s decode; el probe que gastó 6144 tokens razonando dio 70,6 tok/s. No es una cifra comparable sin controlar longitud/salida y MTP. |
| Herramientas | Smoke test OpenAI-compatible y un round-trip de tool `lookup_ticket` pasaron. No es una batería suficiente para Harness o Computer Use. |
| Contexto | Needle exacto: 3/3 a 8k, 32k y 110k tokens de prompt efectivo. |

El modelo y el runtime de esa corrida ya no están en el directorio de datos de
evaluación; los recibos JSON conservados son la fuente de los resultados:

- [`summary.json`](../artifacts/strata-evaluation-20260929/summary.json)
- [`bcb8.json`](../artifacts/strata-evaluation-20260929/bcb8.json)
- [`bcb8-conservative.json`](../artifacts/strata-evaluation-20260929/bcb8-conservative.json)
- [`bcb8-thinking-probe.json`](../artifacts/strata-evaluation-20260929/bcb8-thinking-probe.json)
- [`needle.json`](../artifacts/strata-evaluation-20260929/needle.json)

La corrida de Strata y `UD-Q2_K_XL` no fue un A/B controlado: usaron cuantizaciones
y runtimes diferentes. El resumen histórico ya advierte esto. Tampoco se deben
comparar directamente las cifras de Reddit (IQ3_XXS, otro equipo/configuración)
con las de esta notebook.

## Preparación adicional del 2026-09-30

Se revisó el upstream actual y se clonó en
`~/.cache/strata-coder-eval-20260930`, commit `d6708a4aae15b4860000d54c8af9e84d684bce09`.
El engine compiló para CUDA SM86. El enlace de release prebuilt configurado por
ese checkout devolvió 404, por lo que se usó el build desde source. No se cargó
ningún modelo ni se midió rendimiento/calidad con este checkout.

Durante esa preparación se detectó una descarga independiente ya activa del
GGUF Coder IQ1_M en
`/media/cristian/7CFE1E0FFE1DC1F6/models/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`.
Para no duplicar decenas de GB ni ejecutar otra carga en las GPU, la preparación
quedó sin descargar pesos y sin arrancar el server. La compilación tampoco debe
contarse como validación del modelo.

## Próxima prueba que aporta evidencia nueva

Cuando el GGUF Coder IQ1_M termine de descargarse, ejecutar una sola campaña
nueva (no repetir Q2_0):

1. BigCodeBench-Hard-8 con los mismos ocho IDs de
   `artifacts/bigcodebench-hard-ubuntu-8.json`, sampling conservador, thinking
   apagado y el grader aislado de `artifacts/swift-genesis-evaluation-20260929/run_bcb.py`.
2. Suite de contrato de tools con los mismos schemas/prompts de
   `artifacts/swift-genesis-evaluation-20260929/run_tool_contract.py`.
3. Registrar SHA-256 de ambos shards, commit/runtime, GPUs, context/KV, MTP,
   sampling, IDs, precisión del grader, latencias y tokens/s. Si pasa esos gates,
   recién entonces medir Computer Use o Charla; el score 1/8 previo no justifica
   una campaña más grande.

La decisión de producto sigue siendo **sin cambios** hasta contar con esos
resultados: conservar perfiles actuales y no añadir Strata como preset de
coding/harness por su velocidad sola.
