# Historia, descubrimientos y anotaciones de benchmarking

Este archivo es el espejo histórico de [`benchmark-results.md`](benchmark-results.md).

## 2026-08-17 — Reparación del tier DeepSeek VRAM 0–5

Se investigó la conclusión anterior que atribuía el bloqueo del tier 0–5 a la
generación/harness. La evidencia nueva obliga a corregirla: el primer fallo de
la variante 0–5 reducida ocurrió en el primer prompt con `CUDA error: an illegal
memory access` en GPU0, antes de que el agente pudiera crear
`solution_HumanEval_0.py`. Por lo tanto, no se habilitó HE20 ni BCB.

Se conservaron las variantes históricas y se probaron copias separadas:

| Variante | Cambio | HE0 | Resultado técnico |
|---|---|---:|---|
| `VRAM experts 0-5` | reparto histórico, ctx 131k | 0/1 | El agente llegó a generar, pero el watchdog terminó una reparación sin cambios; luego el agente básico omitió el archivo esperado. |
| `VRAM experts 0-5 · HE0 safe` | mismo reparto; `predict=4096`, ctx 65k, batch 2048, ubatch 512 | 0/1 | `CUDA error: an illegal memory access` en GPU0 al primer prompt; server salió con código `-1073740791`. |
| `VRAM experts 0-5 · CUDA stable` | además `flash-attn off`, `no-mmap` | 0/0 | No carga: el GGUF usa cache V cuantizada y exige Flash Attention. Al corregir Flash Attention a `on`, la carga quedó inestable y el daemon desapareció antes de finalizar HE0. |

Se hizo una repetición adicional del tier histórico 0–5 con `agent-chat`, sin
cambiar el reparto CUDA: `0/1` en `61,421 s`, `10,38 t/s`, sin archivo creado y
sin acceso ilegal a CUDA. Cambiar de agente no corrigió el resultado; el fallo
queda clasificado como salida/modelo no evaluable, no como infraestructura. Por
la compuerta HE0, no se ejecutaron HE20 ni BCB para ninguna variante 0–5/0–9.

La conclusión operativa queda así: **DeepSeek VRAM 0–1 sigue siendo la mejor
variante DeepSeek validada (HE0 1/1 y HE20 histórico 20/20)**. Mover expertos
0–5 sí aumenta la ocupación de GPU0, pero con el binario/GGUF actuales no es una
configuración validada: presenta acceso ilegal intermitente o caída durante la
carga. El problema no es sólo generación ni harness, y no corresponde presentar
0–5 como candidato a HE20 hasta obtener una combinación de backend, binario y
reparto que pase HE0 limpio. El tier 0–9 permanece descartado por OOM en GPU0
(`24663.67 MiB` solicitados sobre `24576 MiB`).
No se reescriben resultados anteriores: cada mejora agrega una entrada nueva
con fecha, configuración, evidencia y decisión.

El ID de la primera columna es el `launchId` persistente de LlamaCode. El
nombre visible puede cambiar sin perder la asociación con sus resultados.

## 2026-08-17 — Selección operativa

La tabla viva se redujo a los siete perfiles solicitados. Se marcó con `⚡` el
Qwen3.8 UD-Q4 visión como BEST de esta selección por tener el mayor BCB
registrado (5/8). Los demás perfiles no llevan el indicador BEST.

Desde esta fecha, el conjunto operativo queda restringido a perfiles con el
indicador `⚡ BEST`; los demás se conservan sólo como histórico y no se
benchmarkean nuevamente sin autorización explícita.

## 2026-08-17 — Telemetría DeepSeek: VRAM por GPU y TPS

La telemetría histórica de LlamaCode conserva `vramMb` agregado y `ramMb`, no
el desglose por GPU. Por eso no se inventa una separación GPU0/GPU1 para las
corridas anteriores; ese desglose debe capturarse durante la nueva serie de
variantes.

| Corrida | Calidad | Tiempo | TPS | RAM pico | VRAM agregada |
|---|---:|---:|---:|---:|---:|
| DeepSeek original — HE20 actual | 20/20 | 1164,244 s | 9,58 | 92.771 MB | 32.986 MB |
| DeepSeek original — HE20 histórico | 20/20 | 802,656 s | 10,35 | 91.865 MB | 32.785 MB |
| DeepSeek VRAM balance — HE20 histórico | 20/20 | 775,223 s | 10,76 | 91.779 MB | 35.705 MB |
| DeepSeek VRAM balance — repetición HE20 | 20/20 | 860,886 s | 9,02 | 91.893 MB | 35.604 MB |

Durante el BCB activo de DeepSeek, la muestra directa del sistema entre
22:19:43 y 22:20:24 registró GPU0 entre 11.086 y 11.150 MB, GPU1 estable en
21.698 MB y RAM de trabajo del servidor en 93.097 MB. El endpoint `/metrics`
reportó 7,484 TPS de generación promedio al cierre de la muestra. La RAM de
trabajo del proceso no representa toda la memoria mapeada del modelo; para
comparar contra las corridas históricas se usa el pico `ramMb` de LlamaCode.

## 2026-08-17 — DeepSeek: tiers de expertos en GPU0

Se conservaron los perfiles originales y se agregaron dos copias desde la
variante VRAM 0–1:

| Perfil | ID | HE0 | Tiempo | TPS | RAM pico | VRAM agregada | Estado |
|---|---|---:|---:|---:|---:|---:|---|
| DeepSeek original | `4f5cc556-333d-4310-955e-15042cd874d6` | 1/1 | 188,312 s | — | 92.303 MB | 32.736 MB | Válido |
| DeepSeek VRAM 0–1 | `6b3bf7bd-0889-491a-9b6d-b12128478a5f` | 1/1 | 184,200 s | — | 92.375 MB | 35.780 MB | Válido |
| DeepSeek VRAM expertos 0–5 | `f3d000b7-59da-4035-9114-f326515ba95d` | 0/1 | 351,267 s | — | 79.374 MB | 42.586 MB | Harness/watchdog; sin OOM/CUDA |
| DeepSeek VRAM expertos 0–9 | `78929286-486e-43a2-a97b-25f251d34254` | 0/0 | 9,199 s | — | — | — | OOM al cargar GPU0 |

El tier 0–5 también se repitió con `agent-basico`: terminó en 0/1 de
calidad, 161,997 s, 4,119 TPS, 77.334 MB de RAM y 42.621 MB de VRAM; el
modelo no creó `solution_HumanEval_0.py`. La primera ejecución con
`agent-maximo` quedó detenida por el watchdog tras 180 s sin cambios del
workspace, aunque el servidor llegó a decodificar cerca de 9,7 t/s.

El tier 0–9 no es viable con contexto 131k y la configuración actual:
`cudaMalloc` pidió 24.663,67 MiB en GPU0 frente a 24.576 MiB disponibles.
Conclusión: sí es posible mover más expertos a GPU0 hasta el tier 0–5, pero
0–5 todavía no es una candidata válida de calidad y 0–9 requiere reducir
contexto/batch o usar una distribución más conservadora.

## 2026-08-17 — Laguna safe y reparación del harness

- Laguna original fallaba durante la carga CUDA en GPU0, antes del harness.
- Se agregó `BALANCE - Laguna S.2.1 · CUDA safe 64k`: contexto 65k,
  batch/ubatch 256/64, `fit off`, Flash Attention activado, `tensor-split 1,1`
  y 32 expertos en CPU.
- La variante con Flash desactivado fue rechazada porque la V-cache cuantizada
  requiere Flash Attention.
- Tras corregirla, HE0 pasó 1/1 en 150,127 s sin crash CUDA.
- Laguna safe todavía requiere HE20 y BCB.

## 2026-08-17 — Reparaciones DeepSeek y bucles del agente

- `code_tests` ahora conserva el traceback completo y el agente recibe los
  checks locales exactos.
- La reparación BCB exige editar un archivo fallido como primera acción.
- El watchdog cancela después de 180 s sin cambios reales.
- `agent-avanzado` fue el mejor agente probado: 3/8 → 4/8.
- `agent-maximo` obtuvo 1/8 → 1/8.
- Esto corrige la infraestructura de reparación, pero no convierte por sí solo
  un fallo funcional del código generado en un éxito.

## 2026-08-17 — HE20 actual de DeepSeek

- Se inició HE20 con la configuración vigente, `agent-avanzado`, harness LC-H1
  y timeout de 3600 s.
- Resultado final: 20/20, 1164,244 s, `avgTps=9,577`, sin reparaciones,
  `failureKind=none` y sin crash CUDA ni cierre del daemon.
- BCB fue habilitado después de validar la huella HE20 actual y quedó en curso
  con `agent-avanzado` y timeout de 5400 s.

## Diagnósticos BCB conocidos

- DeepSeek 765: rutas almacenadas como claves del diccionario.
- DeepSeek 771: contrato exacto de `os.listdir()` y nombres CSV.
- DeepSeek 1019: comentario mediante `img.info.get("comment")`.
- DeepSeek 583: el test exige claves RSA de 512 bits.
- DeepSeek 139: histogramas separados y ejes independientes.
- DeepSeek 360: cierre correcto de Excel y desviación estándar poblacional.
- Laguna 928: bigramas consecutivos ordenados, no combinaciones con reemplazo.

## Regla de interpretación

`server-load`, `server-crash`, `cuda illegal access`, `Connection closed` y
`failureKind=infrastructure` se investigan como infraestructura. Un
`AssertionError`, `KeyError`, `PermissionError` o contrato de archivo con el
servidor estable se clasifica como fallo funcional del código generado o del
agente/harness.
