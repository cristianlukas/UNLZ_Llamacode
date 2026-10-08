# Auditoría local: NInfer Qwen3.6-35B-A3B en RTX 3090

Fecha: 2026-09-18  
Host: Ubuntu/Linux, Ryzen 9 9950X3D, 2× RTX 3090. Las pruebas del runtime se ejecutaron aislando la GPU física 1 para no mezclar la carga del escritorio.

## Artefacto

- Ruta: `/media/cristian/7CFE1E0FFE1DC1F6/models/NInfer-Qwen3.6-35B-A3B/qwen3_6_35b_a3b.ninfer`
- Tamaño: `22.373.184.256` bytes (aprox. 20,84 GiB).
- SHA-256: `9e8378398d2b789a77224b5110c7590adbbc6fd4accd139b918157b2b9da7163`.
- Es el contenedor compacto v1; no es el v2 con DFlash que el proyecto no usó para sus resultados publicados.

## Resultados reproducidos

Todas las corridas usaron INT8 KV, muestreo conservador y `no-thinking` cuando el template del artefacto lo exigía. La build local es NInfer-3090 para SM86.

| Escenario | Resultado local | Observación |
|---|---:|---|
| Texto, 4K, MTP3, 512 tokens | PP 544,80 / TG 190,08 tok/s | 46,86% de aceptación; 2,40 tokens por ronda |
| Texto, 4K, sin MTP, 512 tokens | PP 572,02 / TG 159,66 tok/s | Control directo; MTP aporta aproximadamente +19% de TG |
| Texto, 32K | PP 625,83 / TG 149,54 tok/s | Arranque correcto |
| Texto, 64K | PP 597,37 / TG 145,00 tok/s | Arranque correcto |
| Texto, 131K | PP 605,33 / TG 141,22 tok/s | Arranque correcto |
| Texto, 262K | PP 675,78 / TG 162,23 tok/s | Arranque correcto; quedan aproximadamente 870 MiB libres |
| Visión, 8K | PP 2.766,31 / TG 161,25 tok/s | Leyó correctamente el texto de la captura de prueba |
| Visión, 32K | TG 161,35 tok/s | Arranque correcto |
| Visión, 64K | TG 161,07 tok/s | Arranque correcto |
| Visión, 131K | TG 165,90 tok/s | Arranque correcto; queda aproximadamente 1,17 GiB libre |
| Visión, 262K | No inicia | La reserva de runtime requiere más memoria que el margen disponible |

### Concurrencia y caché

- `ninfer-serve` con `--max-concurrency 2` admitió dos solicitudes simultáneas de 128 tokens sin errores; los tiempos observados fueron aproximadamente 1,10 s y 1,14 s, alrededor de 224 tokens/s agregados en esa ola corta.
- Prefix reuse: en una segunda solicitud con 90 de 97 tokens reutilizados, el coste calculado bajó a 7 tokens y el prefill observado pasó de aproximadamente 137 ms a 22 ms.
- La opción `--reasoning-effort low` no es compatible con el chat template del artefacto compacto v1. No es un fallo del modelo: para esta build se debe usar `--no-thinking` o una opción de presupuesto que el template acepte.

## Integración en LlamaCode

Se aplicaron dos cambios acotados:

1. `parallelSlots` ahora se traduce a `--max-concurrency` únicamente cuando el ejecutable es `ninfer-serve`; no se envía `--parallel` al CLI de NInfer.
2. Se eliminó el `--text-only` incondicional que hacía imposible usar visión desde LlamaCode. La visión queda opt-in mediante una variante separada: `sys-bench-ninfer3090-qwen35-vision-131k`, que agrega `--vision` y limita el contexto a 131K por el margen medido.

El perfil base `sys-ninfer3090-qwen35` queda con contexto inicial de 8K, `parallelSlots: 2` y presets hasta 262K. Esto habilita el uso concurrente, pero no fuerza visión ni sacrifica memoria para un flujo textual.

## Comparación con los perfiles actuales

| Perfil | Rendimiento local | Calidad/validación | Lectura |
|---|---:|---|---|
| SOL | 74 narrativo / 102 código tok/s | BCB 8/8, tool-use estable, 262K, visión 4/4 | Sigue siendo el default y el perfil agentivo principal |
| QWEN35-A3B vLLM | 123,98 BCB / 134,4 directo | BCB histórico 4/8, visión 4/4, 262K | Mejor referencia dual multimodal/concurrente |
| NInfer Qwen3.6-35B-A3B | 190,08 TG MTP3 en una 3090; C2 agregado corto | Visión hasta 131K y texto hasta 262K; BCB del harness todavía no ejecutado | Candidato secundario rápido, multimodal y concurrente |

El TG de NInfer no se debe presentar como una mejora de calidad: todavía no hay un BCB comparable ni una validación completa de tool-use del harness. Por eso se agrega como experimental/secundario y no reemplaza SOL.

## Estado

- Promovido a candidato experimental en LlamaCode.
- Visión disponible en una variante explícita y limitada a 131K.
- Concurrencia C2 habilitada en el perfil base del servidor.
- BCB/HE del harness: pendientes; no se inventa un puntaje.
- No se modificó el default SOL.
