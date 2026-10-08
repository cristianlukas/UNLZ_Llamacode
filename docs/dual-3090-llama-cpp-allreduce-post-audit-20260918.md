# Auditoría del post sobre `internal`/NCCL en 2× RTX 3090 — 2026-09-18

## Conclusión

El post contiene una observación válida, pero no agrega una mejora pendiente para nuestro equipo: su resultado útil para dos GPU coincide con las pruebas A/B ya ejecutadas en Linux. El camino interno de reducción funciona mejor o igual que NCCL en nuestra ruta por capas; el tensor split no es estable en la build/modelo actual. No se cambia SOL ni se agrega un perfil nuevo.

La parte de tres GPU, `butterfly fallback` y el cuello de una tercera placa no aplica a nuestra máquina de dos RTX 3090. La conexión PCIe/P2P sí importa para una ruta tensorial, pero aquí el runtime estable sigue siendo `split-mode layer`.

## Qué afirma el post y qué es transferible

- Con dos GPU, el autor mide aproximadamente 72–74 tok/s con la reducción interna y ~64 tok/s con NCCL.
- Con tres GPU, su reducción interna cae a un fallback `butterfly`, mientras NCCL conserva ~65 tok/s.
- El post usa Windows/WDDM, otro build, Qwen3.8 Q8 con KV F16, MTP3 y un contexto efectivo corto durante decode; no es una comparación directa con SOL vLLM TP2/P2P.
- El aprendizaje transferible es probar `internal` y NCCL por separado, manteniendo fijo el modelo, contexto, batch, KV y MTP.

## Evidencia local ya registrada

La campaña local del 2026-09-07 usó dos RTX 3090, Linux, P2P PCIe activo, el mismo modelo y la misma receta por capas. También se construyó un binario sin NCCL para aislar la dependencia.

| Variante local | TG medio | TG P50 | PP | Estado |
| --- | ---: | ---: | ---: | --- |
| `split-mode layer`, P2P/NCCL activo | 60,75 tok/s | 63,19 tok/s | 269,97 tok/s | Estable |
| `split-mode layer`, binario sin NCCL | 60,73 tok/s | 62,88 tok/s | 276,10 tok/s | Estable; sin mejora |
| P2P real desactivado + sin NCCL | 60,61 tok/s | 62,84 tok/s | 280,70 tok/s | Estable; -0,8% frente al control |
| `NCCL_P2P_DISABLE=1` | 60,61 tok/s | 62,74 tok/s | 272,21 tok/s | Estable |
| `split-mode tensor`, P2P/NCCL activo | — | — | — | No inicia: `llama_params_fit`/`SPLIT_MODE_TENSOR` y luego `ncclAllReduce` |
| `split-mode tensor`, NCCL desactivado | — | — | — | No inicia por la misma incompatibilidad |

El binario actual contiene y enlaza `libnccl.so.2`, por lo que la ausencia de NCCL no explica la diferencia: la prueba aislada sin NCCL también fue funcional. El P2P del driver está activo en lectura y escritura entre ambas placas.

## Estado del modelo Q8 del post

El artefacto local comparable `Qwen3.8-27B-UD-Q8_K_XL.gguf` fue eliminado/movido a la papelera durante la limpieza de modelos. No se volvió a descargar porque:

1. sus resultados ya están registrados: ~41,3 tok/s a 8K y ~22,1 tok/s a 262K;
2. su BCB directo 8/8 no es un BCB agentivo equivalente al de SOL;
3. no superó la ruta SOL en velocidad ni tool-use;
4. descargarlo otra vez ocuparía aproximadamente 30 GB sin abrir una hipótesis nueva.

## Comparación vigente

| Perfil | Velocidad | Calidad/agentividad | Contexto | Decisión |
| --- | ---: | --- | --- | --- |
| SOL, vLLM TP2/P2P + MTP4 | 74 narrativo / 102 código tok/s | BCB 8/8, tool-use estable | 262K validado | Mantener default |
| llama.cpp Qwen3.8 Q8 | 41,3 @8K / 22,1 @262K | BCB directo 8/8; agente pendiente | 262K | No reactivar |
| llama.cpp layer + P2P/NCCL | ~60,75 tok/s | No sustituye la validación de SOL | 131K en la campaña | Mantener como backend experimental |

## Decisión para LlamaCode

- No cambiar la configuración actual de SOL.
- No reemplazar `split-mode layer` por `tensor`.
- No forzar NCCL como supuesta optimización: en dos GPU no mejoró el A/B local.
- No compilar un tercer camino ni descargar nuevamente Qwen3.8 Q8 sólo por este post.
- Mantener registrado el A/B para que futuras actualizaciones de llama.cpp puedan repetirlo con la misma matriz.

No quedaron servidores de prueba activos y no se modificó Windows.
