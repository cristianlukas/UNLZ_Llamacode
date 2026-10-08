# Auditoría MTP y visión de perfiles objetivo — 2026-09-15

## Alcance

Se compararon **METEOR/BigBang**, **QWEN35-A3B**, **CyberTiel** y
**Qwen3.5-9B/4B/2B**. La prueba local usa la misma build CUDA de llama.cpp
adaptada a SM86, las dos RTX 3090 con P2P cuando el modelo lo necesita,
Flash Attention, pesos Q4 y KV `q8_0` como máximo. No se usó ninguna
cuantización de pesos ni KV superior a Q8.

Las métricas de PP/TG son comparables entre sí dentro de esta campaña, pero
no sustituyen automáticamente los resultados históricos de BCB/HE obtenidos
con otro harness, contexto o backend.

## Resultados reproducibles

### Texto: control sin MTP frente a MTP

| Perfil | Configuración | PP sin MTP | TG sin MTP | PP con MTP | TG con MTP | Cambio TG |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Qwen3.5-2B | Q4, GPU única, KV Q8 | 636,2 | 273,4 | 551,6 | **318,9** | **+16,6%** |
| Qwen3.5-4B | Q4, GPU única, KV Q8 | 498,1 | 153,0 | 432,8 | **200,0** | **+30,7%** |
| Qwen3.5-9B | Q4 MTP autocontenido, GPU única, KV Q8 | 434,1 | 106,1 | 285,3 | **166,1** | **+56,5%** |
| CyberTiel 35B-A3B | Q4, TP por capas/P2P | 1.063,3 | 136,8 | 956,7 | **154,3** | **+12,8%** |
| QWEN35-A3B GGUF | Q4_K_XL, TP por capas/P2P, texto | 378,5 | 140,2 | 399,7 | **207,8** | **+48,2%** |

En Qwen3.5-9B se comparó el mismo artefacto MTP en ambos modos. El control
anterior con el Q4 text-only original dio 757,4 PP y 103,7 TG, por lo que no
se debe interpretar la diferencia de PP entre artefactos como un efecto de
MTP.

### Visión + MTP en el servidor

Se envió la misma captura de 768 px con el texto `LlamaCode / P2P VISION
2026` a cada servidor. Los cuatro perfiles cargaron `mmproj` y el cabezal MTP
en el mismo proceso; no fue una prueba separada de visión solamente.

| Perfil | PP | TG | Aceptación MTP | Resultado visual |
| --- | ---: | ---: | ---: | --- |
| Qwen3.5-2B | 1.812,6 | **344,8** | 66/83 = **79,5%** | Leyó ambas líneas |
| Qwen3.5-4B | 1.445,0 | **206,6** | 64/92 = **69,6%** | Leyó ambas líneas |
| Qwen3.5-9B | 1.099,8 | **144,2** | 43/59 = **72,9%** | Leyó la imagen correctamente |
| CyberTiel 35B-A3B | 980,2 | **155,9** | 23/39 = **59,0%** | Devolvió el texto exacto |
| Qwen3.5-4B CPU | 185,8 | **23,1** | 43/59 = **72,9%** | Leyó la captura en el Ryzen 9 9950X3D |

La advertencia de llama.cpp recomienda `--image-min-tokens 1024` para tareas
de grounding Qwen-VL. No es necesario para esta captura simple, pero queda
como ajuste recomendado cuando LlamaCode procese capturas pequeñas o UI
compleja.

## Artefactos disponibles

- Qwen3.5-2B: `Qwen3.5-2B-Q4_K_M.gguf` + `mmproj-BF16.gguf`.
- Qwen3.5-4B: `Qwen3.5-4B-Q4_K_M.gguf` + `mmproj-BF16.gguf`.
- Qwen3.5-9B: variante MTP de `unsloth/Qwen3.5-9B-MTP-GGUF` + `mmproj-BF16.gguf`.
- CyberTiel: `Cyber-Tiel-Coder-35B-A3B-MTP-UD-Q4_K_XL.gguf` + `mmproj-BF16.gguf`.
- QWEN35-A3B: `Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf` de
  `unsloth/Qwen3.6-35B-A3B-MTP-GGUF` + `mmproj-BF16.gguf`, instalados en
  `/media/cristian/Disco local/Models/llamacpp/Qwen3.6-35B-A3B-MTP`.
- METEOR: BigBang Q4_K_M (21,86 GB) y su `mmproj` BF16 están en
  `/media/cristian/Disco local/Models/llamacpp/BigBang-v1-Q4_K_M-GGUF`.

Los repositorios Qwen3.5 publican variantes MTP y proyectores de visión; la
integración local usa los archivos GGUF correspondientes y no agrega una
cuantización fuera de la política. CyberTiel ya incluía MTP y `mmproj` en el
artefacto local. BigBang publica `mmproj`, pero no un archivo MTP separado en
el repositorio consultado; en el GGUF Q4_K_M descargado el cabezal sí está
embebido y MTP cargó correctamente.

### METEOR/BigBang

| Modo | PP | TG | Aceptación MTP | Visión |
| --- | ---: | ---: | ---: | --- |
| Texto, sin MTP, KV Q8 | 381,2 | 149,7 | — | — |
| Texto, MTP, `reasoning off`, KV Q8 | 335,9 | **207,0** | 97/149 = **65,1%** | — |
| Visión + MTP, KV Q8 | 742,9 | **195,3** | 67/115 = **58,3%** | Texto exacto correcto |

El MTP de BigBang mejora TG aproximadamente **38%** en el control textual
servido con el mismo backend. La prueba larga de 131K no se extrapola desde
este smoke de 8K; el perfil reparado debe conservar su límite operativo de
64K/B256/U64 hasta repetir una prueba de contexto largo.

## Calidad y decisión

La campaña nueva demuestra carga, generación, salida no corrupta, lectura
visual y beneficio de MTP. No convierte estas pruebas de humo en HE/BCB:

- **QWEN35-A3B** conserva su validación anterior: BCB 4/8, visión 4/4 y 262K
  en vLLM TP2/P2P.
- **METEOR** conserva el histórico BCB 3/8 hasta repetir el pack con el
  artefacto descargado; la ruta MTP+visión ya es reproducible en 8K.
- **CyberTiel** queda con HE/BCB pendientes; sus PP/TG actuales son fuertes,
  pero todavía no justifican reemplazar SOL como agente principal.
- **Qwen3.5-9B/4B/2B** quedan como auxiliares multimodales con MTP validado;
  todavía no tienen un BCB formal en esta campaña.
- **QWEN35-A3B GGUF MTP** mejoró el smoke textual a 207,8 TG, pero su guía
  indica que `--mmproj` no es compatible con MTP en ese modo. La visión sin
  MTP sí cargó y codificó la captura (385 ms), pero no se lo convierte en
  reemplazo de la variante vLLM, que conserva la validación 4/4 de visión,
  262K y BCB 4/8.

Decisión operativa:

1. Activar MTP y `mmproj` en los perfiles Qwen3.5-2B, 4B, 9B y en el fallback
   CPU de 4B.
2. Mantener CyberTiel como perfil experimental multimodal/concurrente, con
   MTP y visión habilitados.
3. Mantener QWEN35-A3B como perfil multimodal/concurrente de mayor contexto,
   sin cambiar su estado por estas pruebas; conservar el GGUF MTP como
   variante experimental de texto-only, no como default.
4. Mantener METEOR como throughput experimental: activar MTP+visión sólo en
   la variante reparada de 64K/B256/U64, sin cambiar el default SOL hasta
   completar el pack formal HE/BCB.
