# Qwen3.8 / DeepSeek: auditoría de muestreo y agente

## Resultado

La discusión externa aporta una recomendación útil para LlamaCode, pero no un
nuevo modelo que supere las mediciones existentes: mantener `top-p 0.95`,
`top-k 20`, `min-p 0.0`, penalizaciones neutras y un presupuesto explícito de
razonamiento. `temperature 0` sirve para aislar problemas de cuantización o de
sampler; no es el modo diario de un agente.

SOL ya tenía `top-p 0.95`, `top-k 20`, `min-p 0.0`, `repeat-penalty 1.0`,
`presence-penalty 0.0`, esfuerzo `medium` y presupuesto 4096. Se cambió sólo
su temperatura de lanzamiento de `1.0` a `0.6`, alineándola con la política de
sampling conservador para coding. ASTRA conserva `1.0` porque es el perfil
experimental de razonamiento/contexto largo y no debe mezclarse con la
configuración de coding de SOL.

## Evidencia local

La comparación de perfiles sigue siendo la ya validada:

| Perfil | Evidencia local | Lectura |
|---|---|---|
| SOL / Qwen3.8 | BCB 8/8; aproximadamente 74 tok/s narrativo y 102 tok/s código | Sigue siendo el default de coding |
| GALACTA / DeepSeek V4 IQ3_S | BCB 8/8 histórico; aproximadamente 9,65 tok/s | Calidad alta, pero demasiado lento para reemplazar SOL |
| ASTRA / Qwen Flash-Next | BCB no válido; aproximadamente 16–41 tok/s según contexto | Experimental, no comparable como agente principal |
| BeeLlama Q8/KVarN5 | Tool-call y JSON válidos; KVarN5 mantuvo el needle a 131K | La ruta KV experimental es usable, pero no cambia el ranking |

Se ejecutó un smoke A/B local sobre Qwen3.8 UD-Q4 con BeeLlama v0.4.7,
`q8_0` en K/V, dos RTX 3090, cuatro prompts (respuesta breve, JSON exacto,
JSON restringido y código) y estas condiciones:

| Condición | Resultado |
|---|---|
| `temperature 0`, `top-p 0.95` | 4/4 respuestas limpias; JSON exacto válido |
| `temperature 0.6`, `top-p 0.95` | 4/4 limpias; una respuesta convirtió el booleano en cadena |
| `temperature 0.6`, `top-p 1.0` | 4/4 limpias; sin caracteres CJK en esta muestra |

La muestra no reproduce el fallo de caracteres chinos reportado para DeepSeek.
Tampoco permite atribuirlo a `top-p`, porque el backend, el modelo, la
cuantización y el prompt deben mantenerse idénticos para una conclusión causal.

## Decisión

- Se actualizó el lanzamiento de SOL a `temperature 0.6`; no cambia su modelo,
  KV, MTP, P2P ni contexto.
- No se promovió ASTRA ni se reordenaron GALACTA/DeepSeek: las pruebas previas
  siguen siendo más sólidas que los reportes anecdóticos del hilo.
- No se descargó ningún modelo nuevo: el enlace/reporte no aporta un artefacto
  local reproducible superior a SOL.
- El modo greedy queda recomendado para diagnósticos de corrupción, tool-call o
  cuantización; no como default de interacción.

## Artefactos relacionados

- `artifacts/beellama-quality-q8-20260913.json`
- `artifacts/beellama-quality-kvarn5-20260913.json`
- `artifacts/beellama-tool-kvarn5-20260913.json`
- `docs/beellama-kvarn-qwen38-evaluation-20260913.md`
