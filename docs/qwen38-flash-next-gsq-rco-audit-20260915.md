# Qwen3.8-Flash-Next GSQ/RCO — auditoría para LlamaCode

Fecha: 2026-09-15  
Candidato: `pfeifferj/Qwen3.8-Flash-Next-GSQ-RCO-GGUF`  
Decisión: **no descargar, no agregar al menú y no reemplazar SOL**.

## Qué propone

Es una cuantización GGUF no uniforme de 3,5 bits que asigna el tipo de
cuantización por tensor. Incluye un `mmproj` BF16 para visión y conserva las
matrices de embeddings/token y n-gramas en BF16.

Archivos publicados:

| Archivo | Tamaño | Observación |
|---|---:|---|
| Pesos GSQ/RCO | 47.94 GB | Requiere el shard de embeddings |
| Token + n-gram embeddings | 103.68 GB | BF16, obligatorio |
| `mmproj` | 0.91 GB | Visión |
| **Total** | **~152.5 GB** | Sin contar KV, runtime ni swap |

El modelo usa la arquitectura `qwen4exp` y la tarjeta fija como referencia el
commit `f3f1a8f` de llama.cpp. Nuestro checkout experimental Flash-Next conoce
`qwen4exp`, pero no es el runtime fijado por este artefacto.

## Compatibilidad con nuestra máquina y reglas

La máquina tiene 2× RTX 3090, P2P activo, aproximadamente 123 GiB de RAM y
8 GiB de swap. La receta de referencia pide 2×24 GB, 128 GB de RAM y al menos
32 GiB de swap —48–64 GiB es más seguro— porque el loader puede superar la RAM
física durante el arranque.

El modelo declara KV BF16 en su layout de referencia. Eso supera la regla de
LlamaCode de usar como máximo KV Q8. No hay evidencia publicada de que la
variante con KV Q8 conserve la misma calidad ni de que funcione con el mismo
runtime.

Descargarlo ahora ocuparía aproximadamente 152.5 GB en
`/media/cristian/7CFE1E0FFE1DC1F6/models`, dejando sólo unos 40 GB libres en la
partición que ya está bajo presión. Sin swap suficiente, la prueba no sería una
validación limpia y podría terminar en OOM durante la carga.

## Evidencia publicada

La evaluación pública informa 58.25% en MMLU-Pro frente a 55.40% BF16,
perplexity 3.1058 frente a 3.0533, IFEval estricto 13/16 y GSM8K 8/8. No
publica BCB, HE0/HE20, tool-use, velocidad local ni una validación de contexto
largo comparable con nuestra matriz.

## Comparación con LlamaCode

| Perfil | Calidad agentiva | Velocidad/contexto | Visión | Decisión |
|---|---|---|---|---|
| SOL | BCB 8/8, tool-use válido | 74 narrativo / 102 código; 262K validado | Validada en el stack actual | Mantener default |
| ASTRA Q4 | BCB no válido; varias recetas dieron salida corrupta | 16–41 tok/s; 196K experimental | No válida | No reemplazar |
| ASTRA IQ1_S | Smoke Python válido; BCB completo pendiente | 24–26 tok/s hasta 262K | No validada | Experimental |
| GSQ/RCO | Sin BCB ni tool-use publicado | Sin medición local; requiere BF16 KV en la receta | `mmproj` incluido | No promover |

## Qué sí sirve

- La asignación no uniforme por sensibilidad es una idea válida para futuras
  cuantizaciones de ASTRA.
- El `mmproj` demuestra que la arquitectura puede conservar visión junto con
  una cuantización agresiva.
- La separación de embeddings en un shard mmapeado puede ser útil para estudiar
  modelos enormes, pero no es una mejora de rendimiento demostrada en nuestro
  harness.

No se incorporan flags ni perfiles porque el candidato no cumple KV Q8,
requiere un runtime fijado distinto y carece de validación agentiva comparable.
SOL permanece sin cambios.

## Revisión del reporte 2× RTX 5090 / RPC — 2026-09-17

Se revisó el reporte de `ilarp` sobre Qwen3.8-Flash-Next GSQ/RCO y se lo
contrastó con el estado local. No se repitió una descarga o benchmark que ya
había sido descartado en esta misma auditoría; se hicieron únicamente las
comprobaciones nuevas de compatibilidad, recursos y procedencia.

### Qué es comparable y qué no

El reporte externo mide dos RTX 5090 conectadas por una red ConnectX-5 de
100 Gb/s y comunica 90–100 tok/s de decode y ~3000 tok/s de prefill para una
variante Q2. Eso no es comparable directamente con nuestras dos RTX 3090:
además de la diferencia de GPU, el transporte RPC de 100 Gb/s no equivale a
nuestro P2P PCIe local. El propio hilo indica que al pasar a Q4 la velocidad
cae aproximadamente a 40 tok/s, y otro resultado del mismo hilo reporta una
caída muy fuerte al crecer el contexto.

La recomendación del hilo apunta al artefacto GSQ/RCO publicado por
`pfeifferj`, que no es un Q2 liviano convencional:

| Comprobación | Resultado local |
|---|---|
| Pesos GSQ/RCO | No descargados; 47,94 GB publicados |
| Embeddings BF16 obligatorios | No descargados; 103,68 GB publicados |
| `mmproj` BF16 | No descargado; 0,91 GB publicado |
| Requisito total de almacenamiento | ~152,5 GB, antes de KV/runtime |
| Arquitectura/runtime | `qwen4exp`; el artefacto fija llama.cpp `f3f1a8f` |
| Runtime LlamaCode disponible | 0.3.0-dev, commit `9bd97fe`; no es el commit fijado |
| Flags relevantes disponibles | `--tensor-split`, `--no-kv-offload`, `--lazy-mode`, `--moe-expert-cache` |
| GPU | 2× RTX 3090; ~23,0 y ~24,0 GiB libres al comprobar |
| RAM/swap | 123 GiB RAM, 96 GiB libres; sólo 8 GiB swap |
| Espacio libre | ~271 GB en la partición de modelos; ~650 GB en Disco local |

La presencia de los flags no demuestra que el modelo cargue: faltan tanto el
artefacto como el runtime fijado y la validación numérica de `qwen4exp` para
esta combinación. La RAM disponible tampoco deja un margen cómodo para una
carga que necesita mapear 103,68 GB de embeddings BF16, mantener KV y ejecutar
buffers de dos GPUs. `--no-kv-offload` sólo mueve KV a RAM; no convierte el
perfil en KV Q8 ni resuelve el requisito de memoria.

### Resultado de decisión

No se encontró ninguna métrica local que supere a SOL. El reporte externo no
aporta BCB, HE0/HE20, tool-use, visión validada, estabilidad multi-turno ni
velocidad en nuestras 3090. La evidencia local vigente sigue siendo:

| Perfil | Velocidad local | Calidad/uso | Contexto/visión | Decisión |
|---|---:|---|---|---|
| SOL | 74 narrativo / 102 código tok/s | BCB 8/8, tool-use válido | 262K; visión validada | Mantener default |
| GSQ/RCO | Sin medición local | Sin BCB ni tool-use | `mmproj` publicado; no validado aquí | No descargar ni promover |

La idea reutilizable es estudiar cuantización no uniforme y separación de
embeddings para una futura variante de ASTRA, pero no justifica modificar el
perfil activo. El resultado queda registrado para que una futura revisión no
vuelva a repetir la descarga ni confunda los números de 2×5090/RPC con los de
nuestro stack de 2×3090.

## Revisión del post IQ3_XXS / GSQ-RCO en RTX 5070 — 2026-09-18

Se revisó también el reporte de una variante `Qwen3.8-Flash-Next` IQ3_XXS/
GSQ-RCO en una RTX 5070 de 12 GB. El autor informa aproximadamente 15 tok/s
de decode y 100–120 tok/s de prefill a 20K, con una medición posterior de
19–21 tok/s y 450–550 tok/s de prefill a 128K. Son números de otra GPU, otra
capacidad de memoria y otro reparto de pesos; no son una comparación directa
con las dos RTX 3090 ni con el backend vLLM de SOL.

El hilo tampoco aporta BCB, HE0/HE20 ni una validación de tool-use comparable.
La afirmación informal de calidad cercana a Q6–Q8 queda debilitada por los
comentarios del mismo hilo: otro usuario la sitúa más cerca de Q4 para coding
y reporta peor desempeño en un harness. No hay evidencia suficiente para
convertir esa impresión en una métrica de calidad de LlamaCode.

El artefacto no está presente en ninguna de las particiones revisadas. La
auditoría del repositorio calcula aproximadamente 47,94 GB para los pesos
GSQ/RCO, 103,68 GB para embeddings/n-gram BF16 y 0,91 GB para `mmproj`, unos
152,5 GB antes de KV y runtime. Descargarlo ahora consumiría espacio sin
habilitar una prueba comparable reproducible.

### Decisión actualizada

| Perfil | Evidencia local | Contexto/visión | Decisión |
|---|---|---|---|
| SOL | 74 narrativo / 102 código, BCB 8/8, tool-use válido | 262K; visión validada | Mantener default |
| IQ3_XXS / GSQ-RCO | 19–21 tok/s externos; sin BCB ni tool-use local | 128K externo; sin visión validada localmente | No descargar ni promover |

No se modificaron perfiles, defaults ni el dropdown. La única idea potencialmente
reutilizable sigue siendo explorar cuantización no uniforme y separación de
embeddings en una futura variante, pero requiere un artefacto local y una
validación completa antes de justificar otra descarga.
