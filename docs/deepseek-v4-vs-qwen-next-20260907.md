# DeepSeek V4 Flash frente a Qwen3.8 Flash-Next — 2026-09-07

## Conclusión para esta PC

La publicación compara dos equipos DGX Spark y no permite trasladar sus
tok/s directamente a las dos RTX 3090 de esta instalación. Sí aporta tres
criterios útiles para LlamaCode: medir el flujo completo del agente (no sólo
decode), separar calidad de herramienta de velocidad de texto y evaluar
prefill/concurrencia junto con el contexto.

En el hardware local, la evidencia disponible queda así:

| Familia | Evidencia local | Decisión |
|---|---|---|
| Qwen3.8 Flash-Next | 41,31 tok/s de decode con cache experto 188; BCB no válido en la campaña | Mantener como ASTRA experimental para contexto/capacidad; no usar como default de coding. |
| Qwen3.8-27B | SOL/TERRA pasan BCB 8/8 y entregan aproximadamente 63,94/70,37 tok/s según perfil | Mantener SOL y TERRA como opciones principales de coding y uso diario. |
| DeepSeek V4 Flash UD-IQ3_S | BCB histórico 8/8 a 9,645 tok/s; el smoke nativo dual llegó a 5,764–6,171 tok/s | Mantener `sys-48-dsv4-nospec` como perfil opcional de calidad, no promoverlo sobre Qwen por latencia. |
| DeepSeek Fusion antirez | BCB histórico 8/8 a 10,548 tok/s, pero con tiempos de agente muy altos | Mantener como control experimental, no como perfil diario. |

## Qué se implementa y qué no

LlamaCode ya tiene el perfil `SUPERIOR - DeepSeek V4-7-8-26`
(`sys-48-dsv4-nospec`) marcado como mejor dentro de la familia DeepSeek. Usa
los cuatro shards locales, reparto conservador `tensor-split 1,0`, expertos
alineados y no speculative decoding. Se conserva separado de ASTRA, SOL,
TERRA, LUNA y METEOR; no se cambia el comportamiento de Windows.

También existe el perfil experimental de DSpark externo, pero el archivo
drafter no está presente en el catálogo local. No se descarga ni se habilita
automáticamente: en las pruebas anteriores de esta máquina DSpark mejoró
prefill, pero no demostró un decode estable; las configuraciones `tensor-split
1,1` además tuvieron corrupción histórica. El perfil queda disponible sólo
para una campaña futura deliberada.

La variante DeepSeek con visión tampoco se agrega ahora. El repositorio oficial
publica un GGUF Vision-Exp separado, y la API oficial limita la entrada de
imágenes al modelo de visión; ese artefacto no está instalado en esta PC y no
es comparable con el DeepSeek textual ya validado.

## Recomendación operativa

- Coding/agentes: TERRA; SOL cuando se prioriza la máxima robustez ya validada.
- Contexto MoE grande: ASTRA, aceptando su estado experimental.
- Calidad DeepSeek y tareas donde se prefiera su comportamiento: perfil
  `SUPERIOR - DeepSeek V4-7-8-26`, con una latencia considerablemente mayor.
- Visión: seguir usando los perfiles Qwen con visión ya instalados; no afirmar
  que DeepSeek tiene visión local hasta instalar y validar su mmproj/GGUF.

Referencias externas: [DeepSeek V4 Flash GGUF oficial](https://huggingface.co/ggml-org/DeepSeek-V4-Flash-GGUF),
[DeepSeek V4 Flash Vision-Exp GGUF](https://huggingface.co/ggml-org/DeepSeek-V4-Flash-Vision-Exp-GGUF),
[guía oficial de visión](https://api-docs.deepseek.com/guides/vision/) y
[model card oficial](https://fe-static.deepseek.com/chat/transparency/deepseek-V4-model-card-EN.pdf).
