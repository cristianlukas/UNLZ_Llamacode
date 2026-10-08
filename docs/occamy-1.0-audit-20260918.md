# Auditoría local: Occamy-1.0 Q4_K_M

Fecha: 2026-09-18. Hardware: 2× RTX 3090, Ubuntu, `llama-server` CUDA local
`1 (67849b6)`, reparto por capas y P2P habilitado por la ruta habitual.

## Artefactos

Los archivos se guardaron en `/media/cristian/7CFE1E0FFE1DC1F6/models/Occamy-1.0-Q4_K_M/`:

| Archivo | Tamaño | SHA-256 |
|---|---:|---|
| `occamy-1.0-Q4_K_M.gguf` | 21.166.757.696 bytes | `ffb25f763ff9c27f5f4e2adcdef399c5654f9f840fdac33dffe7035ba8266a87` |
| `mmproj-occamy-1.0-F16.gguf` | 899.282.944 bytes | `8f827a1e495f23e987686a7f55c26064270502a5b6ee954a828f1aec0b2fd400` |

## Pruebas locales

Receta común: `--split-mode layer --tensor-split 1,1 -ngl 999`, batch 512,
ubatch 128, Flash Attention, KV Q8 (`q8_0` en K/V), una sesión, sampling
conservador y sin MTP.

| Prueba | PP | TG | Resultado |
|---|---:|---:|---|
| Texto, 8K | 233,09 | **164,07** | Código Python válido |
| Texto, 262K | 131,90 | **162,96** | Carga estable; salida válida |
| Visión, 32K | 175,65 | **162,68** | Leyó correctamente texto y colores de la imagen sintética |
| Tool-use, 8K | 890,07 | **164,08** | `finish_reason=tool_calls`; `add(17,25)` correctamente emitido |

La latencia de prompt del caso de tool-use no es comparable con la prueba de
texto porque el prompt era mucho más corto; el TG sí es comparable como
medición de decode bajo la misma receta.

## Comparación con perfiles actuales

Occamy supera en velocidad de decode local a QWEN35-A3B (123,98 BCB / 134,4
TG directo) y CyberTiel (154,3 TG con MTP; 155,9 TG en visión) en esta máquina,
además de mantener 262K y visión funcional. La comparación de calidad todavía
no está cerrada: no se le asigna BCB8 hasta correr el mismo harness LC-H1 y el
mismo pack que los perfiles existentes. Por eso se agrega como experimental y
no se cambia el default SOL.

El modelo base oficial describe un agente/co-work de 35B-A3B con arquitectura
de 262K y encoder visual. Sus resultados publicados de Claw-Eval, BFCL,
AutomationBench y Terminal-Bench fueron obtenidos fuera de nuestra máquina y
no reemplazan las métricas locales.

## MTP y límites

El GGUF oficial descargado no trae el head MTP. El model card ofrece un head
separado/experimental, pero no se combinó porque todavía no hay una pareja
local validada ni una prueba de aceptación comparable. La cifra de 163 TG es
por lo tanto sin especulación y ya es superior a los perfiles multimodales
experimentales actuales.

No se ejecutó BCB LC-H1 en esta pasada: el evaluador local arrastra una
incompatibilidad de dependencias Python (NumPy/Bottleneck/Pandas) en la ruta
directa y no corresponde inventar un puntaje ni mezclar un BCB directo con el
score agentivo histórico. Próximo experimento reproducible: reparar/aislar el
entorno LC-H1 y correr Occamy, SOL, QWEN35-A3B y CyberTiel en la misma sesión,
con la misma temperatura, timeout, herramientas y número de reintentos.

## Decisión

Se incorpora el perfil `sys-occamy-35b-q4km-262k` en `assets/system_profiles.json`.
Queda disponible sólo para hardware de 48 GB, con visión y tool-use habilitados,
sin MTP, como candidato de alto throughput multimodal. No reemplaza SOL hasta
tener BCB agentivo comparable y una prueba de estabilidad en sesiones largas.

Fuentes externas consultadas:

- [Occamy-1.0, model card oficial](https://huggingface.co/Accio-Lab/occamy-1.0)
- [Occamy-1.0-GGUF, archivos y notas oficiales](https://huggingface.co/Accio-Lab/occamy-1.0-GGUF)
