# Qwen3.8 GSQ-RCO IQ3_S + DFlash2 Q2 — auditoría local

Fecha: 2026-09-18  
Equipo: Ubuntu, Ryzen 9 9950X3D, 2× RTX 3090 24 GB, P2P disponible  
Decisión: **agregar como perfil experimental opt-in; no reemplazar SOL ni hacerlo default**.

## Candidato y fuentes

- Target local: `/media/cristian/7CFE1E0FFE1DC1F6/models/Qwen3.8-27B-GSQ-RCO-IQ3_S/Qwen3.8-27B-GSQ-RCO-IQ3_S-mtp.gguf` (~12,1 GB).
- `mmproj` local: `/media/cristian/7CFE1E0FFE1DC1F6/models/Qwen3.8-27B-GSQ-RCO-IQ3_S/mmproj-Qwen3.8-27B-BF16.gguf` (~889 MiB).
- Drafter descargado: `/media/cristian/7CFE1E0FFE1DC1F6/models/Qwen3.8-27B-DFlash2-Q2_K_S-MIX/Qwen3.8-27B-DFlash2-Q2_K_S-MIX.gguf` (~536 MiB).
- Fuente del drafter: [HermiHg/Qwen3.8-27B-DFlash2-Q2_K_S-MIX-GGUF](https://huggingface.co/HermiHg/Qwen3.8-27B-DFlash2-Q2_K_S-MIX-GGUF).
- Fuente del target: [ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF](https://huggingface.co/ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF).

El model card del drafter indica que no es un modelo autónomo, requiere una
build con soporte DFlash2 (PR #27342), y mide `n-max=3` como el mejor punto de
memoria/aceptación para la variante Q2_K_S-MIX. El Q2 ocupa 535–561 MiB según
la metadata publicada. La especulación es lossless respecto del target: cambia
el coste, no la distribución de salida.

## Runtime y protocolo

Se usó el binario local:

```text
/media/cristian/Disco local/LlamaCode-cache/llamAmpere-build/bin/llama-server
```

La comparación mantuvo el target, el prompt, `parallel=1`, 2 GPU con reparto
por capas/P2P, Flash Attention, sampling conservador, batch 2048/ubatch 512 y
contexto configurado en 81.920. Se probaron KV target Q8/Q8 y K8/V4, además
de KV de draft K8/V4. La política Q8 se respetó; el `mmproj` BF16 se considera
el auxiliar multimodal permitido.

## Resultados

### Texto corto, mismo prompt y 128 tokens

| Variante | PP | TG | Aceptación | Resultado |
|---|---:|---:|---:|---|
| GSQ-RCO sin speculative, KV Q8/Q8 | 221,77 | 42,48 | — | Python válido |
| DFlash2 Q2, `n-max=3`, target KV Q8/Q8 | 183,61 | **67,02** | **85/123 = 69,1%** | Python válido |
| DFlash2 Q2, `n-max=5`, target KV Q8/Q8 | 194,08 | 68,44 en primera corrida; 58,77 con prefijo warm | 93/168 = 55,4%; 87/197 = 44,2% | No mejora estable frente a n=3 |
| DFlash2 Q2, `n-max=3`, target KV K8/V4 | warm-up variable | 60,30 en texto | 83/130 = 63,8% | Python válido |

La ganancia limpia de `n-max=3` frente al control autoregresivo fue de
aproximadamente **+57,8% TG** en la primera A/B. La segunda corrida DFlash fue
65,45 TG con KV Q8/Q8 y 60,30 TG con K8/V4; el prefijo cacheado cambia el coste
del prefill y no debe mezclarse con la primera corrida.

### Tool-use y visión

- Tool-use: correcto. El servidor devolvió `finish_reason=tool_calls` y
  `add({"a":2,"b":3})`; la corrida observó 61 aceptados de 84 tokens draft
  (~72,6%). La primera solicitud usó un `tool_choice` objeto no soportado por
  este binario, que fue advertido y normalizado; la función igualmente fue
  emitida correctamente.
- Visión: el `mmproj` BF16 cargó en GPU con DFlash activo. Sobre una imagen
  local, con `reasoning_effort=none`, describió correctamente la imagen y su
  color dominante: 51,61 TG, 79/150 tokens aceptados (~52,7%). La primera
  prueba con presupuesto corto gastó la salida en razonamiento y terminó
  truncada; al separar razonamiento de respuesta la ruta fue válida.

### Contexto

La carga textual larga terminó sin crash ni OOM. En una solicitud de 9.592
tokens, la receta K8/V4 midió 102,18 PP, 17,67 TG y 19/33 aceptados (~57,6%).
En la misma carga, el prefill se degradó de 359,8 PP a 118,6 PP en 8.192
tokens y a 102,4 PP cerca de 9.588 tokens. Una prueba posterior a ~16.426
tokens fue cancelada de forma controlada por su coste creciente; no se registra
como resultado de calidad.

Esto confirma que el drafter no elimina el coste de contexto largo del target:
la mejora es clara en decode corto, pero no convierte GSQ-RCO en una ruta más
rápida que SOL para sesiones largas.

## Calidad y decisión

No se asigna BCB8 a esta campaña: el target GSQ-RCO no completó aún la cadena
oficial LlamaCode `HE0 → HE20 → BCB` con el harness LC-H1. El tool-call y la
salida Python son smoke tests, no equivalen a BCB8. Tampoco se repitió el BCB
histórico de SOL, que sigue siendo la referencia válida de 8/8.

| Perfil | Evidencia local | Decisión |
|---|---|---|
| SOL | 74 narrativo / 102 código, BCB 8/8, tool-use estable | Default |
| GSQ-RCO IQ3_S + DFlash2 Q2 | 60–67 TG corto, visión y tool-use funcionales, contexto 81.920 cargable, BCB pendiente | Experimental opt-in |
| GSQ-RCO IQ3_S sin DFlash | 39,6 TG sin MTP; ~52,5 TG con MTP histórico | Control experimental |

El perfil DFlash2 se agrega sólo para explorar la combinación de menor VRAM y
decode corto. No reemplaza SOL: queda por debajo en calidad demostrada, no tiene
BCB8, su ganancia cae con el contexto y depende de un binario DFlash2 específico.
No se dejó ningún servidor ejecutándose y la VRAM volvió a estado idle.

## No repetir

No repetir estas variantes sin cambiar el objetivo o el runtime:

1. `n-max=5` con este Q2: ya mostró aceptación inestable y no superó de forma
   consistente a `n-max=3`.
2. DFlash2 vLLM + KV FP8 sobre SOL: ya produjo `CUDA device-side assert` en
   prefill y es una ruta distinta a este GGUF.
3. DFlash2 sobre Flash-Next/Astra Q4: no es compatible arquitectónicamente.

La siguiente validación pendiente, si se busca promoción, es ejecutar HE0,
HE20 y BCB8 completos con el harness oficial usando exactamente este perfil y
su binario DFlash2; hasta entonces el score queda como `pendiente`, no como 0.

## Revalidación A/B adicional — 2026-09-18

Se repitió la comparación en el mismo binario `llamAmpere` local, con el mismo
target, `split-mode layer`, 2× RTX 3090, KV target Q8/KV draft K8/V4,
sampling conservador, semilla 42 y `max_tokens=128`. El control fue el mismo
GSQ-RCO sin drafter; no se comparó contra otro modelo en la misma corrida.

| Escenario | GSQ-RCO control | GSQ-RCO + DFlash2 Q2 n=3 | Lectura |
|---|---:|---:|---|
| Prompt corto, 35 tokens | 191,67 PP / 40,75 TG | 21,36 PP / **67,65 TG** | +66,0% TG; el primer PP DFlash fue cold y no es representativo |
| Prompt ~7.957 tokens | 133,91 PP / 14,19 TG | **128,12 PP / 24,99 TG** | -4,3% PP / +76,1% TG |
| Tool-call `add(2,3)` | 504,53 PP / 39,58 TG | 512,52 PP / **77,50 TG** | tool-call correcto en ambos; +95,8% TG |
| Visión + `mmproj` | — | **151,86 PP / 52,10 TG** | Descripción correcta; 31/57 aceptados (54,4%) |

El primer prompt corto DFlash incluyó la inicialización efectiva de la ruta
especulativa y su PP cayó a 21,36; la medición anterior de la receta ya tenía
183,61 PP en la misma clase de prompt. Por eso la cifra para contexto largo y
la tabla histórica son las referencias de PP, mientras que la corrida nueva
sirve principalmente para confirmar TG, tool-use y visión. La caída a 24,99 TG
con ~8K tokens confirma que la especulación no elimina el coste del contexto.
