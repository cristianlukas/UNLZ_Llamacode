# Auditoría de la receta comunitaria para Qwen3.8 Flash-Next — 2026-09-14

## Objetivo

Evaluar la receta publicada para `Qwen3.8 Flash-Next UD-Q4_K_XL` en dos RTX
3090 y determinar si mejora algún perfil de LlamaCode. La publicación reporta
49 tok/s de generación en Windows a aproximadamente 10,6K tokens, pero usa
KV BF16 y una rama específica de `llama.cpp`; por eso no se toma ese número
como equivalente a una validación BCB o de tool-use.

Referencia aportada: [rama flashnext-e06 de Inovello](https://github.com/Inovello/llama.cpp/tree/flashnext-e06).

## Restricciones del proyecto

- Los pesos y el KV de perfiles promovibles no pueden superar Q8.
- La prueba se hizo en el entorno actual de Ubuntu con dos RTX 3090 y P2P
  disponible.
- No se copió ni descargó otro modelo: se reutilizó el artefacto ya existente
  en `/media/cristian/Disco local/Models/llamacpp/`, porque ocupa unos 111 GB
  más el head MTP de aproximadamente 2,8 GB.

## Pruebas realizadas

### 1. Receta comunitaria adaptada a KV Q8

Se usó la build `llama.cpp-phase-prefill-e06` disponible localmente con:

- `LLAMA_ATTN_ROT_DISABLE=1` y `LLAMA_MMAP_PIN_HOST=1`;
- `--ctx-size 131072`, `--split-mode layer`, `--load-mode mmap`;
- `ffn_(gate|up|down)_exps.weight=CUDA_Host` y
  `per_layer_token_embd.weight=CPU`;
- `--moe-expert-cache 150`, `--ubatch-size 512`, `--batch-size 4096`;
- Flash Attention, KV K/V `q8_0`, una sesión y sin BF16.

Resultado: el servidor cargó, pero el smoke test de código produjo solamente
una secuencia de `/`. El log registró aproximadamente 45,5 tok/s, pero la
salida no es utilizable. Se clasifica como fallo funcional, no como mejora.

### 2. Receta ASTRA actual con cache de expertos 188

Se repitió con rotación normal, reparto CPU/VRAM de ASTRA, KV K/V `q8_0`,
`--moe-expert-cache 188`, `--ubatch-size 512` y `--batch-size 2048`.

Resultado: cargó sin abortar. En el mismo smoke test respondió unos 36,9 tok/s,
pero repitió fragmentos del enunciado en vez de generar una implementación
válida. Por lo tanto, el rendimiento no compensa el fallo de calidad.

Sin el reparto de expertos, `n_gpu_layers=999` intentó reservar unos 40,3 GiB
en GPU0 y falló por falta de VRAM. Esto confirma que el reparto CPU/VRAM no es
opcional para este artefacto en nuestra máquina.

### 3. Variante especulativa publicada

La combinación `--spec-type draft-mtp,ngram-mod` con el head MTP local no pudo
iniciar en esta build: el cargador interpretó el shard principal como draft
head y terminó con el error de `token_embd.weight` ausente. Las pruebas
anteriores tampoco obtuvieron una variante MTP/NGRAM estable para ASTRA.

### 4. BF16 y `load-mode none`

La receta original usa KV BF16. No se promovió ni se considera válida para el
dropdown porque excede el límite Q8 del proyecto. Además, las pruebas previas
mostraron que `load-mode none` provoca una reserva de memoria demasiado grande
o una caída de rendimiento; se mantuvo `mmap` para esta auditoría.

## Comparación con los perfiles actuales

| Candidato | Resultado reproducido | Decisión |
| --- | --- | --- |
| Receta e06 + cache 150 + KV Q8 | Carga; salida corrupta (`////`) pese a ~45,5 tok/s | No promover |
| ASTRA actual + cache 188 + KV Q8 | Carga; ~36,9 tok/s, salida repetitiva no válida | Mantener ASTRA experimental |
| Receta original con KV BF16 | Fuera de la política Q8; no es comparable para promoción | No usar |
| Variante MTP + NGRAM | El parser/cargador local no la inicia de forma estable | No activar |
| SOL actual | BCB 8/8, aproximadamente 74 tok/s narrativo y 102 tok/s código, 262K validado | Mantener como default |

## Conclusión

La cifra de 49 tok/s del post no se reproduce como una respuesta válida en
nuestro setup. La diferencia proviene además de una combinación de Windows,
otra build, KV BF16, una medición corta y MTP/NGRAM; no constituye evidencia
de superioridad frente a SOL.

No se modificó el dropdown ni el default. SOL sigue siendo el perfil principal;
ASTRA queda como experimental para contexto Flash-Next. No hay cambios de
perfiles justificados por esta receta.

## Revisión del post de 10 tok/s y del repositorio AI1 — 2026-09-14

El nuevo post reporta aproximadamente 9,6 tok/s con `UD-Q4_K_XL`, sin MTP, en
una máquina con cuatro GPUs heterogéneas (RTX 3090 + RTX 5060 + 2× RTX 3060),
64 GB de VRAM agregada y 64 GB de RAM. Es una referencia de capacidad, no una
comparación A/B válida contra nuestros dos RTX 3090, y además queda por debajo
de las mediciones locales de ASTRA y muy por debajo de SOL.

El enlace adicional apunta a [qwen38-flash-next-ai1](https://github.com/cat5edopeHA/qwen38-flash-next-ai1),
un proyecto experimental para dos Radeon PRO R9700 (`gfx1201`) con una rama HIP
específica de `llama.cpp`. El repositorio declara que el soporte `qwen4exp` no
es el árbol estable, que tensor/row split y varias rutas de especulación tienen
limitaciones, y que sus resultados no son transferibles a CUDA SM86. Sus cifras
de IQ1 y ngram no constituyen una recomendación de calidad: el quant más chico
es precisamente el que no debemos usar sin HE/BCB y tool-use comparables.

### Cruce con las pruebas anteriores

| Variante | Resultado comparable | Decisión |
|---|---|---|
| Post: Q4 sin MTP, cuatro GPUs mixtas | ~9,6 tok/s; hardware y runtime distintos | No supera ningún perfil |
| AI1: IQ1 + ngram | ~50,9 tok/s en una build HIP experimental; sin equivalencia de BCB LlamaCode | No adoptar IQ1 ni ngram |
| AI1: Q4 + ngram | ~30,8 tok/s en R9700; no CUDA/3090 | No transferible |
| ASTRA local estable | ~16–41 tok/s según contexto; calidad agéntica no validada | Mantener experimental |
| SOL local | 74 tok/s narrativo / 102 código; BCB 8/8 y tool-use OK | Mantener default |

No se ejecutó una prueba nueva porque el repositorio enlazado requiere AMD
`gfx1201` y no puede correr en las RTX 3090. Tampoco se descargó otro modelo:
el artefacto Q4 de Flash-Next ya había sido probado localmente y el espacio de
modelos sigue siendo limitado. El resultado no cambia la tabla ni los defaults.

## Revisión del caso M5 Max de 128 GB — 2026-09-14

El nuevo reporte describe una sesión de OpenCode de más de tres horas con
`UD-IQ4_XS` de 93,7 GB, 128 GB de memoria unificada, Metal, 128K de contexto,
un solo slot y speculative decoding. El resultado publicado fue de 24–36
tok/s de decode y aproximadamente 1.000 tok/s de prefill, con un proyecto
Flutter/PostgreSQL/Playwright validado en varias iteraciones.

Es una demostración valiosa de que Flash-Next puede sostener un flujo agentico
largo cuando el modelo, la tabla n-gram y la caché comparten una memoria grande.
No es, sin embargo, una medición superior a nuestros perfiles: el hardware,
backend, cuantización, sistema de memoria y harness son distintos, y el reporte
no publica BCB, HE0/HE20 ni una tasa de tool-call comparable.

### Ideas reutilizables frente a nuestras pruebas

| Idea del reporte | Resultado ya medido en LlamaCode | Decisión |
|---|---|---|
| 128K y un solo slot | ASTRA carga hasta 196K; su calidad agéntica sigue sin validarse | Mantener ASTRA experimental |
| Descargar la tabla n-gram a SSD | `lazy on` dio TPS bruto alto pero salida corrupta; `on-direct` fue válido pero ~7,54 tok/s | No activar por defecto |
| Speculative decoding | MTP/combos de ASTRA no quedaron estables con la caché de expertos | No activar |
| Q4 agresivo | El IQ4_XS funciona en el entorno Metal del reporte; nuestro Q4/INT4 estable es SOL | Mantener SOL |
| Una sola sesión larga | Nuestro control usa `parallel=1` y pruebas de contexto frío/caliente separadas | Ya incorporado |

### Comparación operativa

| Perfil | Decode local | Calidad/estabilidad | Contexto |
|---|---:|---|---:|
| Caso M5 Max publicado | 24–36 tok/s | Proyecto terminado, sin BCB comparable | 128K |
| ASTRA local | ~16–41 tok/s según contexto | HE0/BCB no válidos; experimental | 196K |
| SOL local | 74 narrativo / 102 código | BCB 8/8, tool-use OK | 262K validado |

No se repitió otra descarga ni se modificó el runtime: la prueba local de
`lazy-mode`, el SSD/PLE y la especulación ya cubre las modificaciones relevantes
del reporte. No se cambia el default ni el dropdown. La única conclusión
accionable es conservar la regla de separar velocidad de contexto, prefijo
caliente, tool-use y calidad final; el resultado de M5 no demuestra que ASTRA
pueda reemplazar SOL.

## Revisión del quant de 85 GB con tabla n-gram en SSD — 2026-09-14

El reporte describe un quant propio de Qwen3.8 Flash-Next ejecutado en un
MacBook de 64 GB. La variante de demostración ocupa aproximadamente 45,8 GB de
RAM y 39,1 GB de SSD; una versión posterior usa 54,5 GB de RAM y 38,4 GB de
SSD. El resultado publicado es 517,9 tok/s de prefill y 36 tok/s de decode en
Metal, con una tabla n-gram de unos 39 GB ubicada en un shard separado.

La idea técnica es válida: la tabla PLE se consulta en direcciones deterministas
y no hace falta mantenerla completa en memoria. Pero el resultado depende de
tres condiciones que no tenemos resueltas en el backend CUDA actual: quant
reempacado con la tabla separada, lecturas directas seguras de ese shard y
compatibilidad completa con el runtime `qwen4exp`/Flash-Next.

### Comparación contra nuestras pruebas

| Variante | Resultado local o publicado | Lectura |
|---|---|---|
| Quant 85 GB del reporte | 517,9 prefill / 36 decode en Mac Metal | No comparable directamente con nuestras 3090/CUDA |
| ASTRA `lazy off`, Q8 | 14,87 tok/s en la prueba comparable; salida válida | Control local reproducible |
| ASTRA `lazy on`, Q8 | TPS bruto alto, pero salida `////` corrupta | Rechazado |
| ASTRA `lazy on-direct`, Q8 | 7,54 tok/s; salida válida | Correcto, pero 49% más lento que el control |
| SOL | 74 narrativo / 102 código; BCB 8/8; tool-use OK | Sigue siendo el default |

El reporte tampoco aporta BCB, HE0/HE20 ni una tasa comparable de tool-use; sus
porcentajes `top1` y KLD son métricas del quant, no una validación de agente.
Además, el quant de 85 GB no está instalado en
`/media/cristian/7CFE1E0FFE1DC1F6/models` y el espacio libre actual no permite
descargarlo de forma prudente.

### Decisión

No se implementa ni se promueve el quant. La mejora potencial queda anotada
como trabajo futuro: generar/obtener un shard PLE separado compatible con CUDA,
integrarlo con `on-direct` y exigir salida correcta, HE0, BCB y tool-use antes de
compararlo con ASTRA y SOL. Mientras tanto se conserva `mmap`/`lazy off` en la
ruta experimental y SOL continúa como default.
