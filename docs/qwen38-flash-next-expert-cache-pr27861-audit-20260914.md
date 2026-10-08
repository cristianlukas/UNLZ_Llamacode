# Auditoría: cache LRU de expertos de Qwen3.8 Flash-Next — 2026-09-14

## Resultado ejecutivo

La idea principal del reporte —reservar VRAM para un cache LRU de expertos
calientes— ya está implementada en nuestras builds experimentales de
`llama.cpp`. La PR #27861 forma parte de `flashnext-2x3090` y de la rama local
`llama.cpp-phase-prefill-e06`.

En nuestra máquina el cache aumenta mucho el rendimiento bruto de Flash-Next,
pero las recetas publicadas no pasan el requisito funcional: con Q4 y KV Q8 la
salida del smoke test queda corrupta o repetitiva. La medición del post usa
Q6, KV BF16, otra build y una plataforma distinta; no es comparable con SOL.

**Decisión:** no cambiar el default ni promover ASTRA. SOL sigue siendo el
perfil principal. No se descargó Q6 ni se añadió otra variante al dropdown.

## Qué reporta la publicación

El reporte usa dos RTX 3090, 188 GB de RAM DDR4, Qwen3.8 Flash-Next UD-Q6 y
261K de contexto. Afirma pasar de aproximadamente 17 a 25–29 tok/s en contexto
corto/medio y unos 17 tok/s a 131K mediante un cache LRU de expertos en VRAM.
También usa KV F16/BF16, `ubatch 512`, `batch 4096`, `--numa distribute`,
expertos restantes en RAM y `LLAMA_ATTN_ROT_DISABLE=1`.

La publicación aclara que Q8 KV, lazy PLE, n-gram y MTP no mejoraron de forma
general en su hardware. Sus números no incluyen BCB, HE0/HE20 ni tool-use.

## Pruebas locales reutilizadas

El artefacto local es Qwen3.8 Flash-Next UD-Q4_K_XL, no Q6, y está en el
volumen de modelos existente. Se respetó el límite del proyecto: ninguna
variante promovible usa pesos o KV superiores a Q8.

| Variante local | Resultado | Lectura |
| --- | --- | --- |
| Sin cache MoE, 16K | 16,45 tok/s | Control reproducible |
| Cache MoE 188, 16K | 36,04 tok/s | Mejora bruta de aproximadamente 2,2x |
| Receta adaptada, cache 150, KV Q8 | ~45,5 tok/s | Carga, pero devuelve `/` o `////` en el smoke de código |
| ASTRA actual, cache 188, KV Q8 | ~36,9 tok/s | Carga, pero repite el enunciado y no genera una respuesta válida |
| N-gram M=7 | ~36,97 tok/s | Estable, pero inferior al cache188 sin speculative |
| MTP + expert-cache | No estable | Acceso ilegal CUDA en la build probada |
| SOL | 74 tok/s narrativo / 102 tok/s código | BCB 8/8 y tool-use OK |

La conclusión importante es que el TPS del servidor no alcanza para declarar
una mejora de perfil si la respuesta no es utilizable por un agente.

## Qué ideas sí aplican

- Mantener `--moe-expert-cache` para la ruta experimental de Flash-Next.
- Priorizar `ubatch 512`: en nuestra prueba controlada superó a `ubatch 4096`
  (45,22 frente a 43,09 tok/s en el mismo escenario).
- Reservar la VRAM restante para expertos calientes y dejar el resto en RAM.
- Usar `--numa distribute` sólo como configuración compatible; esta PC expone
  un único nodo NUMA, por lo que `numactl --interleave=all` no aporta una
  mejora medible.
- Mantener `mmap` y evitar `load-mode none`, que ya mostró peor rendimiento o
  reservas de memoria excesivas.

## Qué no se promueve

- **Q6:** no está instalado y no hay espacio/razón para descargarlo sólo para
  replicar una medición no comparable.
- **KV F16/BF16:** queda fuera de la política de LlamaCode, cuyo máximo para
  perfiles promovibles es Q8.
- **MTP o n-gram combinados con el cache:** la ruta local no quedó estable y
  no superó al cache188 sin especulación.
- **Lazy PLE/SSD como default:** en nuestras pruebas produjo salida corrupta o
  una caída fuerte de rendimiento; requiere una nueva validación funcional.
- **Más de dos uploads de cache por paso:** no hay evidencia local de beneficio
  y el propio reporte indica saturación del enlace.

## Comparación con los perfiles actuales

| Perfil | Rendimiento local | Calidad / estabilidad | Contexto | Decisión |
| --- | ---: | --- | ---: | --- |
| SOL | 74 narrativo / 102 código | BCB 8/8, tool-use OK | 262K validado | Default |
| ASTRA con cache188 | ~36,9 tok/s bruto | Salida repetitiva no válida | 196K declarado | Experimental, no promover |
| Flash-Next del post | 25–29 tok/s en Q6 | Sin BCB ni tool-use comparable | 261K declarado | Referencia externa |

## Trabajo futuro

La única línea con potencial real es combinar el cache de expertos con
`phase-prefill`, porque la rama E06 ya mostró mejoras de prefill en contextos
largos. Antes de tocar ASTRA habría que repetirlo con KV Q8, comprobar salida
determinista, ejecutar BCB y probar al menos un ciclo completo de tool-call.
Hasta que esas pruebas pasen, el cache se conserva como capacidad experimental
y SOL permanece como default.
