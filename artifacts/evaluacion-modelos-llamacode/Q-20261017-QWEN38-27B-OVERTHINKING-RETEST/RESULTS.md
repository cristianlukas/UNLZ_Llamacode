# Resultados — Q-20261017-QWEN38-27B-OVERTHINKING-RETEST

## Decisión

El hilo de Reddit no demuestra que Qwen3.8-27B sea un agente general confiable ni
que UD-Q3/Q2 supere a otros quants. El screen local válido de ByteShape pasó
HumanEval 20/20 en primer intento, con una señal de estancamiento y algo de
redundancia de herramientas. Agention AP-Q3 tuvo un HE20 inválido por el límite
de tiempo equivocado del colector que yo configuré. Por eso no hay par válido
AP/ByteShape y no se declara superioridad, mejora estable ni promoción. Los
perfiles productivos quedaron intactos.

## Alcance y fuentes

El material es una anécdota de Reddit y mezcla modelos, cuantizaciones, runtimes,
hardware y tareas distintas. Los dos archivos locales no son los UD del post:
Agention AP-Q3_K_XL (`b5b35d…c1c8fc`) y ByteShape IQ4_XS
(`89434f…218b78b`). Los archivos Unsloth `UD-Q3_K_XL` y `UD-Q2_K_XL` no estaban
instalados; no se descargaron. El archivo UD-Q3_K_XL sí existe en el repositorio
público y pesa 13,1 GB, lo cual confirma que la hipótesis se podría probar más
adelante, pero no sustituye la prueba local.

Fuentes primarias revisadas:

- [Tarjeta oficial Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B): thinking usa como recomendación T=1.0, top-p=0.95, top-k=20, min-p=0, presence=0 y repetition=1; `reasoning_effort=medium` balancea precisión y velocidad. La tarjeta advierte que bajar el esfuerzo no siempre reduce el tiempo total de un agente multi-turno, pues puede aumentar fallos y reintentos. Para reducir repetición permite elevar presence penalty, con posibles efectos en mezcla de idioma o rendimiento.
- [README oficial de llama.cpp server](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md): `--predict` limita los tokens de salida; `repeat-penalty=1.0` y `presence-penalty=0.0` desactivan esas penalizaciones. Límite de salida y prevención de loops son controles distintos.
- [Método Unsloth Dynamic v2.0](https://unsloth.ai/blog/dynamic-v2) y [archivo UD-Q3_K_XL](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF/blob/main/Qwen3.8-27B-UD-Q3_K_XL.gguf): las métricas del proveedor no son una comparación local de coding/agente y no validan la afirmación del post para esta máquina.

## Configuración de las pruebas

Se usó una instancia aislada de LlamaCode y llama.cpp `0.5.0-dev build1`
(commit `836d571`), una ranura, contexto 32.768, KV Q8, MTP apagado, seed
4242, HarnessSpec `sha256:cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef`
y ejecución serial en GPU1. Las huellas efectivas fueron AP
`3f9cc2a5d8353189c5e6d931799e8ac513412f466d6a22986fab3f6dd746e8b2` y ByteShape
`ced2af413d6b43d2929db712034435cee2d6dd0e9bd01a4b0d49b809a181f0cb`.

El perfil servidor usó T=0,6, top-p=0,95, top-k=20, min-p=0, repeat=1 y
presence=0. En el benchmark de agente, LlamaCode limita la temperatura efectiva
a 0,1 (`min(profileTemp, 0.1)`). Por tanto, el HumanEval no prueba la
recomendación oficial T=1.0; sí mide el comportamiento actual del harness. El
probe directo de presupuestos sí usó T=0,6 y mandó `reasoning_budget_tokens`,
`chat_template_kwargs.enable_thinking` y `reasoning_effort=medium`. El runtime
local confirma esos campos en `server-common.cpp`.

## Resultados de coding/agente

| Perfil / etapa | Resultado | Estado e interpretación |
|---|---:|---|
| Agention AP-Q3, HE0 | 1/1, primer intento, sin reparación | Válido. El primer arranque de HE0 fue cancelado antes de inferencia durante la carga; el segundo fue el recibo válido. |
| Agention AP-Q3, HE20 | 5 de 20 alcanzados; 15 sin completar | **Inválido, sin score.** Mi colector pasó timeout 900 s aunque la pantalla preregistrada era 1.800 s; cortó a 901,1 s. El recibo registra `0/0` como inválido, no como fallo del modelo. No hubo BCB8. |
| ByteShape IQ4_XS, HE0 | 1/1, primer intento, sin reparación | Válido; 27,08 s de benchmark y 1 tool call. |
| ByteShape IQ4_XS, HE20 | **20/20**, primer intento 20/20 | Válido; 1.530,9 s. `failed=false`, `timedOut=false`; el gate dejó HE0/HE20 válidos y BCB pendiente. |

En ByteShape HE20 el agente hizo 53 llamadas: 52 exitosas (98,1%), una fallida,
cinco redundantes y un evento de estancamiento (`list_dir` repetido sobre `/`
sin evidencia nueva); el promedio fue 29,74 tok/s y el TTFT medio registrado
15,25 s. No hubo `stream_repetition`. La suite de código pasó completamente,
pero la telemetría sí muestra que el costo de supervisión del agente no es cero.

BCB8 no se inició: HE20 terminó con sólo unos tres minutos de la ventana
acumulada de 30 minutos de este perfil, insuficientes para correr BCB8 completo.
TaskFlow ULTRA tampoco se inició: AP no tiene HE20 válido y el plan no permite
continuar el screen comparable con esa etapa incompleta. No se infiere nada de
voz, visión E2E, contexto largo, Computer Use ni rendimiento a partir de estos
casos; se conservan los recibos históricos de esas modalidades.

## Sonda directa de presupuesto de razonamiento

Se ejecutaron 18 solicitudes por perfil (seis tareas × presupuesto 0/512/2048),
max_tokens=512. Los 36 requests tuvieron HTTP 200. Resultados de tareas
completas y aceptadas:

| Perfil | Budget 0 | Budget 512 | Budget 2048 | Caso de seguridad |
|---|---:|---:|---:|---|
| AP-Q3 | 5/6 | 5/6 | 5/6 | Incompleto por `finish_reason=length` en los tres presupuestos. |
| ByteShape IQ4_XS | 6/6 | 5/6 | 5/6 | Completo con thinking apagado; truncado a 512 tokens con thinking en 512 y 2048. |

Para ambas cuantizaciones las salidas finales de los seis casos con budget 512 y
2048 fueron iguales entre sí; en los cinco casos no truncados también coincidió
la aceptación. El presupuesto 2048 no produjo una mejora visible en esta sonda.
La petición de 512/2048 no terminó el caso de seguridad porque max_tokens=512
cortó la respuesta; por ello no se cuenta como fallo de calidad. El uso de
reasoning content creció al habilitar thinking, pero el runtime no entregó un
contador de reasoning tokens en `usage`, así que no se afirma un ahorro preciso
de tokens. Esta sonda es pequeña y de una sola corrida.

## Qué queda probado y qué no

La recomendación de `medium` tiene respaldo oficial como punto de equilibrio.
Un límite de salida `n_predict` sirve para acotar una generación, pero no basta
para garantizar que el agente no repita herramientas: en el único HE20 válido
hubo una llamada redundante fallida, cinco redundantes según el recibo y un
estancamiento. El evento de stream repetido de AP ocurrió en una corrida
incompleta y no sirve para una comparación de calidad. No conviene subir la
penalización global de repetición por una observación aislada; el modelo oficial
recomienda repetition=1 y advierte efectos secundarios de presence penalty alto.

La afirmación favorable sobre UD-Q3/Q2 sigue sin probarse porque esas
cuantizaciones no son las instaladas. El resultado 20/20 de ByteShape es un
screen, no una mejora frente a AP ni una promoción: falta un HE20 AP válido,
BCB8 y repetición pareada. No se cambiaron perfiles productivos ni código del
producto.

## Validación y postflight

- `python3 -m py_compile artifacts/evaluacion-modelos-llamacode/Q-20261017-QWEN38-27B-OVERTHINKING-RETEST/scripts/*.py`: pasó.
- Todos los recibos JSON del task root se parsearon correctamente.
- No se tocó C++/QML ni lógica del producto, por lo que no correspondía correr el build ni `tests-linux.sh` del producto.
- Los servidores de modelo de las corridas están detenidos. La instancia aislada de LlamaCode se detuvo y se verificaron cerrados sus puertos; el estado de GPU se comprobó en postflight.

Recibos, scripts y huellas están en `receipts/`, `scripts/` y `runtime/` bajo
este directorio. El resumen de presupuestos está en
`receipts/byteshape-reasoning-budget-summary.json`; el postflight está en
`receipts/postflight.json`. El plan preregistrado y sus desviaciones están en
`PLAN.md`.
