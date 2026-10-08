# Auditoría: Flash-Next con 12 GB de VRAM, RAM limitada y SSD — 2026-09-18

## Resultado ejecutivo

El post propone ejecutar Qwen3.8-Flash-Next con una GPU de 12 GB, una parte de
los expertos en RAM/SSD y una caché de expertos. La idea es técnicamente
válida para hacer entrar el modelo, pero no es una mejora para los perfiles
prioritarios de LlamaCode. La caché de expertos ya existe en nuestra rama
experimental y fue medida; el resultado útil de rendimiento vino acompañado
de salida corrupta o repetitiva.

No se cambia SOL, ASTRA ni el dropdown. No se descargó otra copia del modelo:
el GGUF Flash-Next grande y el IQ1_S fueron retirados durante la limpieza de
modelos; en el volumen principal sólo queda el `mmproj-BF16.gguf` de
aproximadamente 0,9 GB.

## Qué afirma el post y qué es transferible

| Idea del post | Aplicabilidad local | Estado |
| --- | --- | --- |
| Caché LRU de expertos calientes | Ya implementada en la rama experimental Flash-Next | Probada |
| Expertos fríos en SSD mediante `mmap`/lazy | Reduce presión de RAM/VRAM, pero añade lecturas aleatorias | Probada con límites |
| `threads=6` en lugar de `threads=12` | Puede ayudar cuando el CPU compite con el streaming de expertos; no es universal | No se repite sin el artefacto |
| 20–24 tok/s en una GPU de 12 GB | No comparable con nuestras 3090 ni con SOL; depende de Q4, RAM, SSD y del fork | Referencia externa |
| ~50 tok/s de prefill a contexto largo | Sería demasiado lento para un agente que reinyecta herramientas/contexto | No es un objetivo útil para SOL |

La publicación enlaza un fork con cambios de caché de expertos, no una bandera
portable de llama.cpp oficial. El checkout local `llama.cpp-lazy-28136` contiene
`--lazy-mode`, `--load-mode`, `--cache-ram` y `--n-cpu-moe`, pero no dejó un
binario CUDA ejecutable ni un artefacto Flash-Next completo para repetir el
benchmark de `threads=6` de forma limpia.

## Pruebas locales ya realizadas que cubren la propuesta

| Variante | Resultado local | Lectura |
| --- | ---: | --- |
| Flash-Next Q4 sin caché MoE, 16K | 16,45 tok/s | Control reproducible |
| Flash-Next Q4 con caché MoE 188, 16K | 36,04 tok/s | +2,2x bruto, pero smoke inválido |
| Caché 150, receta del post, KV Q8 | ~45,5 tok/s | Salida `/` o `////`; no usable |
| ASTRA Q4, caché 188, KV Q8 | ~36,9 tok/s | Repite el enunciado; no usable como agente |
| `lazy-mode on-direct`, Flash-Next | ~7,54 tok/s | Salida válida, pero 49% peor que el control comparable |
| IQ1_S + `lazy-mode on`, 262K | 57,98 PP / 25,62 TG | Smoke Python válido; BCB completo y visión pendientes |
| IQ1_S + head MTP Q8, warm 8K | 41,63–58,49 TG | Aceptación 48/48; experimental, no BCB completo |
| SOL, Qwen3.8-27B AutoRound | 74 narrativo / 102 código | BCB 8/8 y tool-use OK |

Las pruebas del IQ1_S también comprobaron que un head MTP Q4 incompatible falla
por tensores `hc_head_*`; el head compartido Q8 sí carga. Esto no repara la
menor fidelidad del quant ni proporciona visión validada.

## Sobre bajar `threads`

Las campañas históricas de Flash-Next usaron `threads=16` y
`threads-batch=44`, no `threads=6/12`. Cambiar sólo el número de hilos podría
alterar el equilibrio CPU↔SSD, pero no corrige los fallos observados del
runtime, del cache MoE ni del `mmproj`. No hay evidencia local de que `threads=6`
supere a SOL en PP, TG, BCB o tool-use.

No se ejecutó un A/B nuevo porque faltan simultáneamente el modelo principal y
un binario CUDA del fork; redescargar ~75–115 GB para repetir una medición de
un post sin BCB sería un gasto de almacenamiento sin valor decisorio. Si se
reactiva esa línea, el protocolo correcto es `threads=6/8/12/16`, con el mismo
Q4, contexto 8K/64K/131K, caché MoE fija, lazy off/on y smoke funcional antes
de comparar TPS.

## Decisión para LlamaCode

- La caché de expertos queda documentada como capacidad experimental de
  Flash-Next, no como default.
- `mmap` se mantiene; `load-mode none` y `lazy-mode on` no se convierten en
  defaults porque ya produjeron corrupción o peor rendimiento.
- No se habilita un perfil de 12 GB: nuestro hardware tiene 2× RTX 3090 y la
  solución útil para coding es SOL, con calidad y tool-use validados.
- El Ryzen 9 9950X3D ayuda al prefill y al loader, pero no elimina el coste de
  mover expertos por RAM/SSD ni valida la calidad del quant.
- SOL permanece sin cambios y sin servidores persistentes.

## Evidencia relacionada

- [Auditoría de caché LRU de expertos](qwen38-flash-next-expert-cache-pr27861-audit-20260914.md)
- [Auditoría de lazy-mode y SSD](qwen38-flash-next-lazy-mode-20260913.md)
- [Auditoría IQ1_S y MTP Q8](qwen38-flash-next-iq1s-3090-audit-20260915.md)
- [Auditoría de la receta comunitaria Q4](qwen38-flash-next-community-recipe-audit-20260914.md)
