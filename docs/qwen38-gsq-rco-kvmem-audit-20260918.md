# Qwen3.8 GSQ/RCO IQ3_S + KVMem — auditoría local

Fecha: 2026-09-18  
Equipo: Ubuntu, Ryzen 9 9950X3D, 2× RTX 3090 24 GB, P2P disponible  
Modelo: `ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF`  
Artefactos locales:

- `/media/cristian/7CFE1E0FFE1DC1F6/models/Qwen3.8-27B-GSQ-RCO-IQ3_S/Qwen3.8-27B-GSQ-RCO-IQ3_S-mtp.gguf` (~11,8 GB)
- `/media/cristian/7CFE1E0FFE1DC1F6/models/Qwen3.8-27B-GSQ-RCO-IQ3_S/mmproj-Qwen3.8-27B-BF16.gguf` (~0,91 GB)

## Motivo de la prueba

El post revisado recomienda GSQ-RCO IQ3_S en 81.920 tokens y enlaza dos
ramas de adaptive-KV, además de KVMem. A diferencia del candidato GSQ/RCO
anterior de ~152 GB, este repositorio publica un GGUF IQ3_S-MTP descargable
de ~12,1 GB y un `mmproj` separado, por lo que sí era razonable medirlo.

Se compiló `kvmem/kvmem-llama.cpp` v0.16.0-rc1, con llama.cpp pin
`b81c99b`, parche KVMem actual, CUDA 12.8 y `CMAKE_CUDA_ARCHITECTURES=86`.
La documentación de KVMem recomienda CUDA 13.2.86; por eso los resultados de
esta build se consideran experimentales en SM86.

## Resultados reproducibles

### Runtime CUDA estándar, 2×3090, KV Q8, 8K

| Configuración | PP | TG | MTP | Resultado |
|---|---:|---:|---|---|
| IQ3_S-MTP sin MTP | 297,1 | 39,57 | — | Salida Python correcta |
| IQ3_S-MTP + MTP3 | 165,0 | 52,53 | 57/109, ~52% | Smoke funcional |
| IQ3_S-MTP + MTP3 + visión GPU | 448,1* | 58,04 | 40/68, ~59% | `mmproj` responde correctamente |

\* Incluye 282 tokens de prompt multimodal; no es comparable con un prompt de
texto puro.

### Contexto largo con runtime estándar

Con `--ctx-size 81920`, MTP3 y un prompt de 42.067 tokens:

- prefill: **1.025,27 PP**;
- decode: **44,32 TG**;
- aceptación MTP: 19/34 tokens verificados;
- salida y proceso estables.

Una solicitud que excedía 81.920 tokens fue rechazada correctamente por el
límite configurado; no fue un crash.

### KVMem, una RTX 3090, KV Q8, ventana GPU 32K + reserva 12K

| Prueba | Resultado |
|---|---|
| Texto corto | Correcto; **41,99 TG**, prefill 344 ms |
| Tool-use | Correcto: emitió `add({"a":2,"b":3})` con `finish_reason=tool_calls` |
| Visión con `mmproj` en CPU | Correcta; encoding ~3,67 s, generación ~41,98 TG |
| 42.067 tokens | Correcto; 64,02 s de prefill (~657 PP), **46,45 TG**, MTP 23/27 = 85,2% |
| 73.567 tokens | Correcto; 58,27 s de prefill (~1.262 PP por reutilización de prefijo), **35,20 TG** |
| Visión con `mmproj` en GPU | **Falla** con `CUDA illegal memory access` antes de generar texto |

La corrida de 73.567 tokens tuvo 41.548 tokens de prefijo reutilizados; por
eso su PP no representa una carga completamente fresca. KVMem sí demostró que
puede mantener el workspace lógico de 262K y recuperar contexto desde RAM,
pero no se validó todavía una recuperación semántica tipo NIAH ni un BCB8
completo.

## Comparación con SOL

| Perfil | PP/TG observados | Calidad/tool-use | Contexto/visión | Decisión |
|---|---:|---|---|---|
| SOL | 74 narrativo / 102 código | BCB 8/8, tool-use estable | 262K, visión validada | Default |
| GSQ-RCO estándar | 297 PP / 39,6 TG sin MTP; 165 PP / 52,5 TG con MTP | Smoke y tool-use no equivalen a BCB8 | 81.920 probado; visión GPU funcional | Experimental |
| GSQ-RCO + KVMem | 42–46 TG; 35 TG a 73K | Tool-use funcional; BCB8 pendiente | 73.567 probado; visión sólo CPU confiable | Experimental de contexto |

## Decisión

El post sí aportó una ruta útil: **GSQ-RCO IQ3_S + MTP + KVMem** es una
alternativa real para contexto largo con menos VRAM, y además conserva
tool-use y visión por CPU. No supera a SOL en velocidad, calidad demostrada,
visión GPU ni estabilidad general:

- no se cambia el default SOL;
- no se agrega al dropdown prioritario;
- se conserva el modelo descargado para pruebas de contexto largo;
- KVMem queda como runtime experimental separado, no integrado todavía en el
  flujo normal de LlamaCode;
- no se repite la prueba adaptive-KV anterior: esa ruta ya había llegado a
  ~5,25 TG a 131K y no recuperó correctamente la passkey NIAH.

El fallo GPU de KVMem debe repetirse con CUDA 13.2.86 antes de atribuirlo
definitivamente al fork. No se dejó ningún servidor de prueba ejecutándose.
