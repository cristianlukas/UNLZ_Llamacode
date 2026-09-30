# Auditoría: NVLink frente a P2P PCIe en 2× RTX 3090 — 2026-09-30

## Veredicto

El post describe una ventaja plausible de NVLink para **tensor parallelism**,
especialmente en prefill largo y entrenamiento. No demuestra que cambiar una
ruta por capas a NVLink acelere LlamaCode ni que un bridge aporte ~50% en este
equipo. El resultado transferible más importante ya fue probado aquí: el perfil
Qwen3.8-27B ByteShape con `split-mode tensor` es superior al control `layer` en
decode y prefill de contexto largo, con paridad en las pruebas de calidad
disponibles. Se conserva como candidato experimental; no se promueve a
predeterminado hasta completar LC-H1.

No se cambia ningún perfil ni el harness por este post. No se repite el A/B de
`layer` contra `tensor` ya documentado el 27/9. No se puede ejecutar un A/B
NVLink contra P2P en este host porque sus enlaces NVLink están inactivos y no se
encontró un bridge conectado.

## Qué es comparable y qué no

- El hilo mezcla dos cosas: ancho de enlace/topología de PCIe y NVLink. Una
  caída de x8/x8 a x8/x4 puede ser distinta de instalar NVLink; no se debe
  atribuir automáticamente toda mejora a NVLink.
- NVLink ayuda cuando el runtime intercambia datos entre GPU repetidamente,
  como en tensor parallelism/all-reduce. En `split-mode layer`, cada GPU
  procesa grupos distintos de capas y la comunicación es mucho menor; por eso
  no se espera que NVLink mejore de forma relevante el camino rápido de
  LlamaCode basado en capas.
- El post no fija runtime, modelo, quant, contexto, batch, sampling, control de
  temperatura, harness de calidad ni condiciones de medición. El comentario
  sobre V100 no es una sustitución válida para un A/B de RTX 3090.
- La evidencia pública revisada distingue explícitamente las cifras de vLLM TP
  de llama.cpp. La guía de club-3090 recoge mejoras de NVLink en su escalera de
  prefill TP, pero también advierte que sus mediciones no son extrapolables a
  `layer` ni entre runtimes. La publicación independiente sobre llama.cpp con
  `layer-split` y NVLink registra resultados por profundidad, pero no incluye
  un control PCIe P2P sin bridge; por tanto no aísla el efecto de NVLink.

## Comprobación del host actual

Diagnóstico ejecutado en Ubuntu el 2026-09-30:

| Comprobación | Resultado | Lectura |
|---|---|---|
| GPU | 2× GeForce RTX 3090, ambas visibles | Hardware necesario para comparar |
| `nvidia-smi topo -m` | GPU0↔GPU1: `PHB` | Ruta PCIe vía host bridge, sin NVLink |
| `nvidia-smi topo -p2p r` | GPU0↔GPU1 y GPU1↔GPU0: `OK` | P2P PCIe de lectura disponible |
| `nvidia-smi topo -p2p w` | GPU0↔GPU1 y GPU1↔GPU0: `OK` | P2P PCIe de escritura disponible |
| `nvidia-smi nvlink -s` | NVML: todos los enlaces inactivos | No hay NVLink operativo que activar/comparar |
| `llama-bench` / `llama-server` Linux local | No encontrados en PATH, repo ni caché inspeccionada | No hay binario listo para una nueva prueba controlada en este host |

La capacidad P2P que informa `nvidia-smi` confirma que el driver permite el
acceso peer; por sí sola no demuestra que un proceso concreto lo use. La
prueba histórica separada sí verificó P2P activo/desactivado en el runtime de
entonces.

## Pruebas previas de LlamaCode que responden al post

### A/B P2P PCIe en `split-mode layer`

La campaña Linux ya comparó la ruta por capas con P2P/NCCL habilitado y con P2P
realmente desactivado. Los promedios fueron 60,75 y 60,61 tok/s, respectivamente
(aprox. +0,2% con P2P, dentro del ruido). El prefill también quedó muy cercano
(269,97 frente a 280,70 tok/s en las variantes registradas). Conclusión: P2P no
es el cuello dominante de nuestro camino estable por capas.

Referencia: [`dual-3090-llama-cpp-allreduce-post-audit-20260918.md`](dual-3090-llama-cpp-allreduce-post-audit-20260918.md)
y [`dual-3090-pcie-bifurcation-audit-20260918.md`](dual-3090-pcie-bifurcation-audit-20260918.md).

### A/B `layer` contra `tensor` en Qwen3.8-27B ByteShape

El A/B más reciente se hizo con el mismo GGUF, MTP3, visión, contexto y
herramientas en llama.cpp b10964. Fue en Windows/WDDM, donde P2P no estaba
disponible; por eso mide el efecto del modo de reparto, **no** el efecto de
NVLink ni P2P:

| Métrica | Layer Q8 | Tensor Q8 | Diferencia |
|---|---:|---:|---:|
| TG de código | 83,7 | 119,8 tok/s | +43% |
| TG narrativo | 60,7 | 79,7 tok/s | +31% |
| Prefill a 26K | 858 | 1.070 tok/s | +25% |
| Decode tras 26K | 46,8 | 66,0 tok/s | +41% |
| Computer Use | 48/48; seguridad 29/29 | 48/48; seguridad 29/29 | Paridad |
| Coding smoke / visión con tool | 3/3 / 3/3 | 3/3 / 3/3 | Paridad |

En Charla, la mediana TTFT subió de 181 a 217 ms (+36 ms) con tensor, mientras
la respuesta completa bajó de 0,94 a 0,81 s (−14%). Esto sugiere que el modo
tensor puede beneficiar respuestas habladas completas, aunque añade algo de
latencia inicial; no amerita alterar el harness de Ingi-Charla.

`tensor` pierde en prefill corto sin caché: `llama-bench` mostró −13% a contexto
0 y −3% a 32K; en prompt de 26K la medición del servidor fue +25%. La elección
depende de la forma de la carga, no es un reemplazo universal de `layer`.

BCB8 directo dio 1/8 para ambos modos, en el mismo ítem; no es el LC-H1 agentivo
completo. Por eso el perfil permanece `best=false` con HE20/BCB de LC-H1
pendientes.

Detalles, comandos, configuración y JSON reproducibles: [`reddit-dual-3090-tensor-split-audit-20260927.md`](reddit-dual-3090-tensor-split-audit-20260927.md),
[`artifacts/reddit-dual3090-tensor-20260927`](../artifacts/reddit-dual3090-tensor-20260927/)
y el perfil [`sys-bench-qwen38-byteshape-tensor-q8-mtp3-131k`](../assets/system_profiles.json).

## Relevancia por componente

- **Modelo/perfil:** ya existe un candidato superior en throughput de tensor
  para dos GPU. No se cambia SOL/default ni la receta del perfil: `tensor`
  requiere un runtime compatible y consume ambas tarjetas.
- **Ingi-Charla:** la medición completa favorece tensor en 14%, pero el TTFT
  pierde 36 ms. Sin una mejora clara de la experiencia conversacional medida
  extremo a extremo con STT/TTS, no se cambia el perfil de voz.
- **Computer Use y coding:** los smokes disponibles quedan en paridad. Una
  ganancia de prefill/decode puede reducir el tiempo de respuesta, pero no hay
  evidencia para cambiar el harness o promover calidad.
- **Subagentes:** tensor ocupa ambas RTX 3090. `SubAgentRunner` comparte el
  endpoint del agente principal, así que no ofrece una segunda GPU libre para
  un worker independiente. Un backend de subagente configurable sigue siendo
  una tarea distinta, útil con `layer` o con un modelo separado por GPU.
- **Entrenamiento:** el post sugiere NVLink para entrenamiento, pero LlamaCode
  no tiene una campaña de entrenamiento distribuido que podamos comparar en
  estos artefactos. No se infiere una recomendación de compra desde inferencia.

## Prueba pendiente, sólo si cambia el hardware/runtime

Para contestar literalmente “P2P PCIe vs NVLink” hace falta instalar un bridge
3090 compatible, verificar `nvidia-smi topo -m` como `NV#`, mantener el mismo
driver/runtime y correr tres condiciones —sin P2P, P2P PCIe, NVLink— en
**tensor parallelism**. Usar el mismo modelo y quant, contexto 8K/32K/64K/131K,
batch, KV y MTP; repetir al menos cinco veces alternando el orden; registrar
PP, TTFT, TG, temperatura/potencia, uso de cada GPU y CV. Para `layer`, medir
el mismo control como falsación de que NVLink tenga efecto general. Ejecutar
HE20/BCB LC-H1 sólo para cualquier candidato que supere la comparación de
rendimiento.

Esta prueba no se agenda ni se descarga nada ahora: falta el enlace NVLink
físico y el runtime listo en el Linux actual. El resultado se considera
duplicado del A/B del 27/9 para la comparación layer/tensor; sólo la matriz de
interconexión descrita arriba abre una nueva hipótesis.

## Fuentes externas revisadas

- [club-3090: P2P PCIe y límites por engine](https://github.com/noonghunna/club-3090/blob/master/docs/PCIE_P2P.md) — separa los resultados de vLLM TP de los de llama.cpp y detalla qué mide cada configuración.
- [club-3090: benchmarks](https://github.com/noonghunna/club-3090/blob/master/BENCHMARKS.md) — describe NVLink como una palanca de prefill TP y especifica caveats de las comparaciones.
- [Dual 3090 NVLink con llama.cpp, Qwen3.6-27B](https://lcz.me/topic/322/31) — resultados de layer-split con bridge, pero sin control PCIe P2P emparejado; no sirve para atribuir causalidad al NVLink.
