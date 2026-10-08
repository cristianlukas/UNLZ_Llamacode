# Qwen3.8 Flash-Next IQ1_S + MTP Q4 en la PC dual 3090 — auditoría

Fecha: 2026-09-15  
Equipo: Ubuntu, 2× RTX 3090, P2P habilitado, Ryzen 9 9950X3D, ~123 GiB de RAM  
Runner: `llama-server` CUDA de la rama Flash-Next usada por ASTRA  
Modelo: `Qwen3.8-Flash-Next-UD-IQ1_S` (72,5 GB)  
Head descargado originalmente: `Qwen3.8-Flash-Next-MTP-Q4_K_M.gguf` (2,62 GB),
incompatible con el contrato `qwen4exp` de este runner. La prueba corregida usa el
head compartido `mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf`, que sí contiene los
tensores `hc_head_*` requeridos y respeta el máximo Q8 de LlamaCode. Se dejó una
copia con hash `5ff54097…fa96e6` en
`/media/cristian/7CFE1E0FFE1DC1F6/models/Qwen3.8-Flash-Next-IQ1_S/MTP/`.

## Qué se podía trasladar del post

El post mezcla dos cosas distintas: un quant IQ1_S de 1 bit y un head MTP Q4
emparejado, ejecutados en una Intel Arc B70 con SYCL y parches específicos. La
Arc, SYCL y esos parches no son aplicables a nuestras RTX 3090/CUDA. Sí se
aislaron y probaron las ideas portables: KV Q8, `lazy-mode on`, caché de
expertos y `n_max=4`.

## Resultados locales

Todos los tests usaron una sola sesión, Flash Attention, `split-mode layer`,
P2P disponible, KV K/V `q8_0`, caché de expertos 188 y el mismo binario.

| Variante | Contexto | PP | TG | Salida | Resultado |
|---|---:|---:|---:|---|---|
| IQ1_S, lazy off, sin MTP | 8K | 38,21 | 22,03 | Python válido | Control |
| IQ1_S, lazy off, sin MTP | 32K | 55,06 | 25,64 | Python válido | Funciona |
| IQ1_S, lazy off, sin MTP | 64K | 58,74 | 24,56 | Python válido | Funciona |
| IQ1_S, lazy on, sin MTP | 8K | 58,21 | 25,39 | Python válido | Mejora de PP/TG frente al control |
| IQ1_S, lazy on, sin MTP | 131K | 59,71 | 24,08 | Python válido | Funciona |
| IQ1_S, lazy on, sin MTP | 196K | 58,04 | 24,56 | Python válido | Funciona |
| IQ1_S, lazy on, sin MTP | 262K | 57,98 | 25,62 | Python válido | Techo reproducido |

El smoke sin MTP no es un BCB: una micro-suite diagnóstica de seis tareas obtuvo 4/6
con criterio estricto. La aritmética modular quedó razonada correctamente pero
se truncó antes del marcador final; la función Python fue correcta pero el
matcher del test quedó demasiado estricto. No hay base para convertir esto en
un BCB promocionable.

## MTP: causa del fallo y reparación

El head Q4 no carga con el trunk IQ1_S ni con el Q4 actual. El runner termina
con:

```text
check_tensor_dims: tensor 'blk.48.nextn.hc_head_norm.weight' not found
failed to load draft model
```

La causa no era la ausencia total de `nextn/Qwen4Exp`: la build local ya
incluye esa arquitectura. El head Q4 descargado es de otro contrato y omite
`blk.48.nextn.hc_head_norm/down/up`. El head compartido Q8 de ASTRA sí los
declara, por lo que funciona como reemplazo compatible sin superar Q8.

### Resultados de la receta reparada

Todas las pruebas usan IQ1_S, KV K/V `q8_0`, `lazy-mode on`, caché de expertos
188, `split-mode layer`, P2P y `n_max=2`.

| Variante | Contexto/prueba | PP | TG | Aceptación | Resultado |
|---|---:|---:|---:|---:|---|
| IQ1_S + MTP, head Q8 compartido | 8K, primera corrida | 30,81 | 26,98 | 16/16 | Válido |
| IQ1_S + MTP, head Q8 compartido | 8K, 3 corridas warm | 26,95–39,00 | **41,63–58,49** | **48/48** | Válido |
| IQ1_S sin MTP, control | 8K, 3 corridas | 34,41–45,96 | 39,98–50,11 | — | Válido |
| IQ1_S + MTP, head Q8 compartido | 24.031 tokens, ctx configurado 131K | **244,06** | **28,12** | 17/18 = **94,44%** | Válido; `LONG_MTP_OK` |
| IQ1_S + MTP, tool-use | tool `read_file` | 81,96 | 29,68 | 18/18 | `read_file({path: "README.md"})` válido |
| IQ1_S + MTP, BCB parcial | `BigCodeBench/870` | **104,44** | **50,42** | 282/287 = **98,26%** | Tests del ítem: 1/1 |

El promedio TG de las tres corridas warm fue 49,09 tok/s con MTP frente a
45,05 tok/s sin MTP: **+8,97%** en esta prueba corta y concreta. No se debe
extrapolar a BCB completo ni a sesiones multi-turno largas. El artefacto con
todos los números está en
`artifacts/validation-20260915/flashnext-iq1-mtp-q8head.json`.

Una corrida BCB más amplia sin MTP pasó el primer ítem, pero el runner sufrió
un cierre CUDA durante el segundo; se clasifica como infraestructura y no como
`1/8`. Por eso esta campaña sólo informa el ítem MTP ejecutado y no inventa un
score BCB completo.

### Diagnóstico y corrección del cierre entre tareas

El historial del runner conserva la firma `CUDA illegal memory access`, pero no
el kernel ni el código CUDA exacto. Repetí los dos primeros ítems del pack
(`870 → 509`) directamente contra el mismo `llama-server`, sin el agente: el
servidor permaneció vivo con y sin MTP. La reproducción MTP usó el head Q8
compartido y obtuvo 98,81/49,72 tok/s en 870 y 105,43/63,52 tok/s en 509
(prefill/decode), con aceptación 294/334 y 531/574. El control sin MTP obtuvo
133,17/41,10 y 129,16/44,76. Esto descarta que el segundo ítem sea por sí solo
un input que rompa CUDA.

La causa más probable queda acotada al límite de turno del runner agentivo:
una cancelación o cierre de HTTP podía solaparse con la liberación del slot/KV
CUDA y el siguiente prompt entraba durante ese *unwind*. Es una hipótesis de
ciclo de vida, no una afirmación de que se haya capturado un kernel ilegal en
esta reproducción directa.

Se aplicó una defensa en LlamaCode:

- BigCodeBench ya no usa aceptación temprana; avanza sólo después de
  `turnFinished` natural para no abortar una tarea multi-turno.
- Se agrega un drenaje de 250 ms entre turnos antes de enviar la tarea BCB
  siguiente.
- El workspace registra `benchmark_early_accept_disabled` para que la decisión
  sea auditable.

La prueba directa está registrada en
`artifacts/validation-20260915/flashnext-iq1-bcb-transition-repro.json`.
El puntaje BCB agentivo completo todavía requiere una corrida headless posterior
con el binario recompilado; no se transforma el cierre anterior en un `1/8`.

## Comparación con nuestros perfiles

| Candidato | Evidencia local | Decisión |
|---|---|---|
| **SOL** | 74 tok/s narrativo, 102 tok/s código, BCB 8/8, tool-use y visión validados | Sigue siendo el default |
| **ASTRA Q4** | 16–41 TG históricos; el control fresco dio ~41 TG pero salida `////` | No es agente confiable |
| **ASTRA IQ1_S sin MTP** | 24–26 TG y 58–60 PP hasta 262K; salida Python válida en smoke | Experimental; no hay BCB completo |
| **ASTRA IQ1_S + MTP Q8 compartido** | 41,63–58,49 TG warm a 8K; 28,12 TG con 24K de prompt; aceptación 94–100% en las pruebas realizadas | Reparado y reproducible; experimental, no reemplaza SOL |
| IQ1_S + MTP Q4 | No carga: faltan `hc_head_*` | Rechazado; no usar |

La ruta IQ1_S tampoco aporta visión validada: el post no proporciona un
`mmproj` compatible y la visión de Flash-Next ya falló en nuestras pruebas
previas por abort de `mtmd`/salida repetitiva. El Ryzen 9 9950X3D ayuda a la
carga y al prefill, pero no corrige la incompatibilidad del head MTP ni la
menor fidelidad del quant IQ1_S.

## Decisión para LlamaCode

- No se modifica SOL ni el orden de los perfiles principales.
- No se agrega IQ1_S al dropdown prioritario: es inferior en fidelidad y no
  tiene BCB/tool-use/visión equivalentes.
- Se conserva el modelo en `/media/cristian/7CFE1E0FFE1DC1F6/models` como
  artefacto experimental reproducible de contexto largo.
- `lazy-mode on` queda documentado como válido para IQ1_S, pero no se copia a
  ASTRA Q4: en ese quant ya produjo `////`.
- No hace falta compilar otro backport para esta combinación: la reparación es
  usar el head compartido Q8 correcto. Sí hace falta completar HE0/HE20/BCB
  antes de promoverla.

## Artefactos

- [IQ1_S sin MTP](../artifacts/validation-20260915/flashnext-iq1-no-mtp.json)
- [IQ1_S lazy on 8K](../artifacts/validation-20260915/flashnext-iq1-lazy.json)
- [IQ1_S lazy on 131K/196K](../artifacts/validation-20260915/flashnext-iq1-lazy-long.json)
- [IQ1_S lazy on 262K](../artifacts/validation-20260915/flashnext-iq1-lazy-262k.json)
- [IQ1_S + MTP Q4, fallo de carga](../artifacts/validation-20260915/flashnext-iq1-mtp.json)
- [IQ1_S + MTP Q8 compartido, reparación validada](../artifacts/validation-20260915/flashnext-iq1-mtp-q8head.json)
- [Control ASTRA Q4](../artifacts/validation-20260915/astra-q4-baseline.json)
