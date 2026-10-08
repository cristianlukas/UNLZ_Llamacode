# Auditoría Flash-Next IQ4_XS/IQ1_S contra SOL

## Objetivo

Comparar en la máquina local los artefactos `UD-IQ4_XS` e `UD-IQ1_S` de
Qwen3.8-Flash-Next contra el perfil SOL, sin mezclar cifras externas con
resultados propios ni cambiar el default antes de validar calidad y estabilidad.

Los artefactos se descargan en el Disco D, que tiene espacio suficiente:

- `/media/cristian/Disco local/Models/Qwen3.8-Flash-Next-UD-IQ4_XS`
- `/media/cristian/Disco local/Models/Qwen3.8-Flash-Next-UD-IQ1_S`

## Control

SOL se medirá con su configuración vigente: Qwen3.8-27B AutoRound INT4,
vLLM TP2/P2P, MTP4, KV FP8, muestreo conservador y el harness de LlamaCode.
La referencia conocida es 74 tok/s narrativo, 102 tok/s de código, BCB 8/8,
HE20 20/20, visión 4/4 y contexto operativo de 262K.

## Matriz de pruebas

Cada variante se ejecuta sólo después de que la anterior cargue y pase un smoke
test. Se registran versión del runtime, commit/build, flags, modelo, KV, contexto,
VRAM/RAM pico, PP, TG, TTFT, errores y aceptación especulativa.

1. Carga y generación corta a 8K, 32K, 131K, 196K y 262K.
2. Prefill largo y decode sostenido con el mismo prompt de código y el mismo
   prompt narrativo usados para SOL.
3. MTP desactivado como base; luego MTP compatible disponible para el artefacto,
   comparando aceptación, TG y memoria. No se asumirá que el MTP de otra
   cuantización sea intercambiable.
4. KV Q8 como base Ampere; KV Q4 sólo como experimento de capacidad y separado
   de la comparación de calidad.
5. `lazy-mode`/mmap y caché de expertos únicamente en combinaciones que carguen
   sin salida corrupta ni degradación sostenida.
6. Visión con la misma imagen, primero redimensionada a 768 px y luego original;
   se anotan GPU/CPU para el `mmproj`, PP, TTFT y resultado semántico.
7. Harness: BCB8, HE0, HE20, tool-use de tres turnos, Python y recuperación de
   contexto al final de 131K/196K/262K.
8. Concurrencia: dos sesiones y una tercera pequeña sólo si el perfil mantiene
   memoria y resultados correctos.

## Criterio de promoción

Una variante sólo puede reemplazar a SOL si mantiene generación correcta, tool-use
reproducible, BCB8/8 y HE20 completos, y mejora de forma clara el caso de uso que
justifica el cambio. Si sólo mejora contexto, consumo o velocidad, queda como
perfil experimental con esa ventaja acotada.

## Línea separada: SOL + DFlash2

DFlash2 se evalúa sólo como drafter del mismo SOL AutoRound INT4; no se cambia
el checkpoint base. El drafter W4A16 de `syvai/Qwen3.8-27B-DFlash2-W4A16` se
descarga en el Disco D y se usa con el backport local de vLLM PR #52816.

La matriz mínima es:

- control SOL autoregresivo y control SOL+MTP4;
- SOL+DFlash2 con `n=3`, `n=5` y `n=7`;
- KV FP8/Q8, que es la política normal, y KV BF16 sólo como diagnóstico de
  estabilidad porque la ruta DFlash2/FLASH_ATTN de Ampere puede exigirlo;
- prefill de 32, 512, 2.048 y 8.192 tokens, seguido de decode corto y una
  sesión multi-turno larga;
- aceptación draft, PP, TG, TTFT, VRAM, errores CUDA, equivalencia greedy,
  tool-use/JSON y BCB8 bajo el mismo harness.

El intento anterior de SOL+DFlash2 con KV FP8 produjo `CUDA device-side assert`
durante un prefill de 512 tokens. Por eso no se considera resuelto hasta que la
misma combinación pase varios prefills y el harness. Aunque BF16 pueda evitar
ese crash, supera el límite operativo Q8 y no puede convertirse en default sin
una variante estable con KV cuantizada. La campaña se mantiene opt-in y no
altera SOL mientras esté pendiente.

## Resultados previos que no se deben repetir como si fueran nuevos

IQ1_S con `lazy-mode on` ya fue observado alrededor de 24--26 TG hasta 262K y
con PP cercano a 58--60 tok/s, con micro-suite parcial; su BCB completo, visión
funcional y MTP compatible todavía no estaban cerrados. El MTP que fallaba por
faltantes `nextn` no se considerará válido para IQ1_S sin identificar un head
compatible y repetir la prueba completa.

## Estado inicial

Al comenzar esta auditoría, las descargas exactas de IQ4_XS (~98 GB) e IQ1_S
(~72,5 GB) están activas en D. Ningún perfil se promueve ni se elimina por
resultados de terceros antes de completar la matriz local.
