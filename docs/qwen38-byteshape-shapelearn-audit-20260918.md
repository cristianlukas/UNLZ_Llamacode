# Qwen3.8 ByteShape ShapeLearn IQ4_XS — auditoría local

Fecha: 2026-09-18  
Decisión: **agregar como perfil experimental de contexto/fidelidad; no reemplaza SOL ni cambia el default**.

## Candidato y trazabilidad

- Repositorio: [`byteshape/Qwen3.8-27B-GGUF`](https://huggingface.co/byteshape/Qwen3.8-27B-GGUF).
- GGUF local: `/media/cristian/7CFE1E0FFE1DC1F6/models/Qwen3.8-27B-ByteShape-IQ4_XS/Qwen3.8-27B-IQ4_XS-3.84bpw.gguf`.
- Tamaño: 13.083.052.416 bytes (~13,08 GB).
- `mmproj`: `/media/cristian/7CFE1E0FFE1DC1F6/models/Qwen3.8-27B-GSQ-RCO-IQ3_S/mmproj-Qwen3.8-27B-BF16.gguf`.
- Runtime: `llama-server` local `1 (67849b6)`, CUDA, Ryzen 9 9950X3D, 2× RTX 3090 24 GB, P2P disponible.
- La variante es de vocabulario completo: no tiene la restricción ASCII de
  `sys-qwen38-27b-byteshape-ascii-262k`.

La publicación de ByteShape informa cinco quants ShapeLearn y presenta IQ4_XS
como su variante GPU-5 de 3,84 bpw. Esas cifras son benchmarks externos y no se
mezclan con las métricas de LlamaCode. El post también documenta MTP integrado,
visión mediante `mmproj` y un requisito de llama.cpp b10658+ para DFlash2; aquí
se validó sólo el MTP integrado, no DFlash2 sobre este target.

## Resultados locales

Todas las corridas usaron sampling conservador (`temp=0.6`, `top-p=0.95`,
`top-k=20`, `min-p=0`), Flash Attention, KV Q8 y `parallel=1`.

| Configuración | PP | TG | Aceptación | Resultado |
|---|---:|---:|---:|---|
| 8K, 1× RTX 3090, sin MTP | 156,8 | 25,85 | — | Python válido |
| 8K, 1× RTX 3090, MTP3 integrado | 180,7 | **53,64** | 87/118 = 73,7% | Python válido |
| 32K, 1× RTX 3090, `mmproj` BF16 + MTP3 | 163,5 | **55,92** | 44/55 = 80,0% | Visión correcta |
| 262K, 2× RTX 3090, sin MTP | 118,4 | **41,77** | — | Carga estable |
| 262K, 2× RTX 3090, MTP3 integrado | 108,0 | **66,24** | 83/131 = 63,4% | Carga estable |

La prueba visual identificó correctamente el texto de la imagen sintética y sus
colores dominantes. La salida fue válida; el límite de 64 tokens truncó la
explicación, no la detección visual.

## Comparación con lo ya probado

| Perfil | TG local | Calidad/estabilidad | Contexto/visión | Lectura |
|---|---:|---|---|---|
| **SOL** | 74 narrativo / 102 código | BCB agentivo 8/8; tool-use estable | 262K; visión validada | Sigue siendo el default |
| **ShapeLearn completo IQ4_XS** | 53,6 a 8K; 66,2 a 262K con MTP3 | BCB8 LC-H1 todavía pendiente | 262K cargable; visión+MTP3 funcional | Útil como experimental multilingüe de contexto |
| **ByteShape ASCII/P1M IQ4_XS** | 79–88 corto; 45 a 262K | BCB directo 1/8; sólo ASCII/inglés/código | 262K; visión+MTP2 | Más rápido en corto, menos general |
| **QWEN38-Q8** | 41,3 a 8K / 22,1 a 262K | BCB directo 8/8 histórico; agente pendiente | 262K; visión Q8+MTP no estable | ShapeLearn es más rápido y liviano en esta receta |

No se asigna BCB8 a ShapeLearn: todavía no completó la cadena oficial
`HE0 → HE20 → BCB` con LC-H1. El smoke de Python y visión no equivale a calidad
agentiva. Tampoco se presenta como superior a SOL, que conserva la única
validación agentiva 8/8 y el tool-use estable.

## Perfil agregado

Se agregó `sys-qwen38-27b-byteshape-shapelearn-262k` al catálogo con:

- 2× RTX 3090, reparto `layer`, contexto 262K y KV Q8;
- MTP3 integrado como opción declarada;
- visión habilitada mediante `mmproj-bf16.gguf`;
- MTP separado del score de calidad y sin promoción automática.

No se habilitó DFlash2: el drafter local previamente validado corresponde a
GSQ-RCO IQ3_S, y reutilizarlo aquí no sería una comparación ni una combinación
arquitectónicamente demostrada. La siguiente prueba válida para promover este
perfil es ejecutar HE0, HE20 y BCB8 LC-H1 con esta huella exacta.

## Fuentes externas

- [Anuncio técnico de ByteShape sobre Qwen3.8-27B](https://byteshape.com/blogs/Qwen3.8-27B/).
- [Repositorio oficial de quants ShapeLearn](https://huggingface.co/byteshape/Qwen3.8-27B-GGUF).
- [Auditoría local previa del quant ASCII/P1M](qwen38-byteshape-ascii-audit-20260918.md).
