# Auditoría de FreeToken para LlamaCode — 2026-09-14

## Resumen

FreeToken es una alternativa interesante para modelos MoE grandes porque
combina cache de expertos en GPU, streaming desde RAM/PCIe, ejecución híbrida
CPU-GPU y cache de prefijos. Su documentación actual declara soporte para
Qwen3.8-Flash-Next mediante checkpoints Hugging Face FP8 o NVFP4, además de
API OpenAI/Anthropic y entrada de imágenes.

La publicación evaluada usa un checkpoint Flash-Next compatible con FreeToken,
pero sus 73,6 tok/s corresponden a otra máquina, otro checkpoint y una prueba
corta. No es una medición comparable con SOL ni una validación de tool-use.

## Entorno probado

- Ubuntu, 2× RTX 3090, P2P PCIe disponible.
- Driver NVIDIA `595.71.05`.
- Toolkit del sistema: CUDA `12.8`.
- RAM: aproximadamente `123 GiB`.
- Espacio libre: aproximadamente `261 GB` en la partición secundaria.
- FreeToken nightly `0.1.2+g953565667`, con wheel de kernels CUDA 13.

La instalación se hizo en `/media/cristian/Disco local/LlamaCode-cache/` para
no consumir espacio de la partición casi llena del sistema ni modificar la
instalación de LlamaCode.

## Pruebas

### Instalación y hardware

La instalación desde código fue rechazada por una incompatibilidad correcta:
FreeToken exige que `nvcc` coincida con el CUDA de PyTorch, y el sistema sólo
tiene `nvcc 12.8` mientras el runtime esperado usa CUDA 13. Se instalaron los
wheels precompilados oficiales, y la verificación resultó:

```text
freetoken version 0.1.2+g953565667
torch 2.11.0+cu130
cuda available: True
GPU0 NVIDIA GeForce RTX 3090 (8, 6)
GPU1 NVIDIA GeForce RTX 3090 (8, 6)
```

Se ejecutó `ft bench bw` en ambas placas:

| GPU | CPU-MoE BF16 | PCIe gather | CPU-MoE NVFP4 | PCIe gather | Recomendación |
| --- | ---: | ---: | ---: | ---: | --- |
| RTX 3090 #0 | 30,3 GB/s | 11,4 GB/s | 32,3 GB/s | 11,5 GB/s | `hybrid` |
| RTX 3090 #1 | 34,0 GB/s | 12,2 GB/s | 35,4 GB/s | 12,2 GB/s | `hybrid` |

Esto confirma que el motor podría beneficiarse de la combinación RAM/PCIe en
esta máquina si se dispone de un checkpoint soportado.

### Checkpoint local disponible

Se intentó servir el checkpoint existente:

`/media/cristian/7CFE1E0FFE1DC1F6/models/club-3090/qwen3.8-27b-autoround-int4`

El servidor detectó correctamente el modelo, GPUs y TP2, pero terminó antes
de cargarlo con:

```text
NotImplementedError: quantization method 'auto-round' is not supported
```

No es un fallo de las GPUs ni de LlamaCode: es una incompatibilidad de formato
del checkpoint. Por eso no fue posible obtener tok/s, calidad o tool-use de
FreeToken con los pesos que ya están instalados.

### Checkpoint Flash-Next compatible

La documentación de FreeToken declara como compatibles los repositorios
`Qwen/Qwen3.8-Flash-Next-FP8` y variantes NVFP4. El repositorio base aparece
como un modelo de aproximadamente 180B; la variante NVFP4 publicada ronda los
120B según el catálogo consultado. Descargar cualquiera de ellos consumiría
una fracción muy grande del espacio restante y no garantiza que el rendimiento
supere SOL en dos RTX 3090 con 123 GiB de RAM.

No se descargaron esos pesos. Tampoco se modificó el catálogo de modelos ni se
creó un perfil que no pudiera reproducirse localmente.

## Comparación con LlamaCode

| Candidato | Evidencia local | Comparación | Decisión |
| --- | --- | --- | --- |
| FreeToken + Qwen3.8 AutoRound local | No carga: `auto-round` no soportado | Sin inferencia comparable | No promover |
| FreeToken + Flash-Next FP8/NVFP4 | No probado: faltan 120–180 GB de pesos compatibles | El número externo no es comparable | Pendiente, no default |
| ASTRA actual | Flash-Next GGUF; contexto largo experimental, calidad agéntica no válida | Ya está integrado, pero no reemplaza SOL | Mantener experimental |
| SOL actual | BCB 8/8, aproximadamente 74 tok/s narrativo y 102 tok/s código, 262K validado | Referencia estable de LlamaCode | Mantener default |

## Ideas reutilizables

Aunque no se promovió FreeToken, hay dos ideas aplicables más adelante:

1. Medir el ancho de banda CPU-MoE frente a PCIe por GPU y seleccionar
   automáticamente entre offload e híbrido.
2. Mantener la separación entre capacidad de contexto, cache de expertos y KV,
   sin confundir un pico de decode con rendimiento estable de una sesión
   agéntica.

Estas ideas no justifican cambiar SOL ni el perfil ASTRA actual. La integración
de otro backend exigiría además adaptar el ciclo de vida de servidores,
health-checks, tool-use y apagado para que FreeToken no quede ejecutándose
cuando LlamaCode está detenido.

## Decisión final

No se añadió FreeToken al dropdown ni se cambió ningún default. El resultado
positivo de hardware (`hybrid` en ambas 3090) queda documentado como evidencia
para una futura prueba con un checkpoint compatible, pero hoy no existe una
comparación local válida que permita desplazar a SOL.

