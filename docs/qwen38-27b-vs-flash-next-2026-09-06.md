# Qwen3.8-27B vs Qwen3.8-Flash-Next — Ubuntu

## Alcance

Comparación local solicitada a partir del prompt público de trenes del hilo
“Qwen3.8 27b vs qwen 3.8-flash-next”. No es una reproducción exacta del
hardware del hilo: aquí se usaron dos RTX 3090, PCIe/P2P expuesto como PHB y
NVLink inactivo según `nvidia-smi`.

Los modelos disponibles tampoco son los del post: se comparó el Q4_K_M local
de 27B con el UD-Q4_K_XL local de Flash-Next.

## Configuración

| Variante | Modelo | GPU/RAM | Contexto | B/U | KV | Especulación |
|---|---|---|---:|---:|---|---|
| 27B base | `Qwen3.8-27B-Q4_K_M.gguf` | 1× RTX 3090, residente | 32K | 512/512 | Q8/Q8 | ninguna |
| 27B MTP | mismo modelo + `mtp-Qwen3.8-27B-Q4_0.gguf` | 2× RTX 3090, draft en GPU1 | 32K | 512/512 | Q8/Q8 | MTP, 3 tokens |
| Flash-Next | `Qwen3.8-Flash-Next-UD-Q4_K_XL` | 2× RTX 3090 + expertos en host | 32K | 512/512 | F16/F16 | expert cache 188 |

Receta común: Flash Attention, `parallel=1`, temperatura 0, y el prompt exacto
del hilo. Las cifras de generación se toman de `print_timing` de llama-server.

## Resultados

| Variante | Prefill | Decode | Aceptación MTP | Resultado del prompt |
|---|---:|---:|---:|---|
| 27B base | 789.19 tok/s en frío | 35.41–38.02 tok/s | — | No llegó a las tres líneas; razonamiento repetitivo/truncado |
| 27B + MTP | 556.56 tok/s | **73.75 tok/s** | **83.7%** | No llegó a las tres líneas dentro de 512 tokens |
| Flash-Next + cache 188 | **54.05 tok/s** | **41.31 tok/s** | — | No llegó a las tres líneas; salida numérica/textual corrupta |

El prefill de Flash-Next es mucho menor porque sus expertos permanecen en RAM y
se cargan mediante la caché MoE; no debe compararse como si ambos modelos
cupieran residentes en la misma GPU. El MTP de 27B sí resultó estable y casi
duplicó el decode del 27B base. El MTP equivalente de Flash-Next ya fue probado
antes y produce un acceso ilegal CUDA reproducible cuando se combina con
expert-cache, por eso no se activa en su perfil usable.

## Verificación matemática de la respuesta esperada

La respuesta exacta del prompt es:

```text
CATCH-UP TIME: 10:30:09
CATCH-UP DISTANCE: 337.86 km
DISTANCE AT 10:00: 35.17 km
```

En esta build experimental, ninguna de las dos variantes del prompt público
produjo esas tres líneas de forma completa. Por lo tanto, el resultado es una
comparación de rendimiento y estabilidad de ejecución, no una validación de
calidad para promover Flash-Next.

## Conclusión operativa

Para uso diario local queda recomendado el **Qwen3.8-27B + MTP**, si se busca
respuesta rápida y el contexto requerido entra en 32K. Flash-Next conserva la
ventaja de capacidad/contexto y la caché MoE, pero en esta máquina rinde menos
que 27B+MTP y su rama necesita una corrección antes de habilitar MTP. El perfil
Flash-Next de LlamaCode fue restaurado y verificado saludable en `127.0.0.1:8031`.

## Auditoría de contexto máximo en Ubuntu (2026-09-06)

Se probó el arranque limpio del mismo `llama-server` Linux en 32K, 64K, 131K,
196K y 262K. Es una prueba de capacidad de contexto al iniciar; no implica que
la recuperación de información en el último token tenga la misma calidad.

| Perfil | 32K | 64K | 131K | 196K | 262K | Máximo verificado |
|---|---:|---:|---:|---:|---:|---:|
| SOL · Flash-Next cache 188 | OK | OK | OK | OK | OOM en buffers CUDA | **196K** |
| TERRA · Qwen 28B MTP3 | OK | OK | OK | OOM en reserva de RS cache | OOM en KV cache | **131K** |

El perfil operativo conserva 32K por estabilidad y latencia. SOL no alcanzó
262K porque faltaron aproximadamente 2,1 GiB de buffers CUDA; TERRA no alcanzó
196K porque la reserva adicional de la caché RS excedió la VRAM disponible.
Los comandos y logs completos están en `artifacts/qwen-*-linux-context-probe*`.

### TPS por nivel de contexto

Para separar el decode del coste de prefill, cada fila arrancó un servidor nuevo
con ese contexto y envió la misma petición corta por `POST /v1/chat/completions`
en streaming, con temperatura 0 y 64 tokens de salida. El TPS se tomó del
`slot print_timing` del servidor, por lo que no se confunde con el tiempo de
prefill ni con el tiempo de carga.

| Modelo | Contexto | Decode TPS | Estado |
|---|---:|---:|---|
| SOL · Flash-Next cache 188 | 32K | **16,30** | OK |
| SOL · Flash-Next cache 188 | 64K | **16,46** | OK |
| SOL · Flash-Next cache 188 | 131K | **16,66** | OK |
| SOL · Flash-Next cache 188 | 196K | **16,25** | OK |
| SOL · Flash-Next cache 188 | 262K | — | CUDA abort/OOM antes de `/health` |
| TERRA · Qwen 28B MTP3 | 32K | **48,96** | OK |
| TERRA · Qwen 28B MTP3 | 64K | **49,86** | OK |
| TERRA · Qwen 28B MTP3 | 131K | **49,99** | OK |
| TERRA · Qwen 28B MTP3 | 196K | — | OOM al reservar compute buffers |
| TERRA · Qwen 28B MTP3 | 262K | — | OOM antes de `/health` |

El contexto nominal no produce por sí solo una caída monotónica de TPS: en esta
configuración el decode corto queda casi plano dentro de cada perfil. TERRA
queda cerca de 50 tok/s en los tres niveles que cargan; SOL queda cerca de
16 tok/s. Los datos crudos están en `artifacts/qwen-*-linux-context-tps-stream*`
y los logs con `slot print_timing` son la fuente de TERRA.

## Muestra de BigCodeBench en Ubuntu

Se ejecutaron directamente como modelo los 8 ejercicios oficiales seleccionados
del pack BigCodeBench-Hard que usa esta comparación, para aislar la calidad de
código del agente. La segunda corrida completa terminó sin crash de LlamaCode,
pero ambos perfiles obtuvieron **0/8**: las salidas incluyeron fences Markdown y
texto espurio dentro del código, produciendo errores de sintaxis antes de
ejecutar los tests.

| Perfil | Score diagnóstico | Decode por tarea | Tiempo total | Lectura |
|---|---:|---:|---:|---|
| SOL · Flash-Next cache 188 | 0/8 | media **45,24 tok/s** (41,06–47,05) | 220,9 s | Rápido, pero salida no utilizable para este harness |
| TERRA · Qwen 28B MTP3 | 0/8 | media **36,27 tok/s** (0,06–66,48) | 217,4 s | Más lento en esta modalidad y también contaminó el código |

Esta corrida es **diagnóstica**, no reemplaza el BCB oficial: la compuerta de
LlamaCode exige HE0 válido antes de HE20 y BCB, y los dos perfiles fallaron HE0
(0/1) en Ubuntu. Por eso no se presenta el 0/8 como score BCB promocionable;
primero hay que corregir la extracción/formato de código generado y repetir
HE0 → HE20 → BCB con la compuerta intacta. Los resultados detallados están en
`benchmark-runs/Ubuntu_8_official_code_tests_diagnostic_20260907_000138`.

## Addendum post-corrección del harness (2026-09-07)

El harness Linux fue revalidado con selección de modelo por plataforma. TERRA
pasó HE0 1/1, HE20 20/20 y BCB 8/8 a 70,37 tok/s; SOL pasó HE0 1/1, HE20 20/20
y BCB 8/8 a 63,94 tok/s. La diferencia de TERRA frente al histórico de 71,51
tok/s es -1,6%.

ASTRA (Flash-Next cache 188, 196K) cargó correctamente, pero HE0 siguió en 0/1
con razonamiento off/on y temperatura 0,0: el modelo produjo salida repetitiva
antes de emitir una tool-call válida. Por eso BCB queda correctamente bloqueado
por el gate, sin presentar un 8/8 artificial.
