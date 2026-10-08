# Auditoría de prefix cache y schemas MCP de SOL — 2026-09-18

## Objetivo

Comprobar si la recomendación de mantener estable el JSON de tools mejora el
tiempo de respuesta de SOL en LlamaCode, y comparar el umbral de prefill largo
`2048` del informe externo con el `4096` de la receta local.

Fuente externa: [KV cache para agentes vLLM](https://doug.sh/posts/vllm-kv-cache-agents/).
La documentación oficial de vLLM describe `--enable-prefix-caching`,
`--prefix-match-unit` y `--long-prefill-token-threshold` en la
[referencia de opciones de vLLM](https://docs.vllm.ai/en/v0.29.0/cli/bench/startup/).

## Estado previo de SOL

La receta local ya tenía las piezas principales:

- vLLM 0.27.1, TP2/P2P, Qwen3.8-27B AutoRound INT4, MTP4 y KV FP8.
- `--enable-prefix-caching`, `--prefix-match-unit=16` y
  `--enable-chunked-prefill`.
- `--max-num-batched-tokens=8192`.
- `--long-prefill-token-threshold=4096` por defecto.
- `--mamba-cache-mode=align`, que conserva el estado híbrido entre turnos.
- LlamaCode ya enviaba `cache_prompt=true` en completions y warmups.

La publicación no descubrió una bandera ausente. El hueco real estaba en el
wire del harness: el array de tools y las claves de un schema MCP podían llegar
en un orden distinto, invalidando el prefijo aunque fueran semánticamente
iguales.

## Prueba reproducible

Se restauró el checkpoint activo de SOL en:

`/media/cristian/7CFE1E0FFE1DC1F6/models/club-3090/qwen3.8-27b-autoround-int4`

La prueba se ejecutó en una instancia temporal vLLM 0.27.1 con dos RTX 3090,
TP2/P2P, `max_model_len=262144`, `max_num_seqs=2`, MTP4, KV FP8, prefix cache,
chunked prefill, mamba align y `max_num_batched_tokens=8192`. El prompt fijo
tenía 19.919 tokens, tres schemas de tools y dos turnos con sólo el sufijo de
tarea cambiado.

### Prefix cache y orden de tools

| Caso | TTFT | Tokens cacheados | Resultado |
| --- | ---: | ---: | --- |
| Primer request, tools ordenadas | 10,682 s | 0 | Prefill completo |
| Segundo request, mismo schema y orden | **1,302 s** | **17.776** | Hit de prefix cache |
| Tercer request, mismo contenido pero tools/claves reordenadas | 9,955 s | 0 adicional | Hit perdido |

El hit redujo el TTFT aproximadamente 88%. Las métricas de vLLM confirmaron
`prompt_tokens_by_source{source="local_cache_hit"}=17776` para el segundo
request.

### Umbral de prefill largo

| `long-prefill-token-threshold` | Primer request | Segundo request caliente | Decisión |
| ---: | ---: | ---: | --- |
| 2048 | 10,682 s | 1,302 s | Funciona; no supera 4096 de forma reproducible |
| **4096** | **10,125 s** | **1,238 s** | **Conservar como default local** |

La diferencia de una sola corrida no alcanza para atribuir una ventaja aislada
al 4096. Se conserva porque el barrido local anterior documentado en el compose
mostró mejor comportamiento de TTFT y concurrencia con dos sesiones largas;
2048 queda disponible como override. `8192` sigue siendo el tamaño máximo de
batch, no el umbral.

## Cambio implementado en LlamaCode

Antes de construir el payload OpenAI de completions y warmups, el harness ahora:

1. ordena el array de tools por `function.name`;
2. ordena recursivamente las claves de los objetos JSON;
3. preserva el orden de todos los arrays internos, porque `enum`, `required` y
   otros arrays pueden tener significado operacional;
4. usa la misma canonicalización en warmup y en turnos normales.

Esto no cambia nombres, argumentos ni capacidades de las tools; sólo elimina
variaciones de representación que inutilizan el cache. Se agregó una regresión
en `test_agent_wire` que comprueba tanto el orden de tools como el orden de
claves anidadas.

## Decisión operativa

- SOL sigue siendo el default y conserva sus métricas de calidad, BCB 8/8,
  tool-use y velocidad; el prefix cache mejora TTFT, no el puntaje BCB.
- Se mantiene `4096` como umbral y `8192` como `max-num-batched-tokens`.
- El orden determinista de tools queda activo para todos los payloads del
  harness, incluido MCP, porque es una propiedad de transporte segura.
- La instancia temporal vLLM fue detenida; no queda ningún servicio vLLM
  ejecutándose automáticamente.

## Validación

- Build Release Linux: correcto.
- `test_agent_wire`: **52/52**.
- Suite Linux: compiló todos los targets; la ejecución general volvió a quedar
  detenida en `test_agent_tools`, el cuelgue de integración ya conocido. No se
  atribuye este bloqueo al cambio: el test unitario específico pasó completo.

## Revisión del reporte sobre invalidaciones innecesarias — 2026-09-18

El reporte nuevo describe el mismo problema desde el lado del harness: cambiar
un schema MCP, reordenar sus claves, agregar timestamps o reconstruir el system
prompt hace que el prefijo sea distinto aunque la intención sea la misma.
LlamaCode ya cubre ese caso en el transporte: `buildToolSchemas()` aplica la
canonicalización antes de cada completion y del warmup, ordenando las tools por
nombre y las claves JSON recursivamente, pero conservando el orden semántico de
los arrays (`required`, `enum`, etc.).

No toda invalidación es un bug. Es esperable que se invalide desde el punto que
cambia cuando se modifica el cwd, el modo de aprobación, las directivas, la
memoria del proyecto, una imagen reciente, la compactación o la superficie de
tools. Esas variaciones cambian realmente el prefijo que recibe el modelo. El
harness evita, en cambio, invalidaciones causadas sólo por el orden de JSON y
mantiene estable el prefijo de fases cuando cambia `plan`/`ejecución`.

La prueba unitaria de wire ya verifica warmup, canonicalización de schemas,
prefijo estable y poda de capturas. La prueba vLLM previa sigue siendo la
validación end-to-end: 17.776 tokens reutilizados y TTFT aproximado de 10,1 s a
1,2 s. No se agrega otra capa de caché ni se modifica SOL; repetir el post no
abriría una hipótesis nueva.
