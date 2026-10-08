# Evaluación de ideas club-3090 para LlamaCode — 2026-09-08

## Alcance

Se revisaron las propuestas del listado de club-3090: `benchlocal-cli`, la
jerarquía DFlash2, Qwen3.8 fast/NVFP4, concurrencia, DeepSeek con expert cache,
los slugs de Qwen3.8, Qwen3.6-35B-A3B, ThinkingCap, LMCache y los artefactos
NInfer/llama.cpp. Las referencias principales fueron:

- [DFlash2 tier hierarchy](https://github.com/noonghunna/club-3090/discussions/1076)
- [Qwen3.8 incubating slugs](https://github.com/noonghunna/club-3090/discussions/993)
- [inference-engine matrix](https://github.com/noonghunna/club-3090/blob/master/docs/INFERENCE_ENGINES.md)
- [benchmark matrix](https://github.com/noonghunna/club-3090/blob/master/BENCHMARKS.md)
- [Qwen3.8 dual 3090 SGLang recipe](https://github.com/0xSero/qwen38-3090-sglang)

La comparación local se hizo con el mismo criterio: arranque real, ausencia de
fallback/error CUDA, generación por API y límites de cuantización del equipo.
Los pesos y el KV promovidos no superan Q8. Windows no se modificó.

## Plan de pruebas ejecutado

1. Revisar qué propuestas son compatibles con dos RTX 3090/Ampere y con el
   harness actual.
2. Separar mejoras de infraestructura —P2P, reparto, prefix reuse, batch— de
   nuevos modelos o runtimes.
3. Descargar sólo un artefacto que aportaba una comparación reproducible sin
   instalar otro stack: Qwen3.8-27B UD-Q8_K_XL.
4. Probar 131K/262K, MTP2/MTP3, B512/U128 y el arranque de alta carga B4096/U512.
5. Ejecutar smoke de coding y revisar logs para corrupción, fallback, OOM y
   `device-side assert`.
6. No promover ningún perfil sin BCB formal o evidencia de calidad equivalente.

## Resultados locales

| Candidato/configuración | Resultado local | Decisión |
|---|---|---|
| Qwen3.8-27B UD-Q8_K_XL, 131K, MTP2, KV Q8 | ~48,07 tok/s; carga estable | Perfil Linux opcional |
| Qwen3.8-27B UD-Q8_K_XL, 262K, MTP2, KV Q8 | ~43,08 tok/s; sin fallback ni error CUDA | Perfil opcional de contexto/fidelidad |
| Qwen3.8-27B UD-Q8_K_XL, 131K, MTP3, KV Q8 | ~44,69 tok/s; inferior a MTP2 | No usar como default |
| Qwen3.8-27B Q8, 262K, B4096/U512 | OOM durante reserva de buffers | No usar esos tamaños |
| Qwen3.8-27B Q8, 262K, B512/U128 | Arranca y genera correctamente | Configuración elegida |
| Qwen3.8-27B Q8, smoke de coding | 3/3 respuestas semánticamente correctas; dos checks literales fallaron por acentos/truncamiento | BCB pendiente |
| SOL actual | ~74 narrativo / ~102 código; BCB 8/8 | Mantener principal |
| QWEN35-A3B | ~123,98 tok/s BCB local; visión 4/4; ~240K | Mantener experimental/concurrencia |
| DFlash2 | Ya probado: muy rápido en prompts cortos, caída fuerte en contexto largo; KV BF16 necesario para la variante estable | Fuera del dropdown prioritario: viola la política KV Q8 |
| vLLM FP8/NVFP4, SGLang/DSpark | Requieren artefactos/runtime no instalados o formatos fuera del límite; no reproducibles en esta pasada | No descargar ni promover |
| LMCache/prefix reuse | Ya validado en el stack actual; reutilización aproximada 5064/5068 tokens en la prueba previa | No agrega un perfil nuevo |

## Decisiones técnicas

- **P2P:** sigue habilitado y se conserva el reparto por capas estable. El A/B
  previo no mostró una ganancia significativa en decode single-stream; el
  beneficio esperado queda principalmente en prefill/concurrencia y depende del
  paralelismo.
- **Qwen3.8 Q8:** se agregó como `QWEN38-Q8`, Linux-only, con el modelo en
  `/media/cristian/7CFE1E0FFE1DC1F6/models/club-3090/qwen3.8-27b-gguf/unsloth-q8kxl/Qwen3.8-27B-UD-Q8_K_XL.gguf`.
  Usa MTP2, KV Q8, 262K, B512/U128 y `--tensor-split 0.55,0.45`.
- **DFlash2:** no se promueve porque la configuración estable publicada usa
  KV BF16 y la alternativa KV FP8 produjo el `device-side assert` que ya se
  observó en Ampere; además el rendimiento cae con contexto largo.
- **Qwen3.6-35B-A3B, ThinkingCap, DeepSeek, MINI, LUNA y METEOR:** no reciben
  un nuevo alias en esta pasada. Sus perfiles actuales siguen siendo los más
  reproducibles para sus respectivos usos.
- **Windows:** no se cambiaron argumentos, modelos ni orden de perfiles.

## Tabla operativa actualizada

| Perfil | Modelo/configuración | Velocidad local | Calidad/agentes | Contexto | Visión | Estado/uso |
|---|---|---:|---:|---:|---:|---|
| **SOL** | Qwen 28B Q4 + MTP3, KV Q4, P2P | 74 narr. / 102 código | BCB 8/8 | 131K | No validada | Principal para coding |
| **QWEN38-Q8** | Qwen3.8-27B UD-Q8_K_XL + MTP2, KV Q8 | 43,08 a 262K | BCB pendiente; smoke funcional | 262K | No | Fidelidad/contexto, experimental |
| **TERRA** | ThinkingCap Qwen3.6-27B Q4 + MTP4, KV Q8 | 56–58 | BCB histórico 6/8 | 64K | Sí | Razonamiento/visión |
| **LUNA** | Ling 3.0 Tiny Q6 + template Bailing, KV Q8 | 200,95 histórico | HE0 previo 0/1; smoke tool válido | 131K | No | Auxiliar rápido |
| **METEOR** | BigBang 35B-A3B Q4 + MTP5, KV Q8 | 211,18 histórico | BCB histórico 3/8 | 64K | Sí | Throughput/lotes |
| **GALACTA** | DeepSeek V4 Flash IQ3_S, KV Q4 | 9,65 | BCB 8/8 | 131K | No | Máxima calidad, lento |
| **DEEPSEEK FUSION** | DeepSeek Fusion IQ3/Q4, KV Q4 | 10,55 histórico | BCB histórico 8/8 | 131K | No | Alternativo |
| **MINI** | MiniCPM5-2B Q4, KV Q8 | 248,90 | BCB 1/8; HE0 1/1 | 131K | No | Subagentes/resúmenes |
| **QWEN35-A3B** | Qwen3.6-35B-A3B INT4, vLLM TP2/P2P, KV FP8 | 123,98 BCB; N4 296 agregado | HE20 20/20; BCB 4/8 | ~240K | 4/4 | Experimental/concurrencia |

La tabla de estrellas y la clasificación de uso quedan sincronizadas en
[`profile-use-case-stars-20260908.md`](profile-use-case-stars-20260908.md).
