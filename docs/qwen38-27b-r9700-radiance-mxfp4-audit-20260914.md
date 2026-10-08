# Auditoría: Qwen3.8-27B en 2× Radeon R9700 con Radiance/MXFP4

Fecha: 2026-09-14  
Estado: evaluado, sin promoción de perfil

## Fuente evaluada

La publicación reporta Qwen3.8-27B ejecutado en dos Radeon AI PRO R9700 (RDNA4,
32 GB cada una), con un fork de vLLM/Radiance, kernels MXFP4 W4A8 y DFlash2.
El informe declara entre 116 y 280 tok/s según la categoría y entre 3.106 y
4.894 tok/s de prefill según la longitud del prompt. Los números son del autor,
no una medición reproducida en LlamaCode.

Fuentes:

- [Publicación original](https://www.reddit.com/r/Qwen_AI/comments/1w577ca/how_i_got_280_toks_on_2xr9700s_and/)
- [Fork Radiance MXFP4](https://codeberg.org/ggz14/radiance-vllm-mxfp4)
- [BetterBench](https://github.com/GGZ14/BetterBench)

## Comparación con nuestro equipo

| Candidato | Hardware/backend | Resultado local o reportado | Decisión |
| --- | --- | ---: | --- |
| Radiance + MXFP4 + DFlash2 | 2× Radeon R9700, ROCm/vLLM especializado | 116–280 tok/s; 3.106–4.894 tok/s prefill | No comparable ni ejecutable en nuestras RTX 3090 |
| SOL | 2× RTX 3090, vLLM TP2/P2P, AutoRound INT4, MTP4, KV FP8 | 74 tok/s narrativo; 102 tok/s código; BCB 8/8; tool-use OK | Se mantiene como predeterminado |
| DFlash2 sobre SOL | 2× RTX 3090, vLLM TP2/P2P | 92,8 tok/s narrativo y ~171 tok/s en prompts cortos, pero `CUDA device-side assert` con prefill de 512; el workaround estable exige KV BF16 | Rechazado por estabilidad y por superar el límite Q8 de KV |
| QWEN38-Q8 | llama.cpp, Q8, contexto extremo | 41,3 tok/s a 8K; ~22,1 tok/s a 262K; smoke funcional | Experimental; no reemplaza SOL |

## Qué sí sirve

1. **Separar las categorías de carga.** Conviene conservar mediciones
   diferenciadas para código, edición de archivos, razonamiento, resumen,
   conversación y texto libre. Un único promedio escondería que el rendimiento
   cambia mucho con el patrón de uso.
2. **Medir prefill por profundidad de contexto.** Para agentes, la curva a 8K,
   32K, 80K y contexto máximo es más útil que el pico con prompt vacío.
3. **Registrar el backend y el hardware junto al número.** Los kernels MXFP4,
   la arquitectura RDNA4 y DFlash2 son parte esencial del resultado; no debe
   compararse directamente con CUDA/RTX 3090.

LlamaCode ya tiene benchmarks por categoría y pruebas BCB; por eso no fue
necesario introducir código nuevo. El procedimiento queda como referencia para
una futura batería de rendimiento, sin alterar los perfiles existentes.

## Qué no conviene incorporar

- No instalar Radiance/vLLM ROCm: la máquina actual tiene dos RTX 3090 y ese
  backend requiere kernels y hardware AMD RDNA4.
- No convertir el resultado externo en una mejora de SOL: la cuantización,
  arquitectura GPU, backend y configuración de especulación no son equivalentes.
- No reactivar DFlash2 con KV BF16: aunque puede evitar el `device-side assert`,
  viola el límite operativo del proyecto (cuantización máxima Q8, incluida la
  caché KV) y ya mostró degradación en sesiones largas.

## Resultado final

No se descarga ningún modelo ni se modifica el dropdown. SOL continúa como
perfil principal. La única mejora aplicable es metodológica: reportar por
categoría y por profundidad de contexto, manteniendo separados los resultados
externos de AMD de las mediciones reproducibles en nuestras RTX 3090.

## Revisión del reporte NVFP4→MXFP4 — 2026-09-18

Se revisó un nuevo reporte que declara **5.809 tok/s de prefill y 276 tok/s de
decode** con Qwen3.8-27B NVFP4. El resultado usa dos Radeon R9700 y un fork de
Radiance/vLLM que convierte NVFP4 a MXFP4 en línea para aprovechar un kernel
MXFP4 específico de RDNA4. No es una receta trasladable a CUDA/SM86:

| Elemento | Reporte | Nuestro setup |
| --- | --- | --- |
| GPU/backend | 2× Radeon R9700, ROCm/Radiance | 2× RTX 3090, CUDA/vLLM o llama.cpp |
| Ruta de pesos | NVFP4→MXFP4 online | NVFP4 admitido sólo por dequantización A16 |
| Especulación | DFlash2 en el fork | SOL MTP4 estable; DFlash2 ya tuvo `device-side assert` |
| Resultado | 5.809 PP / 276 TG publicados | SOL: 74 narrativo / 102 código, BCB 8/8 |
| Validación | BetterBench del autor | BCB, HE y tool-use locales |

No se intentó instalar Radiance/ROCm ni descargar otra copia NVFP4: sería
incompatible con las GPU actuales y no produciría una comparación limpia. La
auditoría local ya comprobó que DFlash2 sobre SOL puede dar más TG en prompts
cortos, pero falla con prefill de 512 tokens y el workaround estable necesita
KV BF16, fuera del límite Q8.

### Sampling reutilizable

El reporte reabre una distinción válida de Qwen, pero no justifica cambiar SOL
sin una nueva evaluación BCB:

| Modo | Receta de referencia Qwen | Uso en LlamaCode |
| --- | --- | --- |
| Thinking | `temp=1.0`, `top-p=0.95`, `top-k=20`, `min-p=0`, penalties neutras | Útil para un perfil explícito de razonamiento |
| Instruct/no-thinking | `temp=0.7`, `top-p=0.80`, `top-k=20`, `min-p=0`, presence 1.5 | Útil para respuestas rápidas, no para SOL thinking |
| SOL actual | `temp=0.6`, `top-p=0.95`, `top-k=20`, `min-p=0`, penalties neutras | Se conserva: fue la receta de BCB 8/8 y tool-use estable |

La prueba local de sampling ya mostró 4/4 respuestas limpias con `temp=0` y
4/4 con `temp=0.6`; no mostró una ventaja agentiva reproducible de `temp=1.0`
que compense cambiar la configuración validada. `temp=0` queda como modo de
diagnóstico de corrupción, no como default.

**Decisión:** el reporte no agrega un perfil ejecutable ni supera a SOL en una
métrica comparable. Se conserva como referencia AMD/MXFP4 y como recordatorio
de medir PP/TG por contexto, sin modificar el dropdown ni dejar servicios
persistentes.
