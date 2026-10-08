# Investigación de `tensor split` para Qwen3.8 / `qwen4exp` — 2026-09-18

## Conclusión

El fallo actual es esperable y no apunta primero a una mala configuración de
PCIe, P2P o NCCL. `qwen4exp` está explícitamente excluido de
`llm_arch_supports_sm_tensor()`. Cuando se solicita `--split-mode tensor`, el
runtime aborta con `LLAMA_SPLIT_MODE_TENSOR not implemented for architecture
'qwen4exp'` antes de completar la carga normal del modelo.

La frase anterior —“habría que portar soporte en el planificador, kernels CUDA
y colectivas NCCL”— necesitaba una precisión:

1. **Bloqueo inmediato:** quitar el rechazo de arquitectura no alcanza, pero es
   el primer obstáculo y ocurre antes de NCCL.
2. **Bloqueo probable siguiente:** el meta-backend debe asignar un eje de
   partición válido a todos los tensores y estados de la arquitectura híbrida
   de Qwen3.8: atención, SSM/GDN, PLE, estados recurrentes, inyección y MTP.
3. **KV:** el tensor split actual no admite KV cuantizado; la primera prueba
   válida debe usar `f16`, `bf16` o `f32`. `q8_0` no es una forma válida de
   demostrar que tensor split funciona.
4. **Sampler:** algunas revisiones de llama.cpp fuerzan el muestreo a CPU con
   tensor split. Aunque el modelo cargue, eso puede degradar latencia,
   speculative decoding y tool-use.
5. **NCCL:** es necesario para que las reducciones entre GPU sean competitivas,
   pero sólo después de que el grafo y el reparto tensorial sean correctos.

Por lo tanto, recompilar con NCCL o cambiar la placa a PCIe x8/x8 no puede
resolver el rechazo actual por sí solo. PCIe sólo puede mejorar el rendimiento
de una configuración tensorial que ya cargue y sea correcta.

## Evidencia local

Hay que separar dos builds que antes estaban mezcladas:

* El checkout adaptativo que usa LlamaCode (`c28d538`, 2026-08-26) todavía no
  declara `LLM_ARCH_QWEN4EXP`. El parche no compila allí porque el enum de la
  arquitectura aún no existe. Esa build no puede validar tensor split de
  Flash-Next; sólo puede validar la ruta estable con otros GGUF.
* El `master` oficial actual (`44be98f`, 2026-09-18) sí contiene el loader,
  grafo y metadatos de `qwen4exp`, pero mantiene el rechazo explícito en
  `llm_arch_supports_sm_tensor()`. En una copia aislada quité únicamente ese
  caso, compilé con CUDA/SM86/NCCL y dejé la build fuera de producción.

La protección upstream es:

```text
src/llama-model.cpp:
LLAMA_SPLIT_MODE_TENSOR not implemented for architecture 'qwen4exp'

src/llama-arch.cpp (master oficial):
case LLM_ARCH_QWEN4EXP:   // TODO: fix test-llama-archs
    return false;
```

Las pruebas previas en las dos RTX 3090 dieron:

| Configuración | Resultado |
| --- | --- |
| `split-mode layer`, P2P/NCCL | 60,75 tok/s, estable |
| `split-mode layer`, sin NCCL | 60,73 tok/s, estable |
| `split-mode layer`, P2P desactivado | 60,61 tok/s, estable |
| `split-mode tensor`, P2P/NCCL | No inicia; incompatibilidad de `SPLIT_MODE_TENSOR`/`qwen4exp` |
| `split-mode tensor`, sin NCCL | No inicia por la misma incompatibilidad |

La build de control aislada fue compilada con `GGML_CUDA=ON`,
`CMAKE_CUDA_ARCHITECTURES=86`, `GGML_CUDA_NCCL=ON`, Flash Attention y el
runtime de dos RTX 3090. El artefacto Flash-Next disponible localmente estaba
incompleto durante la primera corrida (faltaban los shards 2 y 3), por lo que
no se inventó una métrica de generación para `qwen4exp`.

Como control de que el binario sigue funcionando, se midió un GGUF completo de
Qwen3.8-27B `qwen35`:

| Control | KV | PP | TG | Resultado |
| --- | --- | ---: | ---: | --- |
| `split-mode layer`, 512/128 | `q8_0` | 843 | 25,1 | estable |
| `split-mode tensor`, 512/128 | `q8_0` | 511–574 | 25,1 | carga; no es `qwen4exp` |
| `split-mode tensor`, 512/128 | `f16` | 524–585 | 25,2 | carga; no es `qwen4exp` |

El control demuestra que el camino tensorial genérico no está roto por CUDA o
NCCL, pero no demuestra compatibilidad de Flash-Next. También muestra que el
tensor split puede empeorar PP sin mejorar TG en esta topología `PHB` sin
NVLink.

## Resultado del guard aislado

Con los tres shards completos se probó una copia del `master` oficial donde se
quitó sólo el caso `LLM_ARCH_QWEN4EXP` de la lista excluida. No se modificó el
checkout ni el ejecutable de LlamaCode.

| Prueba | Resultado observado |
| --- | --- |
| `tensor + f16 KV + FA`, sin overrides | OOM al reservar `per_layer_token_embd.weight`: **31,32 GiB en CUDA0**; aborta en `ggml-backend-meta.cpp:1760` |
| Igual con `per_layer_token_embd.weight=CPU` | El override no evita la reserva en el meta-backend tensorial; repite el OOM de 31,32 GiB |
| `tensor + f16/bf16/q8 KV`, override global a CPU/host | Supera la reserva inicial, pero aborta en `ggml-backend-meta.cpp:819`: `GGML_ASSERT(src_ss[0].axis == GGML_BACKEND_SPLIT_AXIS_1)` dentro del manejo de `GATED_DELTA_NET` |
| `layer + q8 KV`, `per_layer_token_embd.weight=CPU`, expertos en CPU | **Carga y genera**; 12,91 PP / 12,87 TG en 128 tokens (primer smoke: 4,33 PP / 7,58 TG); sin MTP ni visión |
| Qwen3.8 `qwen35` completo, `tensor + q8 KV` | Carga y mide 399 PP / 25,5 TG en 64/16; confirma que el rechazo no es global para todas las arquitecturas |

Esto identifica dos fallos concretos detrás del guard: primero, un tensor de
27,5 GiB que el meta-backend intenta materializar en una sola GPU; después,
una incompatibilidad de ejes en el grafo GDN híbrido. NCCL y P2P no llegan a
participar en ninguno de los dos fallos. La prueba `layer` confirma que el
artefacto y el grafo CUDA sí son utilizables por la ruta soportada, aunque la
configuración con expertos en CPU es lenta.

El KV `q8_0` de `qwen4exp` no llegó a ser el primer error en la ruta tensorial:
con o sin cuantización, el grafo cae antes en la reserva/partición del modelo.
Por eso no se debe afirmar que Q8 “funciona” ni que “es la causa” de este
crash; queda bloqueado por un fallo anterior.

El P2P de lectura y escritura entre ambas placas ya fue validado. La topología
es `PHB`, sin NVLink, pero eso no explica el rechazo de arquitectura.

## Verificación contra upstream

El `master` actual de llama.cpp mantiene el chequeo de arquitectura en
`llama_model_create()` y conserva `LLM_ARCH_QWEN4EXP` en la lista que devuelve
`false`. La documentación oficial también indica que tensor split es
experimental, que `fit` no está implementado para ese modo y que el KV
cuantizado debe reemplazarse por `f16`/`bf16`/`f32`.

Fuentes:

- [llama-model.cpp, chequeo de `LLAMA_SPLIT_MODE_TENSOR`](https://github.com/ggml-org/llama.cpp/blob/master/src/llama-model.cpp)
- [llama-arch.cpp, lista de arquitecturas excluidas](https://github.com/ggml-org/llama.cpp/blob/master/src/llama-arch.cpp)
- [Documentación oficial de multi-GPU](https://github.com/ggml-org/llama.cpp/blob/master/docs/multi-gpu.md)

Hay evidencia de que el soporte está avanzando, pero no de que esté listo para
nuestro caso CUDA/Ampere. Una prueba aislada quitando el guard llegó a cargar
el ejecutable, pero no pudo pasar a la fase de grafo porque el modelo local
seguía incompleto. No se cambió el guard en LlamaCode ni se usó esa build como
runtime. En upstream, un reporte de Qwen3.8 con ROCm muestra
que el MTP nativo puede funcionar con tensor split, mientras que DFlash2 falla
con `SPLIT_AXIS_UNKNOWN`; es otra backend y no habilita automáticamente nuestro
camino CUDA. Otro reporte en CUDA documenta regresiones independientes de
offload parcial y sampler CPU con tensor split.

- [Qwen3.8 + DFlash2 + tensor split: `SPLIT_AXIS_UNKNOWN`](https://github.com/ggml-org/llama.cpp/issues/27829)
- [Regresión CUDA: offload parcial y sampler CPU](https://github.com/ggml-org/llama.cpp/issues/27467)
- [Limitación de KV cuantizado con tensor split](https://github.com/ggml-org/llama.cpp/issues/23567)

## Qué tendría que cambiar para intentarlo correctamente

No conviene cambiar sólo un `return false` y promover el resultado. El orden
mínimo de trabajo sería:

1. Compilar una rama experimental reciente con CUDA, `compute_86` y NCCL.
2. Arrancar Qwen3.8 con `--split-mode tensor`, `--flash-attn on`, `--fit off`,
   contexto corto y KV `f16`; sin DFlash2 y sin visión al principio.
3. Confirmar que ambas GPU reciben los pesos completos y que no aparece
   `SPLIT_AXIS_UNKNOWN`, `backend sampling ... using CPU` ni un fallback de
   capas a CPU.
4. Probar generación determinista y el harness antes de activar MTP nativo.
5. Recién después probar MTP, DFlash2, visión y KV `q8_0` por separado. Cada
   combinación es una hipótesis distinta y un fallo en una no invalida las
   otras.
6. Medir 8K, 32K, 131K y 262K con PP, TG, TTFT, VRAM, aceptación MTP, BCB8 y
   tool-use. Sólo una matriz completa permitiría compararlo con SOL.

La siguiente corrida quedó preparada para cuando los shards terminen de
descargarse. Se deben ejecutar, siempre en la copia experimental:

```text
tensor + f16 KV + FA + sin MTP + sin visión
tensor + bf16 KV + FA + sin MTP + sin visión
tensor + q8_0 KV                 (debe rechazarse)
layer  + q8_0 KV                 (control operativo)
tensor + MTP                     (sólo si pasa la prueba base)
tensor + visión                  (sólo si pasa MTP/base)
```

En cada paso hay que registrar el primer error, PP/TG, memoria por GPU y si el
muestreo cae a CPU. Un arranque exitoso no alcanza para promoción: también
debe pasar generación determinista, tool-use y el BCB8 del harness.

## Decisión para LlamaCode

- Mantener `split-mode layer` como ruta estable.
- No tocar el guard de `qwen4exp` en la build de producción.
- No activar tensor split por detectar NCCL o P2P.
- No cambiar la topología PCIe sólo por este problema.
- Considerar tensor split únicamente como experimento aislado cuando exista un
  commit upstream que retire explícitamente el bloqueo de `qwen4exp` y aporte
  pruebas de reparto para sus estados híbridos.

La conclusión operativa sigue siendo la misma: SOL continúa como perfil
principal y la ruta layer sigue siendo la opción segura para los modelos GGUF
de LlamaCode.
