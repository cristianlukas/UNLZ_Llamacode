# Qwen Flash-Next frente a LUNA y METEOR — Ubuntu — 2026-09-08

## Alcance

Se compararon en la instancia Ubuntu de LlamaCode:

- **ASTRA:** Qwen3.8 Flash-Next UD-Q4_K_XL, cache experto 188, expertos en RAM, KV F16, contexto 196K.
- **LUNA:** ThinkingCap Qwen3.6-27B Q4_K_M, MTP4, CUDA, visión disponible, contexto 64K.
- **METEOR:** perfil BigBang MTP reparado, contexto operativo 64K.

La prueba de velocidad fue `LlamaCode Server Speed v1`, una pasada, warmup 1,
prefill habilitado y un solo slot. La calidad se probó con el flujo del harness
HE0 → HE20 → BCB. Para no dejar el equipo ocupado durante horas, la repetición
actual se detuvo después de completar HE0 de los tres perfiles; HE20/BCB se
conservan como referencia histórica cuando no se pudo completar una repetición
comparable.

## Velocidad medida ahora

| Perfil | Modelo / contexto | Decode promedio | Decode P50 | Prefill | TTFT P50 | Resultado |
|---|---|---:|---:|---:|---:|---|
| ASTRA | Qwen Flash-Next, 196K | **36,83 tok/s** | 38,37 tok/s | 30,89 tok/s | 2.171 ms | Cargó y midió |
| LUNA | ThinkingCap Qwen3.6-27B MTP4, 64K | **57,95 tok/s** | 55,00 tok/s | 221,49 tok/s | 283 ms | Cargó y midió |
| METEOR | BigBang MTP reparado, 64K | — | — | — | — | No cargó |

ASTRA tardó aproximadamente 166 s en estar listo para la prueba de calidad;
LUNA tardó aproximadamente 68 s. METEOR no llegó a iniciar: el loader informó
`wrong number of tensors; expected 866, got 862` al abrir
`Qwen3.8-27B-Q5_K_M.gguf`. El perfil METEOR actual quedó apuntando a ese archivo
Qwen Q5, mientras que el BigBang histórico requiere
`endless-frontier_BigBang-v1-Q4_K_M.gguf`; ese archivo no está disponible en las
carpetas de modelos montadas actualmente.

## Calidad del harness

### Corrida Ubuntu actual

| Perfil | HE0 actual | Reparaciones | Tool calls | Observación |
|---|---:|---:|---:|---|
| ASTRA | **0/1** | 2 | 0 | No produjo una llamada válida; falló criterios de aceptación |
| LUNA | **1/1** | 0 | 2 | Primera pasada válida; primera llamada a los 64,55 s |
| METEOR | **0/0** | 0 | 0 | Bloqueado en carga, sin resultado evaluable |

La generación de ASTRA durante HE0 promedió 18,33 tok/s, menor que su medición
aislada de servidor porque incluye el prompt largo y la interacción del harness.
El valor `0,04 tok/s` registrado para LUNA en HE0 no es una velocidad de decode:
la pasada incluyó un prefill de unos 8.862 tokens y el campo agregado quedó
contaminado por el tiempo total; para velocidad se debe usar la tabla de Server
Speed v1.

### Controles históricos ya validados

| Perfil | HE0 | HE20 | BCB | Velocidad histórica | Estado |
|---|---:|---:|---:|---:|---|
| ASTRA | 0/1 o no evaluable | — | 0/8 diagnóstico | 16,25–41,31 tok/s según contexto | Experimental; no apto como agente principal |
| LUNA | 1/1 | 20/20 en la corrida histórica | 6/8 | 56,84 tok/s | Alternativa funcional de razonamiento/visión |
| METEOR | 1/1 histórico | 20/20 histórico | 3/8 | 211,18 tok/s de throughput histórico | Sólo lotes; calidad parcial |

No se mezclan los scores históricos con la medición actual: la corrida actual de
METEOR no fue evaluable y ASTRA volvió a fallar HE0.

## Conclusión y decisión

1. **LUNA es la mejor opción práctica entre estos tres en Ubuntu:** es casi
   1,6× más rápida que ASTRA en Server Speed, pasó HE0 sin reparación y conserva
   visión y MTP4. Su BCB histórico 6/8 impide llamarla perfil de máxima calidad,
   pero sí es un perfil utilizable.
2. **ASTRA se mantiene como perfil experimental de máxima capacidad/contexto.**
   No se promueve ni se usa como default del harness hasta que pase HE0 con una
   tool call válida.
3. **METEOR no se puede comparar honestamente todavía.** Su cifra histórica de
   211,18 tok/s corresponde al BigBang correcto y no al archivo Qwen Q5 que el
   perfil está intentando cargar ahora. Hay que recuperar el GGUF BigBang y
   repetir Server Speed + HE0 → HE20 → BCB antes de promoverlo.
4. **No se cambian los perfiles de Windows ni los perfiles Linux.** La variante
   Apple MLX/oQ4e-MTP del artículo no es un modelo GGUF CUDA: requiere MLX/oMLX,
   por lo que no es una optimización aplicable a estas dos RTX 3090 dentro de
   LlamaCode.

El servidor quedó restaurado en **TERRA** al finalizar las pruebas.
