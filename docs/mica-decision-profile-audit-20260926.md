# Auditoría de perfil de decisiones Mica v0.1 4B — 2026-09-26

## Resultado

Mica aporta una mejora de **selección discreta frente a Laya y Kev en el Tetris publicado**, pero no supera un selector codificado que siempre toma la opción heurística de mejor rank. Corrí localmente la receta oficial en ambas variantes y las tres semillas: los seis trazos coinciden con los publicados en estado, opciones y decisión, **797/797 movimientos**. El baseline local `greedy` logró 285 líneas y sobrevivió las tres semillas en ambos scaffolds; Mica logró 223 en fácil y 25 en base. La comparación con Qwen3.5-4B sigue pendiente.

Registro: candidato de benchmark `decision-mica-v0.1-4b-q5-systemone` y control pendiente `decision-qwen3.5-4b-q4-systemone-control`. Ambos son perfiles de evaluación, no perfiles seleccionables en LaunchPage.

## Qué es y qué no es

El proyecto publica Mica como un Qwen3.5-4B con LoRA rank 16 fusionada, diseñado para recibir un estado textual y una pregunta con opciones y devolver probabilidades tipadas (`noul`, `choice`, `score`) leyendo logits directamente. No genera texto y no ejecuta acciones. Su endpoint es el contrato propio TypeSafe `/v1/systemone`; rechaza entradas de más de 8.192 tokens. El entrenamiento declarado cubre inglés y coreano, con dominios como coding agents, revisión de código y computer-use.

Eso no es equivalente a cargar el GGUF en nuestro `llama-server` OpenAI-compatible: se necesita el servidor directo-readout de Mica. No agregué el GGUF como perfil nativo para evitar que el selector del launcher prometa una ruta generativa que no conserva ese contrato.

## Perfiles de benchmark

| ID de benchmark | Configuración fijada | Uso previsto | Estado |
|---|---|---|---|
| `decision-mica-v0.1-4b-q5-systemone` | `sky7350/Mica-v0.1-4B@ca36594cc2067c7252704f9f304cc10ef11c7c5c`, `mica-v0.1-4b-Q5_K_M.gguf` (3.512.029.568 bytes; SHA-256 `7fbd1be2293ba158157bbbdcdc4ea57569bd9ed53901ed1766f81264d9da8292`); calibración `1.124473`; TypeSafe `/v1/systemone`; `llama.cpp` b11010 CUDA 12.4; contexto 8.192, 8 secuencias, Flash Attention auto, ubatch 512. | Asesoría de una elección entre opciones textuales enumeradas por el host. | Benchmark-only; reproducción local exacta del Tetris publicado. **SUPERIOR** a Laya/Kev en ese resultado publicado; **INFERIOR** al baseline greedy local. |
| `decision-qwen3.5-4b-q4-systemone-control` | GGUF Qwen3.5-4B Q4_K_M, mismo `DirectJudge`, tokenizer, prompt, codebook y suite; contexto 8.192/8 secuencias; sin calibración Mica. | Control base para medir el efecto de los pesos Mica. | A/B no ejecutado; sin resultado atribuible. |

## Evidencia revisada y pruebas

### Tetris publicado

Los tres jueces reciben la misma semilla, flujo de piezas y scaffold. Las opciones dependen del tablero alcanzado por cada trayectoria; por eso no son necesariamente idénticas entre jueces en turnos posteriores.

| Scaffold | Juez | Líneas (semillas 7 / 11 / 23) | Total | Piezas | Mejor opción | p50 por decisión |
|---|---|---:|---:|---|---:|---:|
| Fácil, 4 opciones | **Mica Q5_K_M** | **33 / 97 / 93** | **223** | 121 / 250 / 250; 1/3 top-out | **75%** | 136 ms |
| Fácil, 4 opciones | Laya | 4 / 8 / 5 | 17 | 50 / 59 / 52; 3/3 top-out | 27% | 37 ms |
| Fácil, 4 opciones | Kev 4B | 27 / 17 / 11 | 55 | 107 / 86 / 69; 3/3 top-out | 49% | 124–138 ms |
| Base, 6 opciones | **Mica Q5_K_M** | **5 / 11 / 9** | **25** | 51 / 65 / 60; 3/3 top-out | **47%** | 140 ms |
| Base, 6 opciones | Laya | 0 / 1 / 3 | 4 | 37 / 40 / 44; 3/3 top-out | 13% | 37 ms |
| Base, 6 opciones | Kev 4B | 6 / 6 / 6 | 18 | 54 / 53 / 52; 3/3 top-out | 30% | 138 ms |

Reproducí el motor determinista contra los 18 JSONL que publica el autor: **1.500/1.500 movimientos** pasaron replay de tablero, pieza siguiente, orden/opciones, colocación y líneas acumuladas. Esto comprueba que los trazos son internamente consistentes con el motor del repo; no reproduce la inferencia del modelo.

Después ejecuté la inferencia local con la receta de `scripts/serve.sh` (Q5_K_M, calibración `1.124473`, b11010 CUDA 12.4, `n_ctx=8192`, `seqs=8`, `flash_attn=-1`, `n_ubatch=512`) en una RTX 3090. Las líneas, top-outs y porcentajes de mejor opción coincidieron con la tabla publicada en ambos scaffolds. Comparé además cada traza Mica local con la publicada: **797/797 estados, listas de opciones y decisiones coinciden**. En la misma batería `greedy` alcanzó 98/93/94 líneas (285 total) y 250 piezas en las tres semillas, en los dos scaffolds; `random` logró 13 líneas fácil y 2 base. Mica, por tanto, está por encima del baseline aleatorio, pero queda claramente **por debajo de greedy** en este juego.

También recalculé `results/public231/mica-v0.1-4b.jsonl`: **231/231 respuestas válidas**, 192 correctas; fácil 48/48, original 72/72 y hard 72/111 (**64,9%**). Es el artefacto publicado por el autor, no una corrida local nueva.

### Smoke local del endpoint

- Pesos Q5 descargados desde la revisión fijada; SHA-256 registrado arriba.
- Runtime oficial `llama.cpp` b11010 compilado para CUDA 12.4, release asset verificado: `f66167619958a9c94a3ff43f0f847a83399716f40d70c2c7c9ed097d0a11c280`.
- La primera carga CUDA falló con `cudaMalloc failed: out of memory` mientras otros benchmarks usaban la segunda RTX 3090; no interrumpí esos procesos. Cuando la GPU quedó disponible, el servidor oficial cargó sin errores y completó la batería local reproducible.
- Una corrida exploratoria previa con contexto 2.048, una secuencia y Flash Attention apagado produjo 181 líneas fácil y 21 base. Queda **excluida de la comparación** porque no respetaba la configuración oficial; con `ctx=8192`, ocho secuencias y calibración oficial, se igualaron las seis trazas publicadas.
- El endpoint CPU-only procesó una decisión sintética: eligió la alternativa correcta con probabilidad 0,9781; 211 tokens de entrada, cero tokens generados, 5.293 ms de latencia del servidor (5.361 ms de pared). Es sólo un smoke de contrato.
- Un intento inicial de Tetris CPU de 10 piezas se canceló en warm-up; no produjo filas y se excluye de los resultados. La corrida válida fue en CUDA con la receta oficial.

El JSON de evidencia está en [`artifacts/mica-decision-profile-20260926.json`](../artifacts/mica-decision-profile-20260926.json).

## Clasificación

- **SUPERIOR a Laya/Kev sólo en el Tetris publicado:** en fácil suma 223 vs. 17/55 líneas y acierta la mejor opción en 75% vs. 27%/49%; en base suma 25 vs. 4/18 y 47% vs. 13%/30%. La réplica local coincide en las 797 decisiones.
- **INFERIOR a greedy en este Tetris local:** greedy suma 285 líneas y sobrevive 250 piezas en las seis corridas; Mica suma 223 en fácil y 25 en base y hace top-out en 1/3 y 3/3 semillas. Mica sólo elige entre los primeros cuatro o seis candidatos; greedy toma siempre el candidato que define el propio harness como heurísticamente mejor.
- **INFERIOR en latencia frente a Laya:** 136/37 = **3,7×** más lento en fácil; 140/37 = **3,8×** en base. No convierte a Laya en inferior para su uso de routing rápido.
- **No promovido para el harness de coding:** el modelo no genera código ni tool calls; su máximo de 8K tampoco cubre los contextos largos del agente. La latencia local fue p50 149 ms fácil y 153 ms base. No se corrió un baseline Laya/Kev ni Qwen3.5-4B local en esta pasada.
- **No es un perfil de Ingi-Charla:** no hace ASR, TTS ni diálogo generativo, y no se validó español.
- **No es un modelo de visión/computer-use visual:** la interfaz recibe texto y opciones; no imágenes, capturas ni coordenadas detectadas. Podría investigarse como selector advisory después de UIA/OCR si el host crea opciones válidas; sus probabilidades nunca autorizan acciones destructivas, externas o que requieran aprobación.
- **Sin cambio productivo:** no agregué un perfil nativo de LlamaCode ni cambié defaults. Mica requiere una integración TypeSafe que hoy no existe; los resultados justifican conservar el candidato sólo para benchmarks acotados, no declararlo ganador del harness.

## Fuentes

- [Repositorio de Mica v0.1 4B](https://github.com/akivet/Mica-v0.1-4B)
- [Pesos Mica fijados en Hugging Face](https://huggingface.co/sky7350/Mica-v0.1-4B/tree/ca36594cc2067c7252704f9f304cc10ef11c7c5c)
- [Servidor TypeSafe `/v1/systemone`](https://github.com/akivet/Mica-v0.1-4B/blob/main/mica/typesafe_server.py)
