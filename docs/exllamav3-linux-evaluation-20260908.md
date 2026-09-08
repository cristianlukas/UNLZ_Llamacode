# Evaluación de ExLlamaV3 / EXL3 en Ubuntu — 2026-09-08

## Conclusión

La tecnología es técnicamente viable para esta PC, pero no hay un modelo EXL3
local completo con el que se pueda hacer una comparación honesta contra ASTRA,
SOL, TERRA, LUNA o METEOR. Por eso no se agregó un perfil ni se modificaron los
perfiles existentes.

La pila ya estaba instalada en una virtualenv separada:

- ExLlamaV3 `1.4.8+cu128.torch2.9.0`.
- PyTorch `2.9.0+cu128`.
- TabbyAPI `0.0.1`.
- Extensión CUDA precompilada `exllamav3_ext`.
- Dos RTX 3090 visibles, compute capability `8.6`.

El cache de Hugging Face sólo contiene una referencia vacía a
`turboderp/Qwen3.8-Flash-Next-exl3` (`4.05bpw_h6_ng6`); no contiene los pesos
EXL3. Se conserva así para respetar la decisión previa de no reanudar una
descarga pesada sin una campaña de benchmark preparada.

## Pruebas ejecutadas

| Prueba | Resultado |
|---|---|
| Importación de ExLlamaV3 | PASS |
| PyTorch CUDA disponible | PASS; CUDA 12.8, 2 GPU |
| Identificación de GPU | PASS; RTX 3090 en GPU 0 y 1 |
| Extensión `exllamav3_ext` precompilada | PASS |
| Kernel ExL3/MoE cargable | PASS; la extensión expone `exl3_gemm`, `exl3_moe` y CPU-MoE |
| Capacidades CPU para offload | PASS; AVX2, AVX512-VBMI y AVX512-VNNI detectados |
| Arquitecturas Qwen relacionadas | PASS; ExLlamaV3 registra Qwen3-Next y Qwen4-Exp, incluyendo la ruta PLE/n-gram de Flash-Next |
| MTP para Flash-Next | PASS en el código instalado; existe arquitectura `qwen4_exp_mtp` |
| N-gram/PLE | PASS en el código instalado; se admite streaming o carga en RAM |
| TabbyAPI sin modelo | PASS; la API OpenAI inicia en `127.0.0.1` y cierra limpiamente |
| Generación real EXL3 | NO EVALUABLE; faltan los pesos EXL3 |
| TPS, VRAM y BCB contra nuestros perfiles | NO EVALUABLE; no se inventaron cifras |

## Qué aporta a LlamaCode

ExLlamaV3 ofrece una ruta interesante para Qwen3.8 Flash-Next: cuantización EXL3
por BPW, CPU-MoE, caché paginada, n-gram/PLE y MTP. TabbyAPI expone una API
OpenAI-compatible, por lo que el harness podría consumirla conceptualmente.

La integración no es todavía un cambio de binario dentro de los perfiles locales:
LlamaCode actualmente administra perfiles locales como procesos `llama-server`
con sus argumentos y ciclo de vida. TabbyAPI necesita su propio proceso Python,
configuración, directorio de modelos y parámetros de carga. Agregarlo sin pesos
y sin una prueba BCB podría dejar un perfil visible pero no arrancable.

## Campaña pendiente recomendada

Si en el futuro se decide descargar el modelo, la campaña mínima debería comparar
el mismo Qwen3.8 Flash-Next en:

1. GGUF actual de LlamaCode, con y sin cache experto.
2. EXL3 4.05 BPW con cache FP16 y Q8.
3. EXL3 con CPU-MoE dividido, con `ngram_ram` apagado y encendido.
4. EXL3 con MTP y luego n-gram como alternativa.

Cada variante debe medir carga, prefill, decode sostenido, VRAM, RAM, TTFT,
aceptación del drafter y BCB 8/8. Sólo una variante que genere correctamente,
mantenga el harness y supere a TERRA/SOL en la métrica relevante debería
promoverse a un perfil prioritario.

## Estado de la aplicación

No se modificaron ASTRA, SOL, TERRA, LUNA, METEOR ni DEEPSEEK. No se tocó la
configuración de Windows. El servidor activo de LlamaCode queda en TERRA.
