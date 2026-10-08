# ExLlamaV3/EXL3 para Qwen3.8-27B — auditoría local

Fecha: 2026-09-14  
Decisión: **no reemplaza a SOL ni se agrega al dropdown principal**. Queda
documentado como candidato experimental porque aporta una receta real de MTP,
visión y contexto largo, pero su validación agentiva local no es competitiva.

## Qué se evaluó

El post propone `turboderp/Qwen3.8-27B-exl3`, revisión
`SC_3.00bpw_H4_V4`, con TabbyAPI y ExLlamaV3. La receta publicada usa MTP2 y
cache de draft Q6; la variante dinámica no se tomó como default porque el
resultado externo publicado es inferior al MTP fijo Q6.

Fuentes técnicas: [ExLlamaV3](https://github.com/turboderp-org/exllamav3),
[TabbyAPI](https://github.com/theroyallab/tabbyAPI) y el
[checkpoint EXL3 de Qwen3.8](https://huggingface.co/turboderp/Qwen3.8-27B-exl3).
La tarjeta del checkpoint declara soporte multimodal, MTP embebido, contexto
262.144 y cuantización de visión V4; el runtime permite cache cuantizado y
tensor parallel.

## Artefactos y entorno

- Hardware: 2× RTX 3090 de 24 GB, Linux, P2P disponible.
- ExLlamaV3 1.5.0, PyTorch 2.9.0+cu128, TabbyAPI.
- Modelo descargado en:
  `/media/cristian/7CFE1E0FFE1DC1F6/models/Qwen3.8-27B-EXL3-SC-3.00bpw-H4-V4/`.
- Tensor parallel nativo en las dos GPU, `max_seq_len/cache_size=262144`.
- MTP2, draft cache Q6, `cache_mode=6,6`, `max_batch_size=1`.
- Sampling de la solicitud: temperatura 0,6, top-p 0,95, top-k 20, min-p 0.
- No se usó ningún peso ni KV superior a Q8. La cuantización de pesos es
  3.00 bpw, no equivalente a un Q4/Q8 GGUF.

## Resultados reproducidos

| Escenario | Prefill | Decode | Aceptación MTP | Resultado |
|---|---:|---:|---:|---|
| Base, 131K, sin MTP, prompt corto | — | ~44 tok/s warm | — | Estable |
| MTP2 Q6, 131K, prompt corto | — | ~102–111 tok/s warm | 91–95% | Estable |
| MTP2 Q6, 6.732 tokens | ~874 tok/s | ~61,5 tok/s | 30% | Estable |
| MTP2 Q6, 103.232 tokens frescos | ~900 tok/s | **63,5 tok/s** | 75% | Estable; TTFT ~114,7 s |
| MTP2 Q6, tool-call | — | ~110,7 tok/s warm | 95% | JSON de tool-call válido |
| MTP2 Q6, 262K reservado | — | 78–116 tok/s warm | hasta 100% | Carga y reserva correctas |
| MTP2 Q6, visión con captura redimensionada a 768 px | — | ~77,8 tok/s | 62% | Descripción/OCR correcto |

El post externo midió en una RTX 4080 aproximadamente 56,48 tok/s a ~100K
con MTP2/Q6. En nuestra máquina dual 3090 la prueba equivalente alcanzó
63,5 tok/s; no es una comparación idéntica porque difieren GPU, backend y
configuración, pero confirma que la receta es reproducible.

El contexto de 262K quedó **configurado y reservado** por el runtime; se llenó
de forma efectiva hasta 103.232 tokens en la prueba larga. No se debe presentar
como una escalera completa hasta 262K sin una corrida adicional de prefill a
ese tamaño.

## Calidad y agentividad

Se ejecutó dos veces la muestra local de 8 tareas BCB de LlamaCode, con el
grader corregido para usar el preámbulo oficial, `pandas`/`numpy` compatibles y
un proceso aislado por tarea:

| Pasada | Resultado |
|---:|---:|
| 1 | **1/8** |
| 2 | **1/8** |

El único acierto fue `BigCodeBench/870`. Los fallos fueron funcionales y
repetibles: diferencias de CSV, lista de archivos, diff, agregación de datos,
conversión de unidades, orden y validación de entradas. No se contaron como
fallos los problemas iniciales del instrumento: la primera versión del grader
carecía de `pandas` y no incorporaba el preámbulo; la medición final corrigió
ambos puntos.

## Comparación contra los perfiles actuales

| Perfil | Velocidad | Calidad/agentes | Contexto | Visión | Decisión |
|---|---:|---|---|---|---|
| **SOL** | 74 narrativo / 102 código | **BCB 8/8**, tool-use estable | 262K validado | Validada en la receta vLLM | Default |
| **EXL3-QWEN38** | ~102–116 corto; **63,5 a 103K** | **BCB 1/8 en 2 pasadas** | 262K configurado; 103K llenado | Funcional con mmproj nativo | Experimental, no default |
| **QWEN38-Q8** | 41,3 @8K / 22,1 @262K | BCB pendiente | 262K validado | No | Experimental |

EXL3 es más rápido que SOL en prompts cortos y aporta visión local con un
consumo razonable, pero cae por debajo de SOL en el régimen largo medido y no
se acerca a su calidad agentiva. Por eso no se reemplaza SOL ni se altera el
orden de perfiles. Tampoco se agrega una entrada activa: el backend TabbyAPI
quedó instalado de forma aislada para la auditoría y no forma parte todavía del
ciclo de vida de servidores de LlamaCode.

## Resultado operativo

- No se modificó el dropdown ni el perfil SOL.
- No se añadió EXL3 como default ni como perfil prioritario.
- Se conservaron el modelo y sus artefactos en `models/` para una futura prueba
  de integración si mejora la calidad BCB.
- La captura de visión se probó con preprocesamiento a 768 px y funcionó; esto
  es compatible con la mejora general ya documentada para capturas grandes.
- El servidor TabbyAPI se detuvo al terminar; no queda un proceso EXL3/vLLM
  ejecutándose en segundo plano.

