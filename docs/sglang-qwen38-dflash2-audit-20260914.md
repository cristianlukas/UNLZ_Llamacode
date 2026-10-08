# Auditoría de la receta SGLang + DFlash2 para Qwen3.8 — 2026-09-14

## Resultado ejecutivo

La receta del post es técnicamente interesante, pero no es un perfil superior
reproducible para LlamaCode en esta PC. El resultado publicado usa SGLang 0.5.19,
CUDA 13, un target Qwen3.8 FP8 específico y un drafter DFlash2 FP8 separado.
Ninguno de esos artefactos/runtime está instalado como stack operativo de
LlamaCode.

No se cambió SOL ni se agregó SGLang al flujo de lanzamiento.

## Qué se verificó localmente

| Elemento | Estado local | Consecuencia |
|---|---|---|
| SGLang 0.5.19 | No instalado; no hay imagen Docker SGLang | No se puede reproducir la receta |
| Target FP8 del post | No está en los directorios de modelos | No hay comparación directa |
| Drafter Qwen3.8 DFlash2 FP8 | No está instalado localmente | Falta el componente central |
| Imagen Docker vLLM | Existe `vllm/vllm-openai:v0.27.1` | No equivale a SGLang y ya tuvo una prueba DFlash fallida |
| Endpoints externos 8000/8001 | Apagados | No hay benchmark API que medir |
| GPUs | 2× RTX 3090, 24 GB, SM86, P2P Linux | Hardware compatible en capacidad, no suficiente para validar el stack |

## Comparación con los datos publicados

| Configuración | Resultado publicado | Comparación local |
|---|---:|---|
| Qwen3.8 sin drafting, 2 solicitudes | 53 tok/s agregado | No comparable: distinto target/runtime y no reproducido |
| MTP, 2 solicitudes | 110 tok/s agregado | SOL local ya validó 74 narrativo / 102 código y BCB 8/8 |
| DFlash2 FP8, 2 solicitudes | 143 tok/s agregado | No reproducido; requiere target y drafter FP8 SGLang |
| SOL local, MTP4, 8 solicitudes | 289,2 tok/s agregado | Es la referencia local de concurrencia ya validada |
| SOL local, 1 solicitud | 74 narrativo / 102 código | Perfil operativo actual con tool-use y BCB 8/8 |

Las cifras del post son throughput agregado de dos solicitudes en una RTX 4090D
modificada a 48 GB. No son una medición single-stream ni una comparación directa
con los números de LlamaCode.

## Fallos DFlash2 ya reproducidos

La prueba local anterior con Qwen3.8 + draft DFlash2 produjo:

```text
done_getting_tensors: wrong number of tensors; expected 81, got 58
```

La prueba vLLM TP2/P2P anterior sí llegó a medir aproximadamente 92,8 tok/s
narrativos y 171 tok/s de código en prompts cortos, pero falló con:

```text
CUDA device-side assert
```

La variante que evitaba el assert exigía KV BF16, fuera de la política del
proyecto (máximo Q8), y sufría una caída fuerte en contexto largo.

## Aspectos útiles del post que ya aplicamos o conservamos

- `max-running-requests` bajo: SOL usa un límite conservador y el KV pool se
  comparte; no se debe reservar artificialmente concurrencia × contexto máximo.
- KV FP8 equivale a 8 bits y respeta el límite Q8, pero sólo es válido si el
  backend lo implementa correctamente en SM86.
- `chunked-prefill-size` y `max-prefill-tokens` son controles de equidad entre
  agentes, no una mejora universal de decode. SOL ya fue medido con cargas de
  concurrencia y contexto.
- `sleep-on-idle` es una idea útil para evitar consumo de CPU de un servidor
  externo, pero no se incorpora porque LlamaCode debe iniciar/detener sus
  backends según el perfil activo.
- `tool-call-parser qwen3_coder` y `reasoning-parser qwen3` no se pueden
  transplantar directamente a llama.cpp; la validación local de SOL ya cubre
  tool calls por su propia ruta.

## Decisión

No hay evidencia local para reemplazar SOL. Se mantienen:

- SOL como default de coding/agentes.
- TERRA para razonamiento y visión.
- QWEN35-A3B para concurrencia/visión experimental.
- GALACTA para calidad máxima lenta.

SGLang + DFlash2 queda como experimento externo pendiente de una instalación
aislada, target FP8 y drafter FP8 compatibles. No se descargaron esos artefactos
porque consumirían decenas de GB en una partición que ya tiene aproximadamente
62 GB libres y no cambiarían la decisión sin una integración LlamaCode validada.
