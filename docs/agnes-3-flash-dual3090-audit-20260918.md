# Auditoría local de Agnes-3.0-Flash Preview

Fecha: 2026-09-18  
Artefacto: `0xKitkat/Agnes-3.0-Flash-GGUF`  
Ruta local: `/media/cristian/7CFE1E0FFE1DC1F6/models/Agnes-3.0-Flash`

Fuentes técnicas: [modelo oficial Agnes-AI](https://huggingface.co/Agnes-AI/Agnes-3.0-Flash),
[cuantizaciones GGUF y validaciones publicadas](https://huggingface.co/0xKitkat/Agnes-3.0-Flash-GGUF)
y [documentación del runtime llama.cpp compatible](https://github.com/JakeATX/llamAmpere/blob/main/docs/agnes-3.0-flash.md).

## Qué se descargó

- `Agnes-3.0-Flash-Q4_K_M.gguf`: aproximadamente 19,8 GiB.
- `mmproj-Agnes-3.0-Flash-F16.gguf`: aproximadamente 0,93 GiB.
- Espacio libre antes de la descarga: ~103 GiB.
- El modelo quedó en la carpeta común `models`, como el resto de los modelos
  locales.

La versión open-weight es el checkpoint **Preview de 33B**, con contexto
declarado de 262.144 tokens. No debe confundirse con el modelo propietario/API
de Agnes que aparece en algunos rankings con contexto de 1M; el propio modelo
card aclara que son checkpoints distintos.

## Pruebas locales

Runtime: `llamAmpere-build/bin/llama-server`, CUDA, dos RTX 3090, P2P PCIe,
`--split-mode layer --tensor-split 1,1`, Flash Attention y KV Q8.

| Prueba | Resultado |
|---|---:|
| Carga Q4 + proyector, contexto 4K | **Correcta** |
| Texto corto, 4K | **139,17 PP / 33,30 TG** |
| Visión, imagen 1920×1080, 2.067 tokens de prompt | **506,46 PP / 33,05 TG** |
| Tool-call `get_weather` | **Correcta**, `finish_reason=tool_calls`, JSON válido |
| Contexto configurado a 262.144 con KV Q8 | **Carga correcta** |
| Respuesta corta con contexto 262K configurado | **Correcta** |
| BCB8 local | Pendiente; no se atribuye score |
| HE20/tool-use completo | Pendiente; sólo se validó un smoke de tool-call |
| MTP | No aplicable al artefacto probado |

La corrida de contexto largo empezó a procesar correctamente una solicitud de
aproximadamente 40K tokens, con el rendimiento de prefill todavía alrededor de
777 tok/s en ese tramo. El cliente de prueba fue interrumpido por el límite
externo de 30 segundos antes de completar una escalera 64K/131K/262K; por lo
tanto no se marca contexto lleno como validado.

Durante una interrupción manual del primer servidor apareció `free(): corrupted
unsorted chunks` al terminar el proceso. No ocurrió durante generación, carga o
visión; se considera un problema de terminación del binario experimental y no
una validación de estabilidad para producción. El proceso quedó cerrado y las
GPU volvieron a su estado ocioso.

## MTP y visión

La cuantización GGUF probada conserva la torre de visión y el proyector, pero la
documentación del artefacto indica que las variantes GGUF publicadas omiten los
pesos MTP. Por eso no se agrega `draft-mtp` artificialmente: no hay un head
compatible que probar y forzarlo podría producir una carga inválida.

La visión sí funcionó con el proyector F16. Esto la hace técnicamente viable,
pero no suficiente para desplazar QWEN35-A3B, que ya tiene visión 4/4,
concurrencia y mejores métricas de generación locales.

## Comparación con perfiles actuales

| Perfil | TG local de referencia | Visión | Calidad agentiva | Decisión |
|---|---:|---|---|---|
| SOL | 74 narrativo / 102 código | 4/4 | BCB 8/8, tool-use estable | Sigue default |
| QWEN35-A3B | 123,98 BCB / 134,4 directo | 4/4 | BCB histórico 4/8 | Sigue secundario multimodal |
| Agnes Q4 | **33,30** | Smoke correcto | BCB/HE pendientes | Experimental, no promover |

El modelo oficial publica pruebas pequeñas de fidelidad y tres checks sintéticos
de imagen, pero también aclara que no son una comparación exhaustiva y que
razonamiento largo, video, tool-calling y contexto largo no están cubiertos de
forma completa. Esas cifras no se mezclan con nuestra tabla BCB.

## Decisión para LlamaCode

- Agnes queda descargado como **candidato experimental multimodal de 33B**.
- No se agrega al dropdown prioritario ni reemplaza SOL, QWEN35-A3B o TERRA.
- No se modifica ningún perfil existente.
- No se descarga Q5/Q6/Q8: aumentar el tamaño sólo empeoraría el margen de
  VRAM y no hay evidencia local de una mejora agentiva.
- Para promoverlo harían falta BCB8, HE20, tool-use encadenado y una escalera
  real de contexto; hoy no hay una razón de rendimiento para pagar ese costo.

