# Plan registrado antes de la prueba de contexto

Task ID: `Q-20261009-FLASHNEXT-IQ3XXS-AB`
Fecha UTC: `2026-10-10T00:06:17.351787+00:00`
Lock: `e0dc3c20-28f5-4522-8897-b124577450d6`

## Fuente recibida en este chat

Hilo de r/LocalLLM “Strata takes the promise of ‘MoE models just need a total amount of VRAM+RAM’ and makes it a reality”. El post habla de Qwen3.8-Flash-Next Q4, KV Q8, contexto 262K, 4× Tesla P100 por PCIe 3.0 x8, 128 GB DDR4-2133 y Xeon E5-2683 v4. Atribuye a Strata aproximadamente 2× la velocidad de un modelo 27B y 5× la de Flash-Next con llama.cpp personalizado. Comentarios agregan anécdotas de calidad/coding y combinan modelos, quantizaciones, hardware y forks distintos.

## Comparación local ya cerrada y reutilizada

La cola ya tenía activa esta misma evaluación de perfil IQ3_XXS en el host de 2× RTX 3090; esos resultados se reutilizan, no se repiten: Server Speed v1 (dos pasadas para IQ3_XXS y ASTRA IQ3_S calibrado), LC-H1 HE0→HE20→BCB8, TaskFlow ULTRA y un probe de sampling. Los controles SOL existentes son históricos y se usarán sólo cuando suite, HarnessSpec, seed y protocolo sean compatibles; las diferencias de modelo/runtime se reportarán como comparación de perfiles completos.

## Pregunta restante y prueba planificada

¿El perfil local ISTA base IQ3_XXS puede aceptar y recuperar un dato cerca del final de una entrada de ~258K tokens efectivos bajo configuración de contexto 262144?

- Perfil candidato: GGUF ISTA-DASLab GSQ-RCO IQ3_XXS, Strata upstream v0.1.41 / commit `fb58e0dbc8399662c0e47c76578c6e878b14f6cf`, engine CUDA SM86, 2× RTX 3090 24 GiB, KV int8, KV residente 32768, MTP4, `spec-min-p 0.70`, `pcie-frac 0.00`, split por capas automático. Sólo cambia `--max-context` de 131072 a 262144 y el puerto del config aislado.
- Métrica primaria: request válido dentro de 262144 que devuelve el passkey literal sembrado al 95% de un prompt sintético de aproximadamente 258K tokens según el tokenizer local.
- Guardas: respuesta HTTP válida, `usage.prompt_tokens` dentro del límite y sin truncamiento, timeout, OOM o caída; una sola solicitud, sin concurrencia.
- Umbral previo al inicio: `MemAvailable` ≥ 32 GiB y swap usado < 2 GiB. Abortar si `MemAvailable` cae bajo 32 GiB o swap sube a 2 GiB. Registrar RAM, swap y VRAM antes/después.
- Interpretación: smoke de capacidad y recuperación de una passkey. No prueba calidad general de contexto, ni reproduce el Q4/P100 del post. El prompt y passkey son sintéticos; se conservará SHA-256 y el script, no el prompt expandido.

Config aislada: [`iq3_xxs-context262k.json`](../../../qwen38-flashnext-iq3xxs-strata-20261009/configs/iq3_xxs-context262k.json)
SHA-256 del config: `654e9345320843bee40321e79b8430b535184ae1165026909fc2090ed7a3e7dc`

## Fuera de esta prueba

La solicitud original del post no atribuye mejora de GUI, audio ni visión. No se ejecutarán ahora Computer Usage E2E, Ingi-Charla ni visión: el engine de esta campaña declara `vision: none`, y estas dimensiones no se infieren de velocidad/coding textual. Se reutilizará la evidencia existente y se marcarán como no evaluadas para IQ3_XXS en este corte.


## Resultado del guard de 262K — 2026-10-10

**Estado: bloqueado por infraestructura/recursos antes de iniciar el modelo.**
La medición preregistrada requería `MemAvailable` ≥32 GiB y swap usado <2 GiB.
En el preflight se observaron 110,564 GiB disponibles y 3,253 GiB de swap
usado (8 GiB total); la segunda condición no se cumplió. No se cargó el engine
262K, no se generó ni envió prompt y no hubo solicitud HTTP. Por ello no hay
score de contexto y esto no se clasifica como fallo del modelo. No se limpió
swap ni se alteraron caches para forzar el ensayo. La prueba sólo se puede
retomar si se cumplen las mismas guardas; incluso si pasa, sería un smoke local
con IQ3_XXS y 2× RTX 3090, no una réplica del post Q4/4×P100.

Snapshot de cierre (`2026-10-10T00:45:35Z`): `MemAvailable=110.80 GiB`, `SwapTotal=8.00 GiB`, `SwapFree=4.80 GiB`, `SwapUsed=3.20 GiB`; la guarda seguía sin cumplirse. El registro está en `guard-abort.json`.
