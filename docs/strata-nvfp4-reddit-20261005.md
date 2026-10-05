# Seguimiento: Strata NVFP4 / Qwen3.8-Flash-Next

Fecha: 2026-10-05. Resultado: se verificó y probó el checkpoint ModelOpt NVFP4 de OrcaRouter en el fork NVFP4 de Strata sobre 2× RTX 3090. La prueba directa de herramientas funciona en prompts cortos. LC-H1 HE0 sólo pasó al fijar prefill en 2K, tras una reparación y en 355 s; las opciones de 4K/8K/16K siguen disparando el bloqueo del prefill batched (issue #29). Ese resultado de un ítem y su latencia no justifican un cambio productivo; no se cambia perfil productivo ni harness.

## Qué versión es y qué se probó

La publicación de Reddit mezcla dos checkpoints: NVIDIA NVFP4 y una variante abliterated. El autor advierte que el 125 tok/s de 256K viene de un prompt sintético repetido y favorable a la localidad, y que su coding real suele variar. El checkpoint que evaluamos es **OrcaRouter Qwen3.8-Flash-Next Uncensored ModelOpt NVFP4**, la variante abliterated, revisión `f24d2b68ff2814f24455ae86717be276619b5664`, empaquetada de forma exacta para el fork. No es el checkpoint NVIDIA del otro resultado de Reddit ni el artefacto con nombre NVIDIA de la prueba histórica del 4 oct.; esos experimentos quedan separados.

Verificación previa: los tensores NVFP4/escala de 24 expertos seleccionados al azar coincidieron bit a bit con el checkpoint ModelOpt. El pack de expertos ocupa 63.28 GiB; el perfil dual de esta ejecución alojó 4,056 expertos (10.44 GiB) en la RTX 3090 primaria y 4,500 adicionales (11.59 GiB) en la secundaria. Equipo local: dos RTX 3090, 24 GiB cada una, PCIe sin NVLink, Ryzen 9 9950X3D, 128 GiB RAM, Linux/CUDA 12.0. Motor del fork: `sergqwer/strata-nvfp4`, commit `992195498c16ea2b26c08bf1ba2402291553136f`, engine 0.1.38-nvfp4.2. Contexto fijado en 131,072; KV int8; MTP4; `spec-min-p=0.5` como control.

Esta no es una réplica de la cifra Reddit: el hardware, el fork/revisión, el sistema operativo, CUDA, el contexto y la distribución PCIe difieren. El README del fork reporta sus medidas principales en RTX 5090/Windows/CUDA 13 y describe el soporte RTX 20/30 como rutas verificadas por emulación en su 5090; por eso el rendimiento local no se extrapola a sus cifras publicadas. [README del fork NVFP4](https://github.com/sergqwer/strata-nvfp4)

## Pruebas y resultado

### API y llamadas a herramientas

- `GET /v1/models`, `/health` y la API OpenAI compatible respondieron con el slug del candidato.
- Una llamada no streaming a la función `add(2,3)` completó con `finish_reason=tool_calls` y argumentos correctos. Una llamada streaming también emitió deltas `tool_calls` válidos. Son pruebas de formato/API, no de desempeño de agente end-to-end.
- En una llamada streaming repetida con el mismo prompt y esquema de herramienta (325 tokens de entrada y 76 de salida), los dos warm runs con `spec-min-p=0.5` dieron 59.1 y 65.8 tok/s; con `0.65`, 48.8 y 57.9 tok/s. Las medianas warm fueron 62.45 vs 53.35 tok/s (+17.1% para 0.5); aceptación MTP warm mediana 88.24% vs 82.60%. En las llamadas frías ambos rondaron 21 tok/s de prefill y 15 tok/s de decode. Es un screening de un prompt y dos warm samples, no un benchmark general; sí muestra que la mejora Q4 con `0.65` no se transfiere a este checkpoint NVFP4. Se conserva `0.5`; no se promociona ningún cambio.

Recibos: `artifacts/strata-nvfp4-reddit-20261005/direct-toolcall-smoke.json`, `direct-toolcall-stream-smoke.json`, `direct-toolcall-spec05-3x.json` y `direct-toolcall-spec065-3x.json`.

### LC-H1 / bloqueo de prefill

Se conectó el candidato a una copia aislada de un perfil LlamaCode y se ejecutó HumanEval/0, primer gate de LC-H1, con `agent-maximo`, seed 4242, thinking activado y el HarnessSpec `sha256:cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef`.

Con prefill `auto` (que eligió 16K) el engine quedó sin progreso en el primer chunk. Se repitió con idle timeout del cliente ampliado a 30 minutos y el mismo corte persistió: era el watchdog interno del engine, no el watchdog de LlamaCode. El primer intento y la repetición terminaron con cero tokens y sin archivo; el 0/1 almacenado es un fallo de infraestructura/harness inducido por la caída de transporte, **no un resultado válido de calidad**.

Iteraciones de chunk:

| Configuración | Prompt observado | Resultado del engine | Resultado Harness |
|---|---:|---|---|
| `--prefill auto` (resolvió 16,384) | 12,826 / 14,753 tokens | Issue #29: 60 s sin progreso en layer 1 del primer chunk; reinicio | 0 tokens, no crea archivo; 0/1 no evaluable; 2 reparaciones |
| `--prefill auto:8192` | 12,826 / 14,753 | Mismo stall exacto a 60 s en layer 1 del primer chunk; 2 reinicios del engine | 0 tokens, no crea archivo; 0/1 no evaluable; 2 reparaciones |
| `--prefill 4096` fijo | 12,826 | Mismo stall exacto a 60 s en layer 1 del primer chunk | Cancelado de forma controlada tras confirmar el stall; sin score |
| `--prefill 2048` fijo | 12,826 / 14,753 | Evitó el watchdog: el segundo intento leyó el prompt completo y generó 228 tokens; 14,753 tokens de prompt en 264.345 s; decode 22.5 tok/s, 173/209 drafts aceptados | HE0 pasó 1/1 **tras una reparación**; 355.284 s de total, 1 llamada a herramienta, 18 líneas creadas |

El candidato de 8K ocupó ~68.3 GiB de RAM residente; quedaron 50,376 MiB disponibles al observar el stall. No era una falta de RAM. El log de `--prefill 4096` muestra `0 of 0 jobs claimed`, todos los workers de expertos dormidos y cero capas atendidas. Reducir chunk de 16K a 8K y luego 4K no resolvió el bloqueo. El chunk fijo de 2K sí permitió terminar HE0, pero con 355.284 s y una reparación; sólo es un workaround técnico para la primera gate, no un resultado LC-H1 completo ni una mejora integral frente a perfiles comparables. Los recibos reproducibles son `artifacts/strata-nvfp4-reddit-20261005/engine-dual-cache-prefill8192.log`, `engine-dual-cache-prefill-fixed4096.log`, `engine-dual-cache-prefill-fixed2048.log`, `app-benchmark-prefill8192-he0.json`, `app-benchmark-prefill-fixed4096-attempt.json` y `app-benchmark-prefill-fixed2048-he0.json`; los JSON completos de cada pasada permanecen en los directorios `benchmark-runs` de Qt test-mode indicados en esos recibos.

## Decisión para LlamaCode

- **Modelo:** técnicamente interesante como perfil experimental. El workaround de 2K logró un HE0 correcto, pero una sola tarea con reparación y 355 s no alcanza para valorar LC-H1 completo ni competir con los perfiles actuales. No se agrega al catálogo/perfiles productivos.
- **Harness:** no se cambia. El cliente LlamaCode alcanza el endpoint, emite solicitudes compatibles y conserva la caída como intento no evaluable. Aumentar el timeout del cliente no arregla el watchdog de 60 s que se dispara dentro del engine.
- **MTP:** para el screening directo en esta variante, `spec-min-p=0.5` superó a `0.65` en velocidad warm; se mantiene el control `0.5`. La diferencia de 2 warm muestras no justifica un perfil de producción.
- **ingi-charla y computer-usage:** estas pruebas no ejercitan voz, OCR, UI automation ni control de escritorio, por lo que no hay motivo para cambiar esas funciones.
- **256K Reddit:** no se probó localmente. El contexto local de 131K y el stall del prefill impiden validar la cifra de 4,100 tok/s prefill/125 tok/s decode. El propio autor califica el prompt 256K repetido como una prueba sintética favorable.

## Entorno aislado y limpieza

LlamaCode corrió con `LLAMACODE_TEST_MODE=1`, `LLAMACODE_PROFILES_DIR=/tmp/llamacode-nvfp4-test/profiles` y `XDG_DATA_HOME=/tmp/llamacode-nvfp4-test/data`. El perfil utilizado fue una copia de prueba; no se tocaron los perfiles productivos. El daemon LlamaCode y los servidores de Strata en 8040–8043 se detuvieron; los puertos quedaron sin listener y las RTX 3090 regresaron a 463/108 MiB usados. Los recibos del perfil y configs están en `artifacts/strata-nvfp4-reddit-20261005/`.

## Próximo paso

No correr todavía el LC-H1 completo. Para no repetir los bloqueos ya medidos, el siguiente ensayo debe usar una versión del fork que corrija `reading the prompt (batched): layer 1 ...` o usar un prefill fijo de 2K con otro ítem representativo. Si el workaround se repite con calidad y una latencia útil, recién entonces evaluar HE20/BCB8/Adversarial en A/B con el mismo harness. No inferir una mejora por tok/s de una llamada corta ni por el HE0 aislado.

## Fuentes

- [Fork Strata NVFP4 y límites del hardware medido](https://github.com/sergqwer/strata-nvfp4)
- [Checkpoint OrcaRouter ModelOpt NVFP4](https://huggingface.co/jpezzulli/OrcaRouter-Qwen3.8-Flash-Next-Uncensored-ModelOpt-NVFP4)
- Publicación de Reddit transcripta por el usuario en la solicitud original.
