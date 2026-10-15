# Resultados — Q-20261015-ANYJEV-EVAL

Fecha: 2026-10-15. Estado: screening local completado; conclusión provisional;
sin integración ni promoción de perfil.

## Decisión

AnyJev L0 muestra una señal favorable para reducir la sensibilidad al orden en
un fixture sintético de routing de LlamaCode con Qwen3.8-27B AutoRound INT4
servido por vLLM. El conteo de respuestas que cambió al invertir las cuatro
opciones bajó de 9/32 en `raw` a 1/32 en L0. La exactitud fue 78,1%/90,6% para
`raw` y 96,9%/93,8% para L0 (orden canónico/inverso, respectivamente).

Esto no alcanza para integrar AnyJev ni para darle autoridad sobre acciones.
Sólo hubo una ejecución determinista de 32 casos sintéticos; el ECE de L0 fue
0,172/0,138, así que sus confianzas siguen mal calibradas en este corpus. El
error observado entre las pocas respuestas con confianza ≥0,95 fue 0/7 y 0/8,
pero esos subconjuntos pequeños no demuestran un límite de riesgo. No hubo
ningún falso `read_only`/`reversible_local` en solicitudes etiquetadas para
aprobación/bloqueo, pero el fixture no es un holdout real ni cubre decisiones
con efectos. Se mantienen los guards y aprobaciones deterministas de
LlamaCode.

Además, AnyJev 0.3.0 ofrece backends HF y vLLM; su roadmap aún marca el backend
llama.cpp como no publicado. El resultado local usa el checkpoint AutoRound
HF servido en vLLM y no se transfiere a los perfiles GGUF/llama.cpp. No se
cambió código de producto, configuración, prompt ni perfiles.

## Protocolo y huellas

- Protocolo preregistrado: [PLAN.md](PLAN.md), fixture
  [routing-risk-screen-v1.json](fixtures/routing-risk-screen-v1.json), 32
  casos sintéticos (8 por clase), cuatro opciones, orden canónico e inverso.
- Modelo local: Qwen3.8-27B AutoRound INT4, revisión
  `b4c61732c4f2d8af323d75ba5702b5c7f3361539`; los ocho shards safetensors
  coinciden con el manifiesto existente, comprobación en
  [sol-model-sha256-check.txt](receipts/sol-model-sha256-check.txt). No se
  descargaron pesos.
- Runtime: imagen local `vllm/vllm-openai:v0.27.1`, ID
  `sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967`,
  TP2, dos RTX 3090, longitud máxima 4096, una secuencia, temperatura 0,
  servidor loopback temporal. Paquete AnyJev 0.3.0, wheel SHA-256
  `24217f23eecb3859353d625b89e0047d02c70c8ce993f956e118d7e39b9dcf3f`.
- `raw`: una solicitud etiquetada por caso/orden. `L0`: cuatro rotaciones
  cíclicas completas y prior de batch (fuerza 0,75); se confirmó en los
  diagnósticos de las 64 decisiones L0. Temperatura 0; sin herramientas ni
  efectos externos. El total del lote fue 320 vectores de log-probabilidades.
- Huellas de los datos principales: fixture SHA-256
  `04ce82d2b90eb2b132db8650d81acf76a3888e864713a05364f94c69e981cb2d`;
  resultados JSON SHA-256
  `4b8b25748d592bf1a46bc2efce7a7419040d891b1d339408c7a1873430329a62`;
  recibos crudos SHA-256
  `1d4be394cdba507bf76a6c02d903c662ce217097d14566610c53f42092b4152f`.

## Ejecución y resultados

| Brazo | Exactitud | Por clase: read-only / reversible / aprobación / aclarar-bloquear | Brier | ECE-10 | Cobertura conf. ≥0,95 (error observado) | Falsos low-risk en aprobación/bloqueo |
|---|---:|---|---:|---:|---:|---:|
| raw, canónico | 78,1% | 50,0 / 75,0 / 87,5 / 100% | 0,351 | 0,109 | 15,6% (0/5) | 0 |
| raw, inverso | 90,6% | 100 / 87,5 / 100 / 75,0% | 0,162 | 0,122 | 25,0% (0/8) | 0 |
| L0, canónico | 96,9% | 100 / 87,5 / 100 / 100% | 0,135 | 0,172 | 21,9% (0/7) | 0 |
| L0, inverso | 93,8% | 87,5 / 87,5 / 100 / 100% | 0,179 | 0,138 | 25,0% (0/8) | 0 |

La latencia de solicitud p50/p95 fue 121,5/132,4 ms sobre 320 peticiones.
Los lotes de 32 tomaron 3,96/3,93 s en raw y 14,07/14,36 s en L0, para orden
canónico/inverso. La lectura L0 cuesta aproximadamente cuatro veces más
solicitudes que raw en este caso de cuatro opciones.

## Pruebas ejecutadas

- Import de AnyJev 0.3.0 y construcción de `Decider`, `Question` y
  `VLLMBackend`: pasó en el contenedor aislado.
- Prueba `FakeBackend` de 32 casos artificiales con fuerte sesgo de posición:
  raw cambió 32/32 respuestas al rotar etiquetas; L0 las corrigió 32/32. Es
  verificación del algoritmo, no un score del modelo.
- Smoke real: API vLLM lista; 10 peticiones; las cuatro variantes devolvieron
  distribuciones normalizadas. El primer guardado falló por un `ndarray` no
  serializable; se corrigió la conversión del recibo y se repitió con éxito.
- Lote real completo: 320/320 vectores recibidos, 32 casos por cada uno de los
  cuatro brazos, sin error de API. La verificación independiente
  [verification.json](receipts/verification.json) recalculó exactitud, Brier
  y cambios por orden, comprobó todas las masas de probabilidad y confirmó
  cuatro rotaciones/prior batch en L0.
- El primer arranque de vLLM no llegó a cargar el modelo: Triton no podía
  mapear su `.so` desde el tmpfs. Se corrigió la opción de montaje a `exec`;
  el segundo arranque cargó el modelo y expuso la API. Logs y respuestas están
  en [receipts](receipts/).
- Contenedor detenido y eliminado. El [postflight](receipts/postflight.json)
  registra GPU sin procesos de cómputo, puerto 8117 libre, sin contenedores,
  MemAvailable 119,5 GB y PSI de memoria avg10 en 0.

## Límites y siguiente prueba

Este screen no prueba un agente conectado, uso de herramientas, Computer Usage,
visión, voz, clasificación de tareas reales, prompt injection ni efectos sobre
archivos o cuentas. El fixture exacto no debe repetirse para afirmar mejora.
L0 corrige efectos de posición/prior de etiquetas; no es un calibrador de
confianza. La cifra publicada por AnyJev en Qwen3-8B/BANKING77 es evidencia de
los autores, no resultado de LlamaCode.

Fuentes primarias: [README AnyJev 0.3.0 en el commit publicado](https://github.com/nokia-applied-research/AnyJev/blob/1ffa57b5287572cd173e1dc83d8a8f2e8dedca00/README.md),
[contrato de niveles](https://github.com/nokia-applied-research/AnyJev/blob/main/docs/levels.md),
[roadmap de backends](https://github.com/nokia-applied-research/AnyJev/blob/main/ROADMAP.md)
y [versión publicada en PyPI](https://pypi.org/project/anyjev/).

Una nueva ronda sólo se justifica con un holdout etiquetado de solicitudes
reales/desidentificadas, al menos tres repeticiones preregistradas, medición de
calibración fuera de muestra y un runner que mida las decisiones del agente
con sus guards intactos. Para perfiles llama.cpp hace falta primero un backend
publicado/compatible. Ningún score de esta campaña autoriza automatizar
acciones.
