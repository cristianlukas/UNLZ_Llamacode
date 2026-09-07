# Ling 3.0 Tiny en Ubuntu

## Modelo instalado

Se descargó la variante recomendada en la referencia aportada:

- Repositorio: `SC117/Ling-3.0-tiny-abliterated-APEX-GGUF`
- Archivo: `Ling-3.0-tiny-abliterated-APEX-I-Compact.gguf`
- Ruta: `/media/cristian/Disco local/Models/llamacpp/Ling-3.0-tiny-abliterated-APEX-GGUF/`
- Tamaño: 3.99 GB
- Arquitectura detectada: `bailingmoe3`
- Catálogo Ubuntu: disponible como modelo estable 134

La variante estándar `Ling-3.0-tiny-Q6_K.direct.gguf` ya existía localmente y
también quedó visible en el catálogo. La prueba principal usa APEX-I-Compact,
que es la variante que indicaba la publicación.

## Comparación de rendimiento

Medición local con el mismo prompt, 256 tokens, contexto 32K, batch/ubatch
512/512, Flash Attention, KV q8_0/q8_0, 12 threads, un GPU completo y sin
speculative decoding:

| Modelo | Tamaño local | Prefill tok/s | Decode tok/s |
|---|---:|---:|---:|
| Ling 3.0 Tiny APEX-I Compact | 3.99 GB | 1,259.76 | **203.75** |
| Qwen3.5 2B Q4_K_M | 1.33 GB | 3,043.75 | **257.42** |
| Qwen3.5 4B Q4_K_M | 2.83 GB | 2,836.54 | 148.37 |
| Qwen3.5 9B Q4_K_M | 5.68 GB | 2,443.19 | 100.07 |
| Gemma 4 12B QAT Q4_0 | 6.98 GB | 2,052.34 | 69.85 |

Ling queda claramente por encima de Qwen3.5 4B/9B y Gemma 4 12B en decode,
pero Qwen3.5 2B sigue siendo más rápido. La tabla mide velocidad y carga, no
calidad ni robustez de tool-calling; las observaciones de la referencia sobre
formato, cálculos y estabilidad deben validarse con una campaña de calidad
separada.

## Estado en LlamaCode

El escaneo de raíces registró automáticamente el archivo nuevo. No se cambió
ningún perfil existente ni se reemplazó el Qwen activo. El modelo puede
seleccionarse desde el catálogo de modelos Ubuntu y el servidor Qwen de
LlamaCode quedó restaurado en `127.0.0.1:8031`.

## Perfil auxiliar Linux validado — 2026-09-07

Además de la variante APEX, se dejó en LlamaCode un perfil editable para el
GGUF estándar Q6 que ya estaba instalado:

- `LING — Tiny — web/tool auxiliar — 131K`
- ID de perfil: `9a7e0789-a278-4b88-b8eb-fc82431f116a`
- Flash Attention, contexto 131K, KV q8/q8, batch 512, `--repeat-last-n 512`,
  penalización de repetición 1.05 y razonamiento desactivado para tareas de
  herramientas rápidas.

Pruebas nuevas con el servidor administrado por LlamaCode:

| Prueba | Resultado |
| --- | ---: |
| Server Speed LlamaCode | 206,13 tok/s decode medio |
| Tool-calling directo | llamada válida en 3/3 temperaturas probadas |
| Recuperación de contexto | marcador recuperado hasta 61K de entrada |
| HE0 con agente Máximo | 0/1; falló el flujo de herramientas/verificación |

El perfil queda como auxiliar para búsqueda web, scraping, resúmenes y tool use
de baja latencia. No se lo promueve a ASTRA/SOL/TERRA/LUNA/METEOR ni se lo
recomienda como agente principal de coding hasta obtener una campaña HE/BCB
válida. La prueba HE0 se detuvo antes de repetir una reparación que quedó en
bucle; TERRA fue restaurado como perfil activo.
