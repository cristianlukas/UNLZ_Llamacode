# Matriz de contexto: TERRA, LUNA y METEOR — 2026-09-07

Esta campaña repite el eje de contexto usado para ASTRA y SOL en Ubuntu,
manteniendo una sola huella CUDA comparable por perfil temporal y probando
`32K`, `64K`, `131K`, `196K` y `262K`.

## Método y validez

- La velocidad es `decode TPS P50` del benchmark `LlamaCode Server Speed v1`,
  con una instancia fría por variante y un solo slot. Es la métrica adecuada
  para comparar generación; no se mezclan con el TPS E2E del agente.
- Cada variante pasó HE0 (`HumanEval`, 1 tarea) antes de continuar. HE0 pasó
  en todos los contextos que llegaron a cargar.
- Para no convertir horas de reparación en una falsa comparación, HE20 y BCB
  se ejecutaron en el mayor contexto estable de cada modelo. Un score BCB bajo
  se conserva como calidad del modelo; una carga fallida, timeout o reparación
  cancelada se marca como infraestructura/inconcluso.
- Las copias temporales de LUNA y METEOR usaron el backend CUDA de TERRA para
  medirlas en las dos RTX 3090. Los perfiles permanentes de LUNA y METEOR no
  fueron modificados por esta campaña.

## Velocidad y estabilidad por contexto

| Perfil | 32K | 64K | 131K | 196K | 262K |
|---|---:|---:|---:|---:|---:|
| TERRA — decode P50 | 63,94 | 64,12 | 63,85 | 63,34 | 63,47 |
| LUNA — decode P50 | 56,51 | 56,58 | 55,10 | 55,32 | No carga |
| METEOR — decode P50 | 33,22 | 33,20 | 33,01 | 33,21 | No carga |

Todos los valores están en tok/s. La variación de TERRA y LUNA entre 32K y
196K es pequeña porque el benchmark de decode usa un prompt corto; el costo
real de contexto largo aparece sobre todo durante el prefill y en el tiempo
E2E del harness.

### HE0 por nivel

| Perfil | 32K | 64K | 131K | 196K | 262K |
|---|---:|---:|---:|---:|---:|
| TERRA | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| LUNA | 1/1 | 1/1 | 1/1 | 1/1 | carga fallida |
| METEOR | 1/1 | 1/1 | 1/1 | 1/1 | carga fallida |

## Calidad en el techo estable

| Perfil | Contexto probado | HE20 | BCB final | Tiempo HE20 | Tiempo BCB | Lectura |
|---|---:|---:|---:|---:|---:|---|
| TERRA | 262K | 20/20 | 6/8 | 104,9 s | 416,3 s | Carga y HE20 estables; BCB no llega a 8/8 |
| LUNA | 196K | 20/20 | 6/8 | 947,6 s | 945,3 s | Calidad parcial y E2E muy lento |
| METEOR | 196K | 20/20 | inconcluso | 1.867,1 s | — | La reparación BCB fue cancelada por costo; no hay score final comparable |

TERRA y LUNA llegaron a `6/8` después de dos intentos de reparación, pero el
registro del harness conserva `failed=true`; por eso no se consideran perfiles
BCB limpios ni se promocionan a un nivel de calidad 8/8. METEOR llegó a
ejecutar parte del BCB, pero la reparación se volvió demasiado lenta tanto a
196K como en el reintento de 64K y se canceló sin cerrar un resultado final.

## Recomendación

- **TERRA:** es el mejor de estos tres para contexto largo. 64K o 131K es el
  punto práctico para uso diario; 262K es el máximo estable medido y queda
  reservado para tareas que realmente necesiten ese contexto. No reemplaza un
  perfil 8/8 hasta repetir/corregir el BCB.
- **LUNA:** usar 64K como punto equilibrado; 131K sigue siendo razonable. 196K
  carga y pasa HE20, pero el tiempo E2E deja de ser atractivo. No usar 262K.
- **METEOR:** reservarlo para throughput corto, preferentemente 32K–64K. Aunque
  el servidor carga hasta 196K, el harness se vuelve demasiado lento y no hay
  BCB final comparable. No es buen perfil principal de agente.

La campaña no promovió cambios permanentes ni alteró Windows. Las mediciones
completas quedan auditables en:

- `/home/cristian/.local/share/LlamaCode/LlamaCode/benchmark-runs/server_speed_20260907_131053`
- `/home/cristian/.local/share/LlamaCode/LlamaCode/benchmark-runs/server_speed_20260907_131702`
- `/home/cristian/.local/share/LlamaCode/LlamaCode/benchmark-runs/BigCodeBench-Hard_8_tems__20260907_142746`
