# Qwen3.8 Flash-Next con SSD offload — auditoría del post

Fecha: 2026-09-14  
Equipo LlamaCode: Ubuntu, 2× RTX 3090, P2P disponible y ~123 GiB de RAM

## Resumen

El post describe `Qwen3.8-Flash-Next UD-IQ1_M` en una RTX 4090 de 24 GB y sólo
32 GB de RAM. La tabla PLE/ngram y parte de los expertos se mantienen fuera de
VRAM/RAM mediante `mmap`/lazy loading y SSD. Reporta 15 tok/s agregados en una
sesión de 112 turnos, con una caída aproximada de 25–27 tok/s a 3K hasta 10–12
tok/s alrededor de 120K.

La idea es útil como técnica de último recurso para hardware con poca memoria,
pero no es una configuración superior para nuestro equipo. El post usa un
quant IQ1_M, SSD como memoria activa y no aporta BCB, HE0/HE20 ni tool-use
comparable con LlamaCode.

## Ideas reutilizables

| Idea del post | Situación en LlamaCode | Decisión |
|---|---|---|
| Mantener `mmap` | ASTRA y los perfiles Flash-Next ya usan `--load-mode mmap` | Ya incorporado |
| Evitar `--no-mmap`/`--mlock` | Las pruebas previas mostraron más presión de memoria, OOM o caída de rendimiento | Mantener desactivados |
| Lazy loading para PLE/ngram | `lazy on` dio TPS bruto alto pero salida `////` corrupta; `on-direct` dio ~7,54 tok/s con salida válida | No activar |
| Ajustar `n-cpu-moe` | Probado en rutas de offload; mueve trabajo crítico a CPU y reduce la respuesta | Sólo benchmark explícito |
| SSD para pesos faltantes | Nuestro equipo tiene ~48 GB de VRAM y ~123 GiB de RAM; el Q4 local ya funciona con cache de expertos | No usar como default |

## Comparación con nuestras mediciones

| Perfil/candidato | Resultado | Contexto | Calidad/estabilidad |
|---|---:|---:|---|
| Post: IQ1_M + SSD offload | 25–27 tok/s a 3K; 10–12 tok/s a ~120K; 15 tok/s agregado | 124,8K usado de 262K | Proyecto terminado por el autor, sin BCB comparable |
| ASTRA, control local | ~14,87 tok/s en prueba Q8 comparable; otras matrices ~16–41 tok/s | 196K | Salida válida en control, pero HE0/BCB no válidos |
| ASTRA, `lazy on` | TPS reportado ~37,56 tok/s | 32K | Salida corrupta `////` |
| ASTRA, `lazy on-direct` | ~7,54 tok/s | 32K | Salida válida, pero 49% más lento que el control |
| BeeLlama KVarN5/KVarN5 | ~36 tok/s decode a 131K; ~27,33 tok/s en solicitud real de ~77,8K | 131K probado | JSON, Python, tool-call y needle válidos; BCB pendiente |
| SOL | 74 tok/s narrativo / 102 código | 262K validado | BCB 8/8 y tool-use OK |

## Decisión

No se descarga el quant IQ1_M ni se añade un perfil SSD. La combinación de
menor precisión y page faults de disco no supera SOL, QWEN38-Q8 ni la ruta
BeeLlama ya validada. La única recomendación que queda incorporada es
conservar `mmap` y no usar `no-mmap`/`mlock` en Flash-Next.

No se modifica el default: SOL continúa siendo el perfil principal. ASTRA
queda experimental y BeeLlama KVarN5/KVarN5 continúa siendo la alternativa
texto-only para contexto largo. No se cambia la política de cuantización: ni
pesos ni KV promovibles superan Q8.

