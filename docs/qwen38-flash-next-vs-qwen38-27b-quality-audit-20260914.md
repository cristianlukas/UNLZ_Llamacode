# Auditoría: Qwen3.8-27B frente a Qwen3.8-Flash-Next — 2026-09-14

## Alcance

El post compara de forma subjetiva Qwen3.8-27B con cuantizaciones menores de
Qwen3.8-Flash-Next y sugiere que Flash-Next puede ser más inteligente por token,
incluso en Q4 o Q3. El autor no publica BCB, HumanEval, una prueba de tool-use
ni una comparación ejecutada en el mismo hardware, runtime y harness de
LlamaCode. Sus cifras de velocidad tampoco separan siempre prefill de decode.

La afirmación es útil como hipótesis de calidad, pero no alcanza para promover
un perfil por encima de SOL.

## Evidencia local disponible

| Candidato | Resultado local comparable | Evaluación | Decisión |
| --- | --- | --- | --- |
| **SOL — Qwen3.8-27B** | ~74 tok/s narrativo / ~102 tok/s código | BCB 8/8, tool-use válido, 262K validado | **Default** |
| **BeeLlama KVarN5 — Flash-Next UD-Q4_K_XL** | ~36 tok/s decode y ~512 tok/s prefill a 131K | Smoke, JSON, Python, needle y `read_file` válidos; BCB completo pendiente | Experimental texto-only |
| **Flash-Next ASTRA — llama.cpp/cache experto** | ~16–41 tok/s según variante | Prefill/corrupción o repetición en las pruebas históricas; BCB no evaluable | No promover |
| **Flash-Next IQ4_XS/Q3/Q1** | No hay una campaña local válida con esos artefactos | Menor fidelidad publicada y sin evidencia superior de agentes | No descargar/promover |

La comparación local de calidad entre Qwen3.8-27B y Flash-Next tuvo empates en
la mayoría de los casos, pero no produjo una victoria estadísticamente útil de
Flash-Next. Además, el camino rápido de ASTRA llegó a producir `////`, números
truncados o texto repetitivo durante el prefill. Una cifra alta de tok/s de una
corrida aislada no se considera éxito si la salida no es utilizable.

## Cuantización y memoria

En esta máquina hay dos RTX 3090 (48 GB de VRAM) y aproximadamente 127 GB de
RAM. El modelo Flash-Next local de mayor fidelidad que entra razonablemente es
`UD-Q4_K_XL`, de unos 111 GB. La tabla de KLD publicada para esa familia muestra
que bajar a IQ4_XS, Q3 o IQ1 reduce fidelidad; no hay espacio suficiente en la
partición activa para descargar otra variante grande sin desplazar modelos.

El perfil BeeLlama probado mantiene `--kv-tail-tokens 0` y KVarN dentro de la
política de LlamaCode: no usa KV superior a Q8. La cola de precisión F16/BF16
que aparece en algunas recetas externas no es admisible para nuestros perfiles.

## Qué ideas del post sí sirven

1. **Separar inteligencia de velocidad.** Flash-Next puede ser atractivo para
   resolver tareas difíciles con menos tokens de razonamiento, aunque tarde más
   por token. Esto debe medirse con éxito de tarea y tiempo total, no sólo con
   tok/s.
2. **Comparar el mismo presupuesto de razonamiento.** Para una campaña futura
   conviene repetir SOL y Flash-Next con `low`, `medium` y `xhigh`, misma semilla,
   temperatura, límite de salida y prompts apareados.
3. **Medir prefill por separado.** En un agente, el contexto crece en cada
   vuelta; los ~512 tok/s de prefill de BeeLlama son una limitación importante
   frente al prefill de Qwen3.8-27B.
4. **Mantener Q4_K_XL como referencia de Flash-Next.** Las variantes IQ4_XS,
   Q3 y Q1 no tienen una ventaja local demostrada que justifique sacrificar
   fidelidad o consumir espacio de modelos.

## Qué no se implementa

- No se cambia el default de **SOL**.
- No se agrega IQ4_XS, Q3 o IQ1: no hay artefacto local validado ni espacio
  suficiente para una campaña que pudiera cambiar la decisión.
- No se activa MTP en Flash-Next por esta referencia: las combinaciones con
  cache de expertos ya mostraron inestabilidad y no hay aceptación estable
  medida en el perfil experimental.
- No se adopta Unsloth Studio: es un runtime externo y no forma parte de la
  integración de LlamaCode.

## Estado final

**SOL sigue siendo el perfil prioritario para coding y agentes.** BeeLlama
KVarN5 queda como la alternativa experimental de Flash-Next para texto y
contexto largo, con aproximadamente 36 tok/s a 131K y tool-use básico validado.
La hipótesis de que Flash-Next sea más inteligente a igual tarea queda abierta,
pero necesita una campaña BCB/HE y tool-use apareada antes de justificar un
cambio de default.

Pruebas de referencia:

- `docs/beellama-kvarn-qwen38-evaluation-20260913.md`
- `docs/qwen38-beellama-kvarn5-kvarn4-audit-20260914.md`
- `docs/qwen38-flash-next-lazy-mode-20260913.md`
- `docs/qwen38-flash-next-community-recipe-audit-20260914.md`
- `docs/qwen38-flash-next.md`
