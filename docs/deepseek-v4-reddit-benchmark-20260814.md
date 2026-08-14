# DeepSeek V4 Flash — experimento de offload CPU-MoE

Fecha: 2026-08-14. Hardware detectado: 2× RTX 3090 (48 GB VRAM) y 128 GB
RAM. Backend: llama.cpp oficial CUDA, con los perfiles DeepSeek de
`assets/system_profiles.json`.

## Alcance real de esta tanda

La receta de Reddit no se pudo reproducir literalmente: requiere el fork
leloch, un GGUF Q8, tres RTX 3090 y la variable
`GGML_CUDA_MOE_CACHE_RESERVE_MB`. Esta máquina tiene dos placas, y los GGUF
disponibles son IQ3_S y el híbrido antirez Q2/Q4. La matriz local sí contiene
el equivalente funcional: CPU-MoE, DSpark, reparto de expertos, KV configurable
y duplicados de perfil.

El grupo antirez tiene exactamente diez variantes. El screening histórico se
guardó como “HumanEval (1 ítems)”, pero cada resultado contiene `0/5`; por eso
no se usa como score de calidad ni como selección válida. Sus TPS y tiempos se
conservan como screening operativo. La única validación comparable de calidad
disponible es HumanEval/20.

## Ranking de resultados HumanEval/20

Ordenado por score y luego por TPS. `llama.cpp oficial CUDA` es el backend
registrado por los perfiles; el binario exigido por estos perfiles es b10228 o
posterior. El tiempo es pared total, incluyendo carga, tools y reparaciones.

| Puesto | GGUF | Perfil | Backend | TPS | Tiempo total | HumanEval/20 | Estado |
|---:|---|---|---|---:|---:|---:|---|
| 1 | antirez Q2/Q4 | `[bench antirez stress] 131k · B4096 · U1024 · KV q4_0` | llama.cpp oficial CUDA | 8,29 | 1338,7 s | **20/20** | válido |
| 2 | antirez Q2/Q4 | `deepseek v4-antirez-10-8-26` | llama.cpp oficial CUDA | 8,20 | 1572,7 s | **20/20** | válido |
| 3 | antirez Q2/Q4 | `[bench antirez prefill] 32k · B8192 · U2048 · KV q4_0` | llama.cpp oficial CUDA | 7,80 | 2238,2 s | 1/20 | inválido por timeout/fallo de calidad |
| — | IQ3_S | 10 duplicados del grupo ULTRA-Q | llama.cpp oficial CUDA | — | — | — | sin corrida HE/20 comparable |

El ganador válido del grupo antirez fue el duplicado de 131k: mejoró el tiempo
total un 14,9% frente al perfil base, con una diferencia de 0,09 TPS. El
prefill agresivo no resultó competitivo en calidad.

## Screening HumanEval/0 del grupo antirez

El nombre histórico “HumanEval/0” corresponde a una corrida que debía ser de
un ítem, pero el artefacto conserva cinco tareas y puntúa `0/5` en todos los
perfiles. Por eso el ranking siguiente es sólo de velocidad de screening y no
de calidad.

| Ranking screening | Perfil | TPS | Tiempo total | HE/0 registrado |
|---:|---|---:|---:|---:|
| 1 | `[bench antirez prefill] 32k · B8192 · U2048 · KV q4_0` | — | 47,1 s | 0/5 |
| 2 | `[bench antirez stress] 131k · B4096 · U1024 · KV q4_0` | — | 49,7 s | 0/5 |
| 3 | `[bench antirez stress] 32k · B8192 · U1024 · KV q4_0` | — | 58,9 s | 0/5 |
| 4 | `[bench antirez stress] 64k · B4096 · U1024 · KV q8_0` | — | 63,5 s | 0/5 |
| 5 | `[bench antirez] 32k · B4096 · U512 · KV q4_0` | — | 70,3 s | 0/5 |
| 6 | `deepseek v4-antirez-10-8-26` | — | 71,4 s | 0/5 |
| 7 | `[bench antirez] 64k · B4096 · U512 · KV q4_0` | — | 72,9 s | 0/5 |
| 8 | `[bench antirez stress] 32k · B4096 · U512 · KV f16` | — | 74,8 s | 0/5 |
| 9 | `[bench antirez] 16k · B2048 · U256 · KV q4_0` | — | 83,6 s | 0/5 |
| 10 | `[bench antirez] 32k · B2048 · U256 · KV q4_0` | — | 88,2 s | 0/5 |

El campo `avgTps` de esos artefactos quedó en cero; no se puede reconstruir un
TPS comparable sin volver a ejecutar. Los tiempos tampoco deben compararse con
los 8,29/8,20 de HumanEval/20: son artefactos de pasadas distintas y el
benchmark corto no quedó validado.

## Conclusión

El hallazgo local es consistente con la publicación sólo en la dirección de
la mejora: mover expertos a RAM y reservar VRAM puede mejorar el throughput en
un modelo que no entra completo. En nuestra configuración no hay evidencia de
24 TPS ni se pudo atribuir una mejora a `GGML_CUDA_MOE_CACHE_RESERVE_MB` o al
fork leloch. El resultado reproducible de LlamaCode es 8,29 TPS y 20/20 para
el perfil antirez 131k.

Para cerrar exactamente el protocolo pedido faltan: corregir el pack HE/0 a un
solo ítem, materializar diez duplicados IQ3_S, ejecutar HE/0 válido, seleccionar
tres por GGUF y correr seis HE/20 adicionales. Los artefactos originales están
en `C:\Users\cristian\AppData\Local\LlamaCode\LlamaCode\benchmark-runs\`, en
particular la tanda `HumanEval_20_tems__20260812_230646`.
