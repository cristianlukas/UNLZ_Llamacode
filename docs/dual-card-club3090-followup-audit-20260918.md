# Auditoría de la guía Dual 3090 de club-3090

Fecha: 2026-09-18  
Equipo: 2× RTX 3090 en Ubuntu, P2P PCIe activo, sin NVLink.

Fuente revisada: [club-3090 DUAL_CARD.md](https://github.com/noonghunna/club-3090/blob/master/docs/DUAL_CARD.md).

## Resultado

La guía no aporta un perfil nuevo que supere a los perfiles ya instalados en
LlamaCode. Sus recomendaciones relevantes ya están cubiertas por SOL,
QWEN35-A3B y el soporte experimental NInfer. No se descargaron modelos nuevos
ni se modificó el default.

## Correspondencia con los perfiles locales

### SOL

La receta equivalente a `vllm/dual` ya está instalada y es el perfil principal:

- Qwen3.8-27B AutoRound INT4.
- vLLM 0.27.1, TP=2 y P2P PCIe.
- KV FP8, contexto configurado a 262.144 tokens.
- MTP4 y muestreo conservador (`temperature=0.6`, `top_p=0.95`,
  `top_k=20`, `min_p=0.0`).
- Prefix caching, chunked prefill y normalización determinista de los schemas
  de herramientas ya implementados.

La prueba E2E de caché registrada previamente redujo el TTFT de 10,682 s a
1,302 s con 17.776 tokens reutilizados. Cambiar el orden de las claves de las
herramientas invalida correctamente la caché; la canonicalización del harness
evita esa pérdida espuria.

Conclusión: SOL permanece como default y no requiere otra variante de la guía.

### QWEN35-A3B

La recomendación de la guía para concurrencia y visión ya fue reproducida
localmente:

- 129,27 tok/s narrativo y 129,66 tok/s código en BCB.
- 134,4 tok/s en la prueba directa.
- 295,9 tok/s agregados con cuatro solicitudes cortas.
- Visión 4/4.
- Contexto validado hasta 240.660 tokens.
- BCB histórico 4/8; no es un reemplazo de SOL en calidad agentiva.

Conclusión: se conserva como perfil multimodal/concurrente secundario.

### NInfer Qwen3.6-35B-A3B

La ruta NInfer de la guía también fue probada localmente, pero con otra
ventaja: puede servir concurrencia acotada en una sola RTX 3090.

- Texto, MTP3, 4K: 544,8 PP y 190,08 TG; sin MTP: 572,0 PP y 159,66 TG.
- Contexto de texto medido hasta 262K; entre 32K y 131K se observaron
  149,5–141,2 TG.
- Visión funcional a 8K, 32K, 64K y 131K, cerca de 161–166 TG.
- Dos solicitudes cortas: aproximadamente 224 tok/s agregados.
- Prefix reuse validado: 90/97 tokens reutilizados y prefill de 137 ms a 22 ms.
- La visión a 262K excede la reserva segura del runtime.

Conclusión: se conserva como experimental para visión/concurrencia; no supera
a SOL en el conjunto de calidad y estabilidad del harness.

## Recomendaciones de la guía que sí aplican

### Caché y herramientas

La guía confirma que la estabilidad del prefijo es crítica en agentes. El
harness ya ordena recursivamente las claves de objetos JSON de herramientas y
mantiene el orden semántico de arrays. La regresión de cableado de herramientas
está en 52/52.

### `max_num_seqs` y subagentes

`max_num_seqs` es un límite de concurrencia, no una reserva fija de contexto.
Por eso SOL puede atender sesiones cortas concurrentes mientras conserva un
techo de 262K para una sesión larga. En los perfiles locales, la cantidad de
sesiones debe seguir parametrizada por `parallelSlots` y la memoria disponible;
no conviene elevarla globalmente sólo por lo que publica la guía.

### Prefill largo

La recomendación de `max-num-batched-tokens` y `long-prefill-token-threshold`
es específica de vLLM. SOL ya usa 8.192 y 4.096 respectivamente, y la prueba
comparativa no mostró una ventaja reproducible al bajar el umbral a 2.048.
No se trasladan esos flags a llama.cpp/NInfer porque allí no tienen la misma
semántica.

### P2P

P2P está activo, pero la topología es PCIe/PHB y no NVLink. En nuestros perfiles
por capas la diferencia medida fue aproximadamente 0,2%; el modo tensor split
no inicia de forma estable. Por eso se mantiene P2P en SOL y QWEN35-A3B, sin
promover tensor split.

### Muestreo

Se conserva el perfil conservador recomendado por Qwen:
`temperature=0.6`, `top_p=0.95`, `top_k=20`, `min_p=0.0`. No se aplica el
`min_p=0.75` mencionado en algunas variantes: en razonamiento produce
repetición y empeora el comportamiento agentivo.

## Perfiles externos no promovidos

Gemma-4-31B, Tess-4-27B y Qwen-AgentWorld-35B-A3B aparecen en la guía, pero no
hay artefacto local, prueba reproducible ni validación BCB/visión comparable en
este equipo. No se descargan ni se agregan a la tabla por ahora.

Las variantes Qwen3.8 FP8/NVFP4 y el tier DFlash de la guía mantienen caveats
de backend, memoria o estabilidad ya observados en pruebas anteriores. No son
un reemplazo seguro para SOL.

## Estado del sistema tras la revisión

- El artefacto AutoRound de SOL sigue intacto en `models/club-3090`.
- La imagen Docker de vLLM está disponible, pero no hay contenedores de
  inferencia ejecutándose en reposo.
- No se descargó ningún modelo adicional.
- Pruebas enfocadas existentes: `test_gguf_profiles` 58/58 y
  `test_system_profiles` 45/45.
- La suite completa conserva el cuelgue de integración conocido; no afecta a
  estas validaciones enfocadas.

## Decisión para la tabla

1. **SOL** sigue siendo default.
2. **QWEN35-A3B** sigue como segundo perfil para visión, contexto largo y
   concurrencia.
3. **NInfer Qwen3.6-35B-A3B** sigue experimental para una GPU, visión y
   concurrencia acotada.
4. No se agrega ni se elimina ningún perfil por esta auditoría.

