# Auditoría de factibilidad local de GLM-5.3-Flash — 2026-09-14

## Resultado

GLM-5.3-Flash es un candidato interesante para una futura máquina o backend,
pero no es incorporable hoy a los perfiles locales de LlamaCode.

La ficha oficial lo describe como un modelo multimodal de aproximadamente
320B parámetros totales y 18B activos, con despliegue documentado para
SGLang, vLLM, TokenSpeed, Transformers, KTransformers y Unsloth. La publicación
de Reddit no aporta una medición reproducible en nuestras dos RTX 3090.

## Verificaciones en esta PC

| Verificación | Resultado |
| --- | --- |
| GPUs | 2 × RTX 3090, SM 8.6, 24 GiB cada una |
| VRAM combinada | 48 GiB |
| RAM disponible para inferencia | aproximadamente 128 GiB |
| Pesos GLM-5.3-Flash locales | No encontrados |
| Cuantización GLM local | No encontrada |
| Perfil LlamaCode existente | No |
| Imagen vLLM local `0.27.1` | No contiene implementación GLM5/GLM5Next |
| LayerStoRm | No compatible: requiere SM120/RTX 50xx |

El inventario sólo contiene fuentes y conversiones relacionadas con GLM-5.2,
no un artefacto GLM-5.3-Flash listo para cargar. Los GGUF publicados para este
modelo aparecen como variantes de más de 300B parámetros; no se descargó ninguno
porque no hay una ruta validada para ejecutarlo en SM86 y el espacio local es
limitado.

## Comparación con nuestros perfiles

| Perfil local | Evidencia actual | Decisión |
| --- | --- | --- |
| SOL | Qwen3.8 TP2/P2P + MTP4, 74 tok/s narrativo / 102 código, BCB 8/8, tool-use OK | Mantener default |
| GALACTA | DeepSeek V4 Flash, BCB 8/8, ~9,65 tok/s | Mantener como calidad máxima local |
| TERRA/LUNA/METEOR | Perfiles locales ya probados con otros modelos | No reemplazar sin benchmark comparable |
| GLM-5.3-Flash | Sin pesos, backend local compatible ni BCB | No agregar |

## Qué sí vale conservar como idea

- Evaluar la arquitectura híbrida sparse/linear para contexto largo.
- Probarlo en el futuro mediante el backend oficial más reciente, no con la
  imagen vLLM Qwen fijada actualmente.
- Exigir antes de promoverlo: artefacto por debajo del presupuesto de memoria,
  soporte CUDA SM86, smoke de texto, visión, tool-use, HE0/HE20/BCB y medición
  de cold/warm prefill.

No se descargaron pesos, no se modificó ningún perfil, no se cambió el default
y no se dejó ningún servicio ejecutándose.

## Revisión del anuncio de Reddit — 2026-09-14

El anuncio sólo confirma la disponibilidad del modelo y enlaza el soporte de
Unsloth; no aporta una medición reproducible en RTX 3090. La ficha oficial
actual describe a GLM-5.3-Flash como un modelo multimodal de aproximadamente
321B parámetros, con 18B activos, y documenta despliegue mediante SGLang,
vLLM, TokenSpeed, Transformers, KTransformers y Unsloth. También indica que el
control de razonamiento usa `reasoning_effort=low|high|max` y que el valor por
defecto es `max`.

La cuantización local más pequeña mencionada por el anuncio es NVFP4, de unos
181 GB sólo para los pesos. En esta revisión el volumen de modelos de
LlamaCode tenía aproximadamente 22 GB libres, por lo que descargarla habría
dejado el sistema sin margen y, aun con el modelo descargado, los 48 GiB de
VRAM más la RAM disponible no dejan una ruta prudente para pesos, caché y
runtime en esta máquina.

### Comparación actualizada

| Candidato | Resultado local | Decisión |
|---|---|---|
| GLM-5.3-Flash NVFP4 | No descargable de forma responsable; 181 GB de pesos y sin backend local validado para nuestro SM86 | No agregar |
| GLM-5.3-Flash BF16 | 585 GB declarados; fuera de memoria y almacenamiento | Descartado |
| SOL | 74 tok/s narrativo, 102 tok/s código, BCB 8/8 y tool-use OK | Mantener default |
| GALACTA | BCB 8/8, aproximadamente 9,65 tok/s | Mantener como calidad local validada |

No hay una prueba adicional ejecutable que pueda demostrar superioridad de GLM
frente a SOL sin introducir una descarga masiva y un backend nuevo. Por lo
tanto, este anuncio no cambia el dropdown ni la tabla de perfiles. Queda como
candidato para una máquina con más memoria o para un entorno remoto; si aparece
un artefacto cuantizado realmente menor, el gate requerido será smoke de texto,
visión, tool-use, HE0, HE20, BCB y medición de contexto con la misma huella que
SOL.

Referencia primaria actualizada: [ficha oficial de GLM-5.3-Flash](https://huggingface.co/zai-org/GLM-5.3-Flash).

Referencias:

- [Ficha oficial GLM-5.3-Flash](https://huggingface.co/zai-org/GLM-5.3-Flash)
- [Ficha oficial GLM-5.3-Flash-BF16](https://huggingface.co/zai-org/GLM-5.3-Flash-BF16)
- [Auditoría previa de LayerStoRm](layerstorm-linux-evaluation-20260908.md)
