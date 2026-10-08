# SOL + DFlash2 — auditoría local

Fecha: 2026-09-18. Hardware: 2× RTX 3090, TP2, P2P/NCCL, vLLM 0.27.1 en
Docker. El target es exactamente el AutoRound INT4 usado por SOL. El drafter
se descargó en el Disco D:

```text
/media/cristian/Disco local/Models/llamacpp/Qwen3.8-27B-DFlash2-W4A16/model.safetensors
1.28 GB
```

Se aplicó el backport local de vLLM PR#52816 y se probaron dos recetas: DFlash2
con BF16/Flash-Attention y DFlash2 con FP8 E4M3/FlashInfer. Las instancias se
levantaron en un puerto aislado y se eliminaron al terminar; no se cambió el
perfil activo ni se dejó un contenedor arrancando.

## Resultados reproducidos

| Receta | Contexto configurado | Narrativa | Código | Prefill probado | Aceptación observada | Resultado |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| SOL canónico | 262K | 74 tok/s | **102 tok/s** | 2.287 tok/s @10K; 1.500 @90K | — | BCB 8/8, tool-use estable |
| Control local, BF16/Flash-Attention, sin drafter | 204.8K | 48–50 tok/s | 50 tok/s | ~2K: TTFT 1,51 s | — | Arranque y tool-call OK |
| DFlash2 n=7, BF16/Flash-Attention | 204.8K | **109 tok/s** | **144 tok/s** | ~2K: TTFT 1,52 s | 31% en la primera batería; 42–60% en otras | Arranca y genera; JSON/xgrammar falla |
| DFlash2 n=7, FP8 E4M3/FlashInfer | **262K** | **103–108 tok/s** | **124–142 tok/s** | ~900 tokens: TTFT 0,63 s | 45–57% en las baterías cortas | Arranca; JSON/xgrammar falla |

Las cifras locales son requests cortos y medianos, no una repetición del BCB8.
El resultado externo de 218 tok/s de código no se reprodujo: en nuestra
máquina el máximo observado fue 144 tok/s con BF16 y 142 tok/s con FP8 en la
batería comparable. La diferencia puede depender de revisión, prompt,
sampling, aceptación, compilación y métricas de ventana.

## Validaciones adicionales

- El drafter cargó como `DFlash2DraftModel` y completó CUDA Graph capture con
  n=7 en Ampere.
- La receta BF16 llegó a un smoke de contexto largo alrededor de 131K sin OOM
  ni cierre del runner; la variante FP8 arrancó con KV pool de 406.093 tokens y
  máximo de 262.144 por request. También completó un smoke largo cercano a
  100K con HTTP 200.
- Tool-use OpenAI: una llamada `get_project_status` válida, con argumentos `{}`
  y `finish_reason=tool_calls`.
- JSON estructurado: la respuesta visible fue JSON correcto, pero el runner
  registró `backend_xgrammar.py: Failed to advance FSM ... tokens 271` durante
  la misma prueba. No se considera tool-use estructurado estable.
- Visión: el `mm_processor` procesó una imagen PNG y devolvió una descripción
  correcta con thinking desactivado. Es una validación funcional, no todavía
  un 4/4 de visión del harness.
- El smoke greedy de código produjo la misma función en dos ejecuciones
  consecutivas, pero no prueba equivalencia token a token contra el servidor
  SOL sin drafter.

## Lectura para la tabla de perfiles

| Perfil | Calidad agentiva | Visión | Contexto | Decisión |
| --- | --- | --- | --- | --- |
| SOL | **BCB 8/8 y tool-use estable** | Validada 4/4 | **262K validado** | Mantener default |
| SOL-DFlash2-BF16 | BCB8/HE20 pendientes; xgrammar inestable | Funcional, pendiente 4/4 | 131K smoke; 204.8K configurado | Experimental, no default |
| SOL-DFlash2-FP8 | BCB8/HE20 pendientes; xgrammar inestable | Funcional, pendiente 4/4 | **262K configurado; smoke ~100K** | Experimental separado |

Conclusión: DFlash2 sí es utilizable localmente y mejora el decode corto
aproximadamente 2,2–2,9× frente al control BF16, pero no demostró todavía
superar a SOL como agente. FP8 elimina en esta build el bloqueo de arranque
observado anteriormente y conserva 262K configurados; no elimina el problema
de corrección estructurada. No se reemplaza SOL ni se modifica el dropdown.

## Próxima compuerta de promoción

Ejecutar con el harness oficial, en la misma revisión y sampling: HE0 → HE20 →
BCB8, tool-use multi-turno, JSON/xgrammar repetido, equivalencia greedy con y
sin thinking, y una prueba de contexto 8K/32K/131K/262K. La promoción exige
BCB8, tool-use estable y ausencia del error xgrammar además de una ventaja
medida de TG; un resultado de decode aislado no alcanza.
