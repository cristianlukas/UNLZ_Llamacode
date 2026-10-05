# Auditoría Strata NVFP4 — requisito de almacenamiento

Fecha: 2026-10-04. Estado: auditoría de fuentes y prueba de carga/API parcial;
LC-H1 bloqueado por identidad de checkpoint sin trazabilidad suficiente,
inestabilidad del servidor durante HE0 y falta del margen de almacenamiento
requerido para repetir la prueba de forma controlada.

## Candidato identificado

El fork actual es
[`sergqwer/strata-nvfp4`](https://github.com/sergqwer/strata-nvfp4), commit
`992195498c16ea2b26c08bf1ba2402291553136f`. Adapta Strata para el checkpoint
ModelOpt NVFP4 de OrcaRouter Qwen3.8-Flash-Next Uncensored. No es el Genesis
NVFP4 de Swift probado con `llama.cpp` el 2026-09-29, ni el UD-Q4_K_XL medido
con Strata en el informe LC-H1 del 2026-10-04.

El README del fork indica soporte de código para RTX 20/30/40/50, con fallback
en RTX 30, pero las medidas publicadas y el desarrollo de la release se hicieron
en Windows 11, RTX 5090, CUDA 13.3, Ryzen 9 9950X3D y 128 GiB RAM. Declara que
las rutas RTX 20/30/40 se verificaron por emulación en esa máquina; no presenta
una corrida en RTX 3090 real ni un build Linux reproducido. El upstream Strata
v0.1.38 sirve de base, mientras el Strata local disponible para Q4 es v0.1.35.

## Hardware local y bloqueo

- 2× RTX 3090 de 24 GiB, compute capability 8.6; 123 GiB RAM.
- `nvcc` local es CUDA 12.0. El fork publica su build/test en CUDA 13.3; falta
  validar si el fallback sm_86 compila con CUDA 12 y Linux.
- Espacio libre observado al retomar: 27 GiB en `/media/cristian/Disco local`,
  30 GiB en HDD extra; tampoco había 280 GiB en la raíz ext4. El workspace sí
  contenía una conversión NVFP4 reutilizable, así que se hizo una prueba
  acotada antes de descubrir que la fila activa de cola exigía el margen de
  staging completo. No se descargó ni se borró ningún modelo.
- Preparación descrita por el fork: checkpoint ModelOpt de 126 GiB, tabla PLE
  de 51.2 GB, pack experto de unos 63 GiB, además del GGUF, embedding, MTP,
  temporales y espacio de build. Una cota prudente de staging es ~280 GiB
  libres en un volumen; los volúmenes actuales no alcanzan. No se borraron ni
  movieron otros modelos para abrir espacio.

## Prueba parcial del artefacto local

Se cargó el ejecutable local del fork `992195498c16ea2b26c08bf1ba2402291553136f`
en una RTX 3090, single-GPU. El log indica Strata v0.1.38, pack NVFP4 de
`/media/cristian/HDD extra/strata-nvfp4-review-20261003/pack/nvidia-nvfp4`,
GGUF local `nvidia-qwen38-nvfp4.gguf`, PLE FP8, MTP y contexto máximo 131072.
El primer arranque tardó aproximadamente 859 s en leer el pack desde HDD. Una
petición HTTP pequeña respondió el texto exacto solicitado (73 tokens de
prompt, 49 de salida, 15.7 tok/s de prompt y 11.2 tok/s de decode; 31/45 tokens
draft aceptados). Esto sólo valida que el artefacto puede contestar un smoke
simple; no valida LC-H1 ni superioridad frente a SOL.

La corrida LC-H1 aislada usó HarnessSpec `cca4645…8832ef`, agente `agent-maximo`,
seed 4242, thinking activado y el suite HE0 de 1 ítem. HE0 **no pasó**: tras dos
reparaciones no se creó `solution_HumanEval_0.py`, el resultado persistido fue
0/1 y el servidor devolvió `Connection refused`. El log del primer servidor
registra un watchdog de Strata que abortó el motor durante prefill de un prompt
de 12966 tokens; el arranque automático posterior no recuperó el endpoint. Un
segundo intento con `--prefill auto:2048` seguía sin endpoint a los ~549 s y se
detuvo para liberar recursos y respetar el prerrequisito de la cola. No se
ejecutaron HE20, BCB8 ni Adversarial, ni se modificó ningún perfil de producción.

La procedencia del checkpoint cargado **no quedó probada**: los nombres del
pack/GGUF dicen NVIDIA, mientras la tarea de cola describe el fork como adaptación
del checkpoint OrcaRouter/ModelOpt. El log de conversión sólo registra el nombre
local `strata-qwen38-nvfp4-review-20261003`, sin repositorio ni revisión HF. Por
eso esta corrida no debe atribuirse a ninguno de esos repositorios ni compararse
como resultado definitivo. En la reanudación hay que resolver primero la identidad
y fijar el commit del modelo; luego contar con ~280 GiB libres (o volumen
alternativo), verificar los hashes de todos los insumos y repetir el smoke y el
gate HE0 con arranque estable antes de habilitar suites mayores.

## Evidencia anterior que no se debe mezclar

El candidato Swift Genesis NVFP4 guardado en
[`docs/swift-genesis-qwen38-evaluation-20260929.md`](swift-genesis-qwen38-evaluation-20260929.md)
sí tiene una corrida LC-H1 reproducible: HE0 1/1; HE20 20/20 en 758.8 s; BCB8
2/8 en 417.4 s; adversarial se canceló sin score. El BCB8 fallido detiene la
promoción. Es otro checkpoint, se ejecutó con `llama.cpp`, thinking apagado y
otra huella de perfil; no demuestra calidad ni rendimiento del fork Strata
NVFP4 actual. No repetir esa corrida guardada para fabricar una comparación
con el nuevo checkpoint.

La evaluación reciente Strata UD-Q4_K_XL queda en
[`docs/strata-udq4-38ram-lch1-20261004.md`](strata-udq4-38ram-lch1-20261004.md):
HE20 expiró, BCB8 no se habilitó y Adversarial empató a SOL en score final pero
fue 3.84× más lenta. Tampoco es el checkpoint ModelOpt NVFP4.

## Fuentes técnicas revisadas

- [README y método/build del fork Strata NVFP4](https://github.com/sergqwer/strata-nvfp4)
- [Checkpoint ModelOpt usado por el fork](https://huggingface.co/jpezzulli/OrcaRouter-Qwen3.8-Flash-Next-Uncensored-ModelOpt-NVFP4)
- [Variante alternativa con PLE FP8](https://huggingface.co/lychee888/Qwen3.8-Flash-Next-Uncensored-NVFP4-FP8PLE); no se asume compatible hasta revisar el layout y los hashes.

## Actualización 2026-10-05: checkpoint OrcaRouter verificado

La prueba histórica de esta auditoría (artefactos llamados NVIDIA, procedencia sin fijar) debe mantenerse separada del checkpoint probado después. En Q-20261005-REDDIT-NVFP4 se descargó/verificó el checkpoint exacto OrcaRouter ModelOpt `f24d2b68ff2814f24455ae86717be276619b5664`, se verificaron tensores NVFP4 y escalas y se ejecutó el fork sobre 2× RTX 3090. Por lo tanto, la identidad del candidato nuevo sí está establecida; esto **no** retrovalida ni cambia la identidad de los artefactos del ensayo del 4 oct.

En la evaluación nueva las llamadas cortas OpenAI/tool-call funcionaron. El prefill automático de 16K y los bloques de 8K/4K fijo dispararon el watchdog interno de Strata (#29): 60 s sin progreso en el primer chunk. Un bloque fijo de 2K sí completó HE0 con una reparación (1/1 en 355,284 s), pero no se ejecutó LC-H1 completo; esa latencia y evidencia de un solo ítem no justifican promoverlo. Los 0/1 de los intentos sin tokens no son scores de calidad válidos. Sin cambios productivos. Evidencia y decisión completa: [`docs/strata-nvfp4-reddit-20261005.md`](strata-nvfp4-reddit-20261005.md).
