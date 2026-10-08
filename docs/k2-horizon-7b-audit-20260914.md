# K2 Horizon 7B — auditoría local

Fecha: 2026-09-14  
Decisión: **no se agrega al dropdown ni reemplaza a SOL o MINI**. Queda como
candidato experimental de texto, con interés para probar reasoning/coding en
contextos cortos y como referencia de contexto largo.

## Qué propone

[K2-Horizon-7B](https://huggingface.co/IFM/K2-Horizon-7B-GGUF) es un modelo
denso de 7B con arquitectura `k2-horizon` y contexto nativo declarado de
524.288 tokens. Su tarjeta exige una versión de llama.cpp con soporte K2; no es
intercambiable con cualquier build del runtime actual. La tarjeta recomienda
razonamiento `high`, temperatura 1.0 y presupuestos de salida muy grandes para
las evaluaciones oficiales.

El modelo es **text-only**: la cuantización GGUF publicada no incluye
`mmproj`, por lo que no aporta una alternativa de visión a SOL, TERRA o
QWEN35-A3B. Las cuantizaciones Q4_K_M y Q8_0 usadas aquí provienen de
[abenzerps/K2-Horizon-7B-GGUF](https://huggingface.co/abenzerps/K2-Horizon-7B-GGUF),
que publica también sus checksums y confirma que son archivos de texto.

## Artefactos descargados

Todos quedaron en el directorio requerido:

`/media/cristian/7CFE1E0FFE1DC1F6/models/K2-Horizon-7B-GGUF/`

| Archivo | Tamaño aproximado | Uso |
|---|---:|---|
| `K2-Horizon-7B-Q4_K_M.gguf` | 5,3 GB | Prueba de velocidad/auxiliar |
| `K2-Horizon-7B-Q8_0.gguf` | 9,0 GB | Prueba de fidelidad/contexto |

No se descargó BF16: el proyecto mantiene el límite de pesos y KV en Q8 o
inferior.

## Backend y pruebas

Se compiló aparte el fork oficial de arquitectura K2,
[MBZUAI-IFM/llama.cpp `model/K2Horizon`](https://github.com/MBZUAI-IFM/llama.cpp/tree/model/K2Horizon),
commit `35999d1`, con CUDA para SM86. No se modificó el backend ni el build de
LlamaCode.

Hardware: 2× RTX 3090 de 24 GB, driver 595.71.05, CUDA 12.0.140. En todas las
pruebas se usó KV `q8_0/q8_0`; nunca se usó KV superior a Q8.

| Prueba | Resultado | Estado |
|---|---:|---|
| Q4_K_M, 8K, una 3090, razonamiento apagado | ~96–103 tok/s | Pasa |
| Q4_K_M, tool-call `read_file` | `finish_reason=tool_calls`, JSON válido | Pasa |
| Q4_K_M, BCB, razonamiento apagado | **1/8** | Insuficiente |
| Q4_K_M, BCB, `high`, budget 2048 | **2/8** | Insuficiente |
| Q8_0, 8K, una 3090, razonamiento apagado | ~66 tok/s | Pasa |
| Q8_0, prompt de 23K, una 3090 | prefill 2.653 tok/s; decode 42,8 tok/s | Pasa |
| Q8_0, 131K reservado, una 3090 | Carga; ~18.834 MiB usados | Pasa |
| Q8_0, 262K reservado, una 3090 | Falla al reservar KV: OOM | Esperable |
| Q8_0, 262K reservado, dos 3090 | Carga; ~16,5/16,0 GiB por GPU | Pasa |
| Q8_0, 23K, dos 3090 | prefill 5.202 tok/s; decode 54,7 tok/s | Pasa |
| Q8_0, BCB, `high`, budget 2048 | **0/8** en esta corrida | No promocionar |
| Q4_K_M, 262K dual, prompt de 23K | acceso ilegal CUDA durante el procesamiento | No estable |
| Visión | No hay `mmproj` | No aplica |

El BCB se ejecutó con el mismo bundle local de ocho ejercicios de LlamaCode.
La corrida de razonamiento alto además expuso dos dependencias de tests que
requieren compatibilidad con NumPy 1.x; aun descontando ese ruido, los errores
restantes fueron funcionales (archivos, CSV, fechas, orden y formato), no un
pase comparable al 8/8 de SOL.

## Comparación con la tabla actual

| Perfil | Velocidad local | Calidad/agentes | Contexto | Visión | Decisión |
|---|---:|---:|---:|---|---|
| SOL | 74 narrativo / 102 código | BCB 8/8; tool-use estable | 262K validado | Receta vLLM visual validada | Default |
| MINI | 248,90 tok/s histórico | BCB 1/8; auxiliar | 131K | No | Más rápido para subagentes |
| K2 Q4_K_M | ~100 tok/s corto; 2/8 con reasoning high | Tool-call válido, BCB insuficiente | 23K probado; Q4 largo a 262K inestable | No | Experimental, no agregar |
| K2 Q8_0 | ~66 tok/s corto; 54,7 tok/s a 23K dual | BCB 0/8 en esta corrida | 131K en una GPU; 262K dual de carga | No | Experimental, no agregar |

K2 puede ser interesante por su diseño denso y su contexto nativo, pero en
nuestro entorno no supera ningún criterio decisivo: Q4 no alcanza el caudal de
MINI ni la calidad de SOL; Q8 consume mucho más KV, cae con el contexto y no
mejora la validación agentiva. El contexto declarado de 512K no debe trasladarse
a la tabla operativa: con Q8, 262K requiere las dos GPU y con Q4 el prompt largo
produjo un fallo CUDA.

## Resultado operativo

- No se modificó SOL, MINI ni ningún perfil existente.
- No se agregó K2 al dropdown ni se lo marcó como default.
- No se le asignó visión: el artefacto es text-only.
- Se conservaron Q4_K_M y Q8_0 en `models/` para futuras pruebas controladas;
  no son dependencias de LlamaCode.
- El candidato queda documentado como **K2-HORIZON experimental**, no como
  reemplazo de perfiles actuales.
