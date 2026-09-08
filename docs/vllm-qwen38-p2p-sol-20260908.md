# SOL Linux: Qwen3.8-27B vLLM TP=2 con P2P

Evaluación realizada el 8 de septiembre de 2026 en esta PC (2 x RTX 3090,
PCIe 4.0 x8 por placa, Ubuntu y driver P2P habilitado). Windows conserva el
backend llama.cpp anterior; el cambio de SOL se aplica mediante
`platformBackendIds.linux`.

## Configuración promovida

- Pesos Frozenlock Qwen3.8-27B AutoRound INT4 W4A8.
- vLLM 0.27.1, tensor parallel 2, NCCL y custom all-reduce P2P.
- MTP4, KV FP8 E4M3 (8 bits), contexto máximo 262.144 y una secuencia.
- `temperature=0.6`, `top_p=0.95`, `top_k=20`, `min_p=0.0`.
- Endpoint local compatible OpenAI en `127.0.0.1:8113`, alias `local`.

El contenedor queda con política `unless-stopped`, por lo que LlamaCode puede
conectarse al perfil SOL después de reiniciar Docker o el equipo.

## Resultados locales

| Variante | Narrativa decode | Código decode | Prefill 10K | Prefill 90K | Decode a 90K | Resultado |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| TP2 P2P, sin MTP | 50,11 tok/s | 49,91 tok/s | 2.355,75 tok/s | 1.543,30 tok/s | 44,34 tok/s | Estable |
| TP2 P2P, MTP4 | **74,03 tok/s** | **102,36 tok/s** | 2.287,11 tok/s | 1.499,71 tok/s | **52,95 tok/s** | Promovido |
| TP2 sin P2P, MTP4 | No medible | No medible | No medible | No medible | No medible | `device-side assert` al primer request |

MTP4 mejora el decode aproximadamente 47,7% en narrativa y 105,1% en código,
con una baja de 3-4% en prefill. La aceptación observada fue 84-100%. El perfil
usó 23.381 MiB en GPU0 y 22.181 MiB en GPU1.

## Calidad y compatibilidad

- Verificación completa del servidor: aprobada, incluida visión 4/4 y tool calls.
- HumanEval 20: 20/20 después de una reparación (19/20 inicial).
- BigCodeBench Hard: 8/8 después de reparación; 32 tool calls.
- Perfil de agente: `agent-maximo`, razonamiento `medium`, presupuesto 4.096.
- Quantización: pesos INT4 y KV FP8 de 8 bits; cumple el límite máximo Q8.

## Lectura del A/B P2P

En llama.cpp con reparto por capas, P2P sólo había cambiado 60,61 a 60,75 tok/s,
dentro del ruido. En tensor parallel de vLLM sí es parte del camino crítico. La
receta P2P aprobó toda la campaña; al forzar P2P apagado, el worker CUDA cayó en
el primer request. Por ello el resultado demuestra estabilidad funcional y no
permite atribuir un porcentaje aislado de velocidad a P2P.

## Decisión

SOL pasa de llama.cpp Q4/MTP3 131K (63,94 tok/s histórico) a este backend Linux:
mejor decode narrativo, mucho mejor código, el doble de contexto, visión y BCB
8/8. El backend anterior sigue intacto para Windows y como fallback manual.
