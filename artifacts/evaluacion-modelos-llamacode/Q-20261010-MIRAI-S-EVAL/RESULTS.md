# Resultados — Q-20261010-MIRAI-S-EVAL

**Estado: auditoría documental completa; sin descarga, build, inferencia ni promoción.** El material combina un quant nuevo de Qwen3.8-27B con un runtime llama.cpp especializado, caché KV escalonada/MTP y una capa API opcional. El post no demuestra «70 tok/s a 262K» de forma sostenida.

## Qué dice el material primario

- El post atribuye 70 tok/s, contexto de 262K y mejoras agentic a una receta de RTX 4070 de 12 GB. Enlaza el checkpoint experimental de Mirai Labs y `mirai-s-ada`.
- La card de Mirai marca el proyecto experimental y dice que los números son provisionales. El checkpoint es una versión trellis de Qwen3.8-27B, aproximadamente 2,4 bits por peso; se declara 8,45 GB para el modelo del Hub. La conversión GGUF de alesha-pro es de ~11,17 GB y conserva tipos ggml privados 90–93. El llama.cpp stock que usa LlamaCode no puede abrir ese GGUF.
- `mirai-s-ada` obtiene 262.144 posiciones con KV q8_0 en una receta tiered: ~58K posiciones en VRAM y el resto en RAM bloqueada/pinned. En la RTX 4070 reporta 76,6 tok/s a contexto vacío, 61,7 a 60K, 19,5 a 120K y 11,4 a 180K. Así, 70 tok/s y 262K son dos puntos distintos de la curva.
- En la prueba Linux del autor de la conversión, una RTX 3090 limitada a 12 GB con 44K posiciones en VRAM reportó 66,9 tok/s a 8K, 27,9 a 60K, 9,5 a 120K y 5,8 a 180K. Esta sí es evidencia del autor del runtime de referencia, pero el PCIe era 3.0 y no representa el host LlamaCode.
- La página del proyecto dice que el proxy `layer` agrega API cards, valida nombres/argumentos de API y ofrece `run_python` bajo WASI con 128 MB/10 s y sin archivos del host, red ni procesos. Cuando el cliente manda sus propias tools, el proxy no ofrece `run_python`; conserva sólo las API cards. La capa publicada, por tanto, no reemplaza las herramientas de coding del harness LlamaCode.

## Evidencia de calidad publicada y sus límites

La suite `exact-work` del propio proyecto cubre 37 tareas. La ejecución pareada ML2 reporta 16/37 raw frente a 29/37 con layer; la revisión ML2b reporta 18/37 frente a 28/37, con 12 rescates y 2 pérdidas. La familia coding bajo dos juegos de seeds muestra 7/24 raw y 12/24 con layer, pero una prueba de baja resolución/effort distinto cambia además tokens y comportamiento. HumanEval 164 reporta 158/164 raw, 160/164 tras un chequeo de ejemplos, y 154/164 sin thinking. Son cifras del autor, de perfiles y gates propios; no son resultados de LlamaCode ni una comparación independiente con SOL/ASTRA/Q4.

El README informa que una corrida pareada de 37 tareas (74 ejecuciones entre raw/layer) duró 3,5 horas. No cabe en el criterio del usuario de ≤30 minutos acumulados por perfil para tres semillas, por lo que no se corrió ni se descargó el repo/modelo. Un HumanEval corto no sustituiría esa suite y no validaría contexto largo, agentic E2E ni seguridad con herramientas.

## Utilidad para LlamaCode

- **No integrar el modelo/runtime en perfiles productivos ahora.** El GGUF necesita tipos y kernels de una bifurcación especializada; no es compatible con el binario stock. Una prueba local exigiría model files ausentes y otra build/runtime completo.
- **No adoptar el `layer` como mejora general del harness.** La parte de Python sandbox no se ofrece cuando LlamaCode manda tools cliente. Las API cards son una idea acotada para tareas Python que mencionan paquetes: se podría diseñar una prueba propia en menos de 30 minutos, pero no atribuir el resultado a este modelo ni a los 37 casos privados del proyecto.
- El trade-off de contexto es claro y útil como idea de perfil de poca VRAM: 262K queda técnicamente disponible al mover parte de la KV a RAM, con caída marcada de decode al superar la línea de VRAM. No asumir 70 tok/s a profundidad 262K ni recuperación de hechos sin una prueba larga.
- No habilitar ni evaluar el vector opcional de eliminación de refusals para agentes con acciones.

## Preflight local y decisión

Se buscaron nombres/artefactos Mirai en `/media/cristian/Disco local/Models`, `/media/cristian/HDD extra` y `/home/cristian/.cache/huggingface/hub`; no apareció checkpoint, conversión GGUF ni directorio de cache Mirai. No se descargó nada. Durante la comprobación de sólo lectura, GPU0 reportó 1.736 MiB/24 GiB y 25% de utilización; GPU1 reportó 108 MiB/24 GiB y 9%. No se reservaron recursos ni se tocaron procesos.

**Decisión:** no promover, descargar ni compilar ahora. Mantener los perfiles existentes. Si se pide una prueba futura, separar (A) calidad del modelo raw, (B) el efecto de API cards/capa, y (C) latencia/contexto del runtime; fijar hashes/revisiones, herramientas cliente, semillas y verificadores antes del run. Exigir una suite completa de tres seeds que proyecte ≤30 minutos por perfil; el exact-work publicado no cumple.

## Artefactos y fuentes

- [Plan preregistrado](PLAN.md)
- [Recibo de fuentes](receipts/source-review.json)
- [Preflight local](receipts/local-preflight.json)
- [Post de Reddit](https://www.reddit.com/r/LocalLLM/comments/1x1rv5k/mirai_s_70_toks_262k_context_12gb_gpu/)
- [Card del modelo Mirai Labs](https://huggingface.co/trymirai/Qwen3.8-27B-S-experimental)
- [README del GGUF de referencia](https://huggingface.co/alesha-pro/Qwen3.8-27B-S-mirai-GGUF)
- [README y resultados de mirai-s-ada](https://github.com/professorpalmer/mirai-s-ada)
- [Informe técnico y suite del proyecto](https://raw.githubusercontent.com/professorpalmer/mirai-s-ada/main/docs/REPORT.md)
- [README del engine de referencia](https://github.com/alesha-pro/llama.cpp-mirai-s/blob/master/tools/mirai-s/README.md)
