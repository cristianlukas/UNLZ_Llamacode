# Qwen3.8 ByteShape IQ4_XS ASCII/P1M — auditoría local

Fecha: 2026-09-18  
Candidato: `islamsidratul/Qwen3.8-27B-ByteShape-IQ4_XS-ASCII-GGUF`  
Decisión: **agregar como perfil experimental especializado; no reemplazar SOL ni
marcar como default**.

## Qué se probó

Se descargó sólo el GGUF de 12,25 GB en:

`/media/cristian/7CFE1E0FFE1DC1F6/models/Qwen3.8-27B-ByteShape-IQ4_XS-ASCII-P1M/`

SHA-256 validado contra el publicado: `d533c568ba028fb7bc24d646d9f0259341a388fb2535e559fd0bc62275a55a4d`.

La variante conserva 129.272 tokens ASCII/P1M, el head MTP y los pesos
transformer del quant ByteShape. El modelo publicado advierte que CJK, árabe,
cirílico, otros alfabetos no latinos y caracteres como `ñ`/acentos se degradan.
La fuente es el [model card de ByteShape](https://huggingface.co/islamsidratul/Qwen3.8-27B-ByteShape-IQ4_XS-ASCII-GGUF)
y la herramienta de poda es
[ASCII-Condensed-prune-tools](https://github.com/bsaleh03/ASCII-Condensed-prune-tools).

## Resultados locales

Hardware: 2× RTX 3090, P2P disponible, Ryzen 9 9950X3D, 123 GiB RAM. Runtime
LlamaCode `0.3.0-dev`, CUDA, commit `9bd97fe`.

| Configuración | Resultado | Lectura |
|---|---:|---|
| 8K, una RTX 3090, KV Q8, sin MTP | 189–244 PP; 43,4–44,1 TG | Funcional; inferior a SOL en decode |
| 8K, una RTX 3090, MTP2 | 79,0–88,4 TG; aceptación 73–90% | Mejor receta local |
| 8K, MTP5 | 70,4–79,3 TG; aceptación 48–56% | Peor que MTP2 |
| 8K, MTP5 + ngram-mod | 69,1–76,5 TG; aceptación 51–56% | No mejora; descartado |
| 131K, una RTX 3090, KV Q8, sin MTP | 16,8 GiB usados; 41–46 TG | Carga estable |
| 196K, una RTX 3090, KV Q8, sin MTP | 19,3 GiB usados; 44,2 TG | Carga estable |
| 262K, 2× RTX 3090, KV Q8, sin MTP | 13,25/13,01 GiB; 45,1 TG | Carga estable; contexto nominal |
| 32K, `mmproj` + MTP2 | Visión correcta; 67,6 TG; aceptación 81% | Visión realmente funcional |

La prueba visual leyó correctamente una imagen sintética y devolvió el texto
exacto. El `mmproj` usado fue el Qwen3.8 BF16 ya disponible localmente; no se
descargó una copia duplicada.

## BCB8 directo

Se ejecutó el mismo pack directo de 8 tareas usado en la campaña del
15-09-2026, con KV Q8, temperatura 0,2, top-p 0,95, top-k 20 y min-p 0.0.
No usa herramientas, reparación ni reintentos del agente LC-H1.

**Resultado: 1/8.**

Pasó `BigCodeBench/870`. Falló en los restantes por errores funcionales de
ordenamiento, tipos, muestreo, fechas y un caso que agotó el límite de salida
sin entregar código evaluable. Es un resultado de calidad directa, no un
problema de carga o de visión.

## Comparación con perfiles actuales

| Perfil | Velocidad | Calidad/estabilidad | Contexto/visión | Decisión |
|---|---:|---|---|---|
| **SOL** | 74 narrativo / 102 código | BCB 8/8 agentivo; tool-use válido | 262K; visión validada | Default |
| **ByteShape ASCII/P1M** | 79–88 TG con MTP2; 45 TG a 262K | BCB directo 1/8; inglés/código ASCII | 262K estable; visión+MTP2 válida | Experimental especializado |
| **QWEN38-Q8** | 41,3 @8K / 22,1 @262K | BCB directo 8/8 histórico; agente pendiente | 262K; visión+MTP Q8 no estable | Fidelidad/contexto |

ByteShape es claramente más liviano y más rápido que QWEN38-Q8 en esta receta,
y aporta una ruta de visión+MTP funcional. No es superior a SOL: SOL conserva
la calidad agentiva, el tool-use y la compatibilidad lingüística necesarias
para el uso general.

## Decisión operativa

- Se agregó `sys-qwen38-27b-byteshape-ascii-262k` al catálogo como benchmark
  experimental.
- El perfil usa KV Q8, contexto 262K, reparto layer `0.5,0.5`, visión y MTP2.
- No se habilita como default ni como fallback automático de SOL.
- Se recomienda sólo para inglés, código y entradas predominantemente ASCII,
  cuando se prioriza liberar VRAM o usar contexto largo.
- MTP5 y MTP5+ngram no se conservaron como receta: fueron más lentos y con
  menor aceptación.
- No se repite esta matriz en futuras campañas salvo que cambien el runtime,
  el harness, el tokenizer o aparezca una variante no-ASCII.
