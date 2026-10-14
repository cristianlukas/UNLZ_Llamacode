# Resultados — Q-20261010-QWEN38-27B-OVERTHINKING

**Estado:** auditoría documental completa; no se ejecutó inferencia nueva.

## Hallazgos

El post de r/LocalLLaMA atribuye buenos resultados prácticos al Qwen3.8-27B
Unsloth UD-Q3_K_XL y dice que UD-Q2_K_XL también le sirve cuando necesita más
contexto. Es una experiencia personal, no una evaluación reproducible: faltan
prompts, hardware, runtime, revisión/hash, verificador y recibos.

Los comentarios del mismo post se contradicen sobre el overthinking. Hay
reportes de loops con Q8, otro usuario dice no observarlos con greedy, y otros
atribuyen una mejora a cambiar sampling, usar reasoning medium o limitar la
salida. La discusión en Hugging Face describe loops de 20K–55K tokens en
SGLang/GB10 y un caso BF16 donde el autor dice que un thinking budget explícito
ayudó; son relatos no controlados de configuraciones distintas.

La tarjeta oficial indica thinking activado por defecto y recomienda para ese
modo temperature 1.0, top_p 0.95, top_k 20, min_p 0, presence_penalty 0 y
repetition_penalty 1. Declara xhigh como esfuerzo predeterminado y también
ofrece medium y low. Advierte que reducir el esfuerzo puede acortar una
respuesta aislada, pero aumentar fallos y reintentos en agentes. La tarjeta no
documenta un thinking budget rígido.

## Preflight local y decisión de no correr

No se encontró el Unsloth UD-Q3_K_XL ni UD-Q2_K_XL exacto del post. Sí existe
Agention AP-Q3_K_XL (13.146.392.480 bytes; SHA-256
b5b35d550712f01fcaa0a982f281b7bcf47f6309c541450ca0e064c945c1c8fc), con
calibración/encoding propios; no se presenta como el mismo quant. El runtime
local disponible es llama.cpp 0.3.0-dev, commit ef6876693.

En el snapshot, GPU0 tenía 1.083 MiB usados por el escritorio y ArtCraft; GPU1
tenía 108 MiB, Xorg y 58% de utilización. No se confirmó una reserva exclusiva
para una prueba; no se detuvo ninguna aplicación ni se cargó un modelo. Tampoco
se reutilizó el perfil productivo SOL para una comparación que no corresponde
a su runtime ni a su modelo.

## Conclusión

La publicación aporta una hipótesis para probar terminación/overthinking y
controles de generación. No demuestra que UD-Q3/Q2 sea superior ni valida un
ajuste de sampling para LlamaCode. No se cambian perfiles, HarnessSpec ni
defaults.

Para una futura prueba local: usar una suite fija con casos de coding/agente,
verificador independiente, conteo de tokens de razonamiento/salida, tiempo,
éxito de terminación y detección de repetición; comparar una variable por vez y
fijar un límite de salida explícito. Cada corrida debe permanecer por debajo de
30 minutos. Una prueba con el AP-Q3 local sería evidencia sólo de ese artefacto
y de ese perfil completo, no una réplica del post Unsloth.

## Fuentes y recibos

- [Post r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1wybak7/qwen3827b_appreciation_moment/)
- [Tarjeta oficial de Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B)
- [Discusión de loops en Hugging Face](https://huggingface.co/Qwen/Qwen3.8-27B/discussions/178)
- [Unsloth GGUF](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF)
- [Agention AP GGUF local](https://huggingface.co/agentionai/Qwen3.8-27B-AP-GGUF)
- [Recibo de revisión de fuentes y preflight](receipts/source-review.json)
