# R9V para Qwen3.8 Flash-Next — auditoría de compatibilidad

Fecha: 2026-09-14  
Decisión: **no aplicable a nuestro equipo y no se integra en LlamaCode**.

## Qué propone

[R9V](https://github.com/Dyluhn/R9V) es un runtime de kernels especializados
para **ROCm/RDNA4**, orientado al perfil `dual-r9700-128k`. Su documentación
requiere dos Radeon AI PRO R9700 de 32 GiB, GPU `gfx1201`, `/dev/kfd`, `/dev/dri`
y `amd-smi`; además compila un fork de vLLM, AITER y kernels HIP específicos.
No es un backend CUDA ni una optimización portable de llama.cpp.

El perfil publicado es interesante por su combinación de MTP, expertos en
VRAM/UVA, PLE en SSD y visión. El proyecto declara aproximadamente 1.512 tok/s
de prefill y 78 tok/s de decode en **dos R9700**, pero sus propios documentos
aclaran que esos kernels sólo están calificados para `gfx1201` y que no deben
trasladarse a otra GPU sin rehacer la validación completa. Ver el
[README del proyecto](https://github.com/Dyluhn/R9V) y la
[guía de instalación](https://github.com/Dyluhn/R9V/blob/main/docs/installation.md).

## Pruebas locales

Hardware detectado:

- 2× NVIDIA GeForce RTX 3090, 24 GiB cada una.
- Driver NVIDIA 595.71.05.
- Linux con P2P CUDA operativo.

Se clonó el repositorio sin submódulos ni modelos y se ejecutó:

| Prueba | Resultado |
|---|---|
| `./r9v validate qwen38` | **PASS**: descriptor del perfil válido |
| `./r9v doctor qwen38` | **FAIL cerrado**: faltan submódulos de runtime/kernels, `amd-smi`, paquete del modelo y PLE |
| Descarga de modelo | No realizada |
| Build Docker/ROCm | No realizado |
| Benchmark | No corresponde al hardware |

El `doctor` también confirmó que Docker, `/dev/kfd`, `/dev/dri`, RAM de
123,5 GiB, CPU y espacio disponible están presentes, pero eso no compensa la
incompatibilidad fundamental: nuestras GPU no son AMD `gfx1201` y el host no
tiene el inventario ROCm requerido.

## Comparación con nuestros perfiles

| Candidato | Hardware/backend | Resultado local | Decisión |
|---|---|---|---|
| R9V Qwen3.8 IQ4_XS | 2× AMD R9700 + ROCm/HIP | No ejecutable en RTX 3090 | Descartado para esta PC |
| SOL | 2× RTX 3090 + vLLM TP2/P2P | 74 narrativo / 102 código; BCB 8/8 | Default |
| EXL3-QWEN38 | 2× RTX 3090 + ExLlamaV3 | 102–116 corto; 63,5 a 103K; BCB 1/8 | Experimental |
| ASTRA | llama.cpp/Flash-Next | 16–41 tok/s; calidad no válida | Experimental |

R9V no puede mejorar nuestra tabla porque sus cifras dependen de otro
acelerador, otro backend y kernels no compatibles con SM86. No se descargaron
los ~90 GiB del paquete ni el PLE adicional de ~26,8 GiB; no se ocupó espacio
en `models/`.

## Resultado operativo

- No se modificaron perfiles, dropdown, runtime ni servicios de LlamaCode.
- No se agregó R9V como perfil experimental: no sería ejecutable en esta PC.
- Se conserva únicamente el checkout fuente pequeño en la caché de trabajo para
  referencia; no es una dependencia de LlamaCode.

