# Strata + Qwen3.8-Flash-Next — auditoría para LlamaCode

Fecha: 2026-09-28  
Fuente primaria: [Niko1221/Strata](https://github.com/Niko1221/Strata), checkout
revisado `c1e903310f211e6630780c3bd2038778c071c68d`; artefactos y resultados del
modelo: [ISTA-DASLab GSQ-RCO GGUF](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF).  
Decisión: **no cambiar perfiles ni el harness predeterminado; mantener Strata
como candidato para una prueba comparativa cuando haya una GPU libre**.

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

## Compatibilidad comprobada aquí

Se clonó el repositorio en `/media/cristian/Disco local/strata-eval-20260928`,
fuera del checkout de LlamaCode. `python3 setup.py --check` completó y detectó:

| Recurso | Resultado |
|---|---|
| GPU | 2× RTX 3090 de 24 GB, compute capability 8.6 |
| Runtime Strata | Selecciona una GPU; permite elegir índice, no sumar las dos |
| RAM / CPU | 124 GB; Ryzen 9 9950X3D con AVX-512 |
| Driver | 610.57.04, suficiente para el runtime CUDA 13 requerido |
| Almacenamiento | 527 GB libres en el volumen de modelos al revisar |
| Preflight `setup.py --check` | Correcto; todos los tamaños que enumera caben en RAM |

No se descargaron modelos ni se inició el servidor. A las 23:42 UTC ambas GPU
tenían procesos `llama-server` activos, aproximadamente 10 GB ocupados cada una
y actividad de cómputo alta. El benchmark de Strata reserva memoria y calibra la
caché de expertos; ejecutarlo a la vez habría contaminado las medidas e
interferido con los servidores que ya estaban corriendo. Este bloqueo es sólo
para la prueba de rendimiento/calidad, no para la compatibilidad del equipo.

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

- **Modelo:** no se puede reemplazar SOL con los números publicados. La fuente
  GSQ-RCO informa LiveCodeBench v6 81,14 para Q2_0, frente a 87,43 del modelo
  BF16 base; el Coder informa resultados SWE-bench/LiveCodeBench del autor, no
  BCB8 ni una corrida del harness LC-H1. Es evidencia útil para seleccionar
  candidatos, no validación de nuestra carga agentiva.
- **Harness:** Strata puede funcionar como proveedor OpenAI-compatible de un
  perfil externo si supera tool-call, streaming, cancelación y ciclos de tools
  reales. Su única solicitud concurrente y su caché conversacional propia deben
  medirse con las sesiones durables y el preflight de contexto de LlamaCode. La
  interfaz MCP de Strata no reemplaza el motor de Computer Use de LlamaCode.
- **Computer Use:** no se encontró una capacidad de desktop-control en el repo;
  sólo API, imágenes y herramientas de servidores MCP configurables. No aporta
  una mejora demostrada a `computer-usage` ni justifica cambios allí.
- **Ingí-Charla:** sin relación con STT, VAD, turn detection o TTS locales; no hay
  cambio sugerido.
- **Perfiles/runtime:** no copiar cuantización, argumentos ni presupuesto de
  contexto desde Strata a los perfiles `llama.cpp`. Si se valida, la integración
  correspondería a un backend/API externo dedicado; Strata puede elegir una GPU,
  pero no dispone de la ejecución multi-GPU que usa SOL.

## Próxima campaña si se libera una RTX 3090

Usar checkout aislado ya preparado. Los modelos y datos deben quedar en el
volumen de modelos, no en el repo. No volver a correr el preflight ni los
barridos del Q2 local. Protocolo propuesto:

1. Instalar Strata Q2_0 y `mmproj` off; contexto 32K, KV Q8. Fijar `--gpu 0` o
   `--gpu 1` según cuál quede libre. Guardar versión del motor, argumentos,
   hash del repo, uso de RAM/VRAM y logs.
2. Medir en idénticos prompts y longitudes que el perfil SOL: generación corta,
   HE0/HE20/BCB8 y prompt largo 8K/32K/128K. Comparar latencia TTFT, PP, TG,
   calidad y uso de memoria; no comparar TPS de prompt corto con prefill de
   contexto largo.
3. Probar una conversación de varias vueltas, tool-call OpenAI-compatible,
   streaming, cancelación, error por límite de contexto e imagen si `mmproj`
   está habilitado. Verificar compatibilidad concreta con el cliente/harness,
   no inferirla sólo de la etiqueta OpenAI-compatible.
4. Sólo si Q2_0 completa la cadena de calidad sin regresiones, medir IQ2_XS o
   Coder IQ1_M (elegir según si la prioridad es charla general o coding), y
   entonces evaluar backend externo opt-in. Mantener SOL como control.

La cuantización GSQ-RCO ya tiene resultados publicados en tareas de razonamiento
y código, pero la campaña local de Strata queda **pendiente por GPU ocupada**.
No se editó `assets/system_profiles.json` ni se cambió el perfil activo: falta
evidencia local de superioridad.
