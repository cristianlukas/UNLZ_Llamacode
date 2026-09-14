# Auditoría de BridgeSpec para LlamaCode — 2026-09-14

## Resultado

BridgeSpec es una integración experimental de speculative decoding para
Qwen3.8-27B en una RX 7900 XTX. Aporta un sidecar HIP para MTP/DFlash y tuning
de kernels RDNA3, pero no es una ruta ejecutable ni reproducible en las dos RTX
3090 de LlamaCode.

Fuente revisada: [repositorio oficial de BridgeSpec](https://github.com/kdheeraj-p/bridgespec).
El propio repositorio limita la validación a Windows 11, una RX 7900 XTX,
ROCm/HIP 7.2 y una revisión fijada de `llama.cpp`; no publica binarios ni
artefactos derivados y declara que no es todavía un runtime general.

## Qué muestran sus números

| Configuración BridgeSpec | Código | Edición agéntica | Prosa | Lectura |
|---|---:|---:|---:|---|
| Vulkan MTP control | 104,5 | 117,7 | — | Línea base |
| Vulkan + sidecar HIP MTP | 106,9 | 120,7 | — | Mejora pequeña: ~2,3% |
| HIP DFlash de desarrollo | 109,4 | 146,0 | 56,8 | Pico dependiente del workload |
| HIP DFlash release candidate | 84,2 | 111,8–112,4 | 43,7 | Más realista, pero irregular |

La propia documentación aclara que las cifras son sólo decode, excluyen
prefill/TTFT y dependen de aceptación, caché, contexto y carga. En la curva de
contexto reportada, el target Vulkan quedó por encima del sidecar HIP a ~127K
(52,29 frente a 49,35 tok/s), así que el sidecar no ofrece una ventaja general
para contexto largo.

## Cruce con LlamaCode

| Candidato/idea | Evidencia local | Decisión |
|---|---|---|
| MTP adaptativo | El concepto podría evitar elegir una profundidad fija, pero no forma parte de nuestro binario validado | No activar sin port y BCB |
| Sidecar HIP MTP | Requiere HIP/RDNA3; nuestras GPU son CUDA/SM86 | No ejecutable |
| DFlash sidecar | Sólo Windows/RX 7900 XTX y muy dependiente de aceptación; prosa cae a 43,7–56,8 tok/s | No promover |
| ngram-mod | Ya existe en la matriz, pero las variantes Flash-Next locales dieron salida corrupta o menor velocidad | Mantener sólo experimental |
| SOL | 74 tok/s narrativo / 102 código, BCB 8/8, tool-use OK y contexto 262K validado | Mantener default |

Los 120,7 tok/s agénticos de BridgeSpec no se pueden usar para reemplazar SOL:
se obtuvieron a 16K en otra GPU, otro backend, otro sistema operativo y con un
sidecar no generalizado. Además, la ganancia controlada es pequeña y no hay BCB,
HE0/HE20 ni tool-use de LlamaCode.

## Decisión operativa

- No se descarga ni integra BridgeSpec.
- No se cambia SOL ni el orden del dropdown.
- No se agrega un perfil DFlash/MTP adaptativo sin una implementación CUDA
  compatible y una validación completa de corrección, BCB y tool-use.
- La idea reutilizable queda anotada: medir aceptación por workload y separar
  código, edición agéntica, prosa, contexto y prefill antes de promover
  speculative decoding.

Las pruebas locales anteriores de ASTRA ya cubrieron las palancas relevantes:
`lazy on` produjo salida corrupta, `on-direct` fue válido pero bajó a ~7,54
tok/s, y las variantes MTP/NGRAM no quedaron estables. Por eso no hace falta
repetir una prueba que requiere un backend AMD ausente en esta máquina.
