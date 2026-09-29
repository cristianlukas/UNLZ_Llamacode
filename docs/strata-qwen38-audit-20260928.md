# Strata + Qwen3.8-Flash-Next — auditoría para LlamaCode

Fecha inicial: 2026-09-28; pruebas locales: 2026-09-29
Fuente primaria: [Niko1221/Strata](https://github.com/Niko1221/Strata), checkout
revisado `c1e903310f211e6630780c3bd2038778c071c68d`; artefactos y resultados del
modelo: [ISTA-DASLab GSQ-RCO GGUF](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF).  
Decisión: **no cambiar perfiles ni el harness predeterminado. La prueba local
funcionó en el equipo, pero la calidad BCB8 de Strata Q2_0 quedó en 1/8**.

## Qué aporta

Strata es un runtime CUDA de una GPU para Qwen3.8-Flash-Next, no un quant ni una
mejora que se pueda activar con flags de llama.cpp. Combina caché adaptativa de
expertos en VRAM, cómputo CPU de expertos ausentes, tabla n-grama en SSD con
lectura mapeada, prefill por lotes y MTP especulativo. Publica una API compatible
con OpenAI y Anthropic, soporte de imágenes y conexión de servidores MCP. El
servidor procesa una solicitud por vez; el MCP descrito en su documentación está
integrado en la interfaz de chat, y no está documentado como una superficie MCP
que LlamaCode pueda consumir como cliente.

El repositorio recomienda Q2_0 o IQ2_XS según calidad/memoria. El GGUF GSQ-RCO
consta de dos shards: Q2_0 ocupa 37,6 GB residentes y 28,8 GB de tabla n-grama
accesible por mmap; descarga total aproximada 66,4 GB, más MTP, KV y hasta 0,91
GB de `mmproj`. Strata también ofrece un modelo Coder podado a la mitad de los
expertos, IQ1_M, que reduce el shard residente a 29,6 GB. Es una distribución
distinta de nuestro Flash-Next UD-Q2_K_XL y no se deben intercambiar sus
resultados.

## Equipo y prueba local de Strata — 2026-09-29

Se clonó Strata en la caché ext4 de Ubuntu (`/home/cristian/.cache/strata-eval-20260929`); los GGUF, tabla PLE, packs y pesos MTP quedaron fuera de LlamaCode, en el volumen de modelos. `python3 setup.py --check` completó. El instalador compiló el engine para SM86, descargó Q2_0 (66,4 GB), generó el pack de expertos y el MTP. No se descargó `mmproj` y la visión quedó desactivada.

| Recurso | Resultado |
|---|---|
| GPU | 2× RTX 3090 de 24 GB, compute capability 8.6 |
| Runtime Strata | Selecciona una GPU; permite elegir índice, no sumar las dos |
| RAM / CPU | 124 GB; Ryzen 9 9950X3D con AVX-512 |
| Driver | 610.57.04, suficiente para el runtime CUDA 13 requerido |
| Almacenamiento | 474 GB libres al iniciar; modelo y datos experimentales quedaron en el volumen de modelos |
| Preflight `setup.py --check` | Correcto; todos los tamaños que enumera caben en RAM |

La campaña se corrió cuando la GPU 1 quedó libre. Strata usó una sola RTX 3090; al cargar tenía el pool de expertos de 31,64 GiB en RAM bloqueada, caché de expertos de 17,10 GiB en VRAM y 367 MiB de VRAM libres. Configuración: contexto 131072, KV int8 con 32768 tokens residentes, MTP de 4 tokens y visión desactivada. El servidor OpenAI-compatible se aisló en `127.0.0.1:8311` y se detuvo al acabar.

### Resultados

| Prueba | Resultado | Lectura |
|---|---:|---|
| `/health`, `/v1/models` | correcto | API inicia y anuncia el modelo |
| `llamacode_local_coding_smoke` | 3/3 checks | Acepta los checks básicos de función Python, escritura atómica y plan incremental; es sólo un smoke, no tests ejecutables de código generado |
| Tool calling OpenAI | correcto | Emitió `lookup_ticket({"ticket_id":"LC-42"})`; tras recibir una respuesta simulada, continuó el turno con estado y responsable correctos |
| Streaming corto | TTFT 0,319 s; 180 tokens en 2,165 s | Streaming funciona; una sola medición |
| Aguja en contexto | 3/3 | Recuperó el valor a 8,4K (12,1 s), 31,7K (23,7 s) y 109,9K (92,1 s) tokens. En esos casos el prefill medido fue 698,5, 1345,7 y 1194 tok/s |
| BigCodeBench-Hard-8 local | 1/8 | Sólo pasó el ID 870. Los demás fallaron tests funcionales; no es un resultado apto para promover el modelo |

El BCB usa los mismos ocho IDs locales que la comparación directa de UD-Q2_K_XL (20/20 HE, 8/8 BCB), pero aquí cambia la cuantización (GSQ-RCO Q2_0), el runtime y la máquina efectiva (una GPU). No es A/B controlado; la diferencia de 1/8 sí es una señal negativa que requiere resolver antes de proponer Strata para coding agentivo. El smoke corto y la prueba de aguja no compensan ese resultado.

Con el `max_tokens` corto y el pensamiento por defecto habilitado, las dos primeras peticiones del smoke terminaron en `reasoning_content` sin texto visible. Al enviar `chat_template_kwargs.enable_thinking=false`, las respuestas quedaron en `content` y el smoke pasó. El cliente debe fijar explícitamente el modo de razonamiento y un presupuesto suficiente; la compatibilidad de protocolo no garantiza resultados útiles con cualquier presupuesto.

Los detalles reproducibles están en `artifacts/strata-evaluation-20260929/summary.json`, con resultados por tarea en `bcb8.json`, `coding-smoke.json` y `needle.json`.

## Evidencia local previa relacionada — no repetir

| Prueba existente | Resultado registrado | Relación con Strata |
|---|---|---|
| Flash-Next UD-Q2_K_XL, barrido `n-cpu-moe` y contexto, 2×3090 | A 16–32K: ~56–57 tok/s con `n-cpu-moe=4`; a 64–256K requiere más expertos en CPU y cae a ~31 tok/s con `n-cpu-moe=40`. Barridos adicionales encontraron ~53,7 tok/s/128K con `n-cpu-moe=8`, y 47,1 tok/s/256K con `n-cpu-moe=12`, ambos sin calidad agentiva completa. | Mide otra cuantización y llama.cpp; no mide Strata. No repetir esos barridos buscando demostrar Strata. Ver `artifacts/qwen38-q2-context-matrix-20260923.json` y `artifacts/qwen38-q2-ncpu-moe-sweep-20260923.json`. |
| Flash-Next UD-Q2_K_XL vs SOL | HE20 20/20 y BCB8 8/8 en evaluación directa; ~30,3 tok/s media BCB con ese runtime y receta. Falta harness agentivo completo. | Control de calidad relacionado, no velocidad comparable 1:1 ni cuantización Strata. Ver `artifacts/qwen38-q2-vs-sol-20260923.json`. |
| GSQ-RCO IQ3_S + DFlash2 Q2 | 60–67 tok/s corto, ~25 tok/s a ~8K, tool-use e imagen funcionales; HE20 cancelado a 5/20 por latencia, BCB bloqueado. | El artefacto GSQ-RCO ya existe localmente, pero es Qwen3.8-27B y usa DFlash2; no es el GSQ-RCO Flash-Next de Strata. Ver `docs/qwen38-gsq-rco-dflash2-q2-audit-20260918.md`. |
| Flash-Next con caché MoE/lazy mode | Hubo resultados de TPS más altos, pero con salida repetitiva/corrupta o rendimiento peor; no válidos para uso agentivo. | La hipótesis de mantener expertos calientes y descargar expertos fríos ya se probó parcialmente. Strata cambia kernels, prefill, MTP y reparto CPU/GPU, por lo que merece una prueba aparte, no una repetición del mismo A/B de flags. Ver `docs/qwen38-flash-next-12gb-ssd-audit-20260918.md`. |

Referencias locales: `docs/qwen38-flash-next-gsq-rco-audit-20260915.md`,
`docs/qwen38-gsq-rco-dflash2-q2-audit-20260918.md`,
`docs/benchmark-results.md` y los artefactos JSON indicados arriba.

## Lectura para LlamaCode

- **Modelo:** no se puede reemplazar SOL con los números publicados ni con esta
  corrida: aunque el throughput y el contexto largo funcionaron, Strata Q2_0
  pasó sólo 1/8 BCB-Hard. La fuente
  GSQ-RCO informa LiveCodeBench v6 81,14 para Q2_0, frente a 87,43 del modelo
  BF16 base; el Coder informa resultados SWE-bench/LiveCodeBench del autor, no
  BCB8 ni una corrida del harness LC-H1. Es evidencia útil para seleccionar
  candidatos, no validación de nuestra carga agentiva.
- **Harness:** la API OpenAI-compatible completó tool-call, streaming y un ciclo
  de herramienta de dos turnos en prueba manual. Falta la prueba del cliente y
  las sesiones durables de LlamaCode, cancelación y preflight; sólo admite una
  solicitud a la vez. Puede servir como candidato a proveedor externo de
  laboratorio, no está validado para producción. La interfaz MCP de Strata no
  reemplaza el motor de Computer Use de LlamaCode.
- **Computer Use:** no se encontró una capacidad de desktop-control en el repo;
  sólo API, imágenes y herramientas de servidores MCP configurables. No aporta
  una mejora demostrada a `computer-usage` ni justifica cambios allí.
- **Ingí-Charla:** sin relación con STT, VAD, turn detection o TTS locales; no hay
  cambio sugerido.
- **Perfiles/runtime:** no copiar cuantización, argumentos ni presupuesto de
  contexto desde Strata a los perfiles `llama.cpp`. Si se valida, la integración
  correspondería a un backend/API externo dedicado; Strata puede elegir una GPU,
  pero no dispone de la ejecución multi-GPU que usa SOL.

## Siguiente paso posible

Si se quiere seguir con un backend externo, usar el checkout y los datos aislados
ya preparados. No volver a correr el preflight ni los barridos previos del Q2.
Primero repetir BCB8 con la receta, engine y runner exactos del control; luego
probar la integración cliente real (cancelación, sesiones durables, error por
límite de contexto). Sólo tras una calidad agentiva sin regresiones medir
IQ2_XS o el modelo Coder IQ1_M. No editar perfiles para habilitarlo aún.

La cuantización GSQ-RCO ya tiene resultados publicados en tareas de razonamiento
y código, pero la evidencia local de Strata Q2_0 en coding agentivo fue débil.
No se editó `assets/system_profiles.json` ni se cambió el perfil activo. Para
Ingí-Charla no aporta STT/VAD/TTS; para Computer Use no aporta control de
escritorio. No hay cambios de producto justificados por estos resultados.
