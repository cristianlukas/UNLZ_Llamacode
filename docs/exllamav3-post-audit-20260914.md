# Auditoría del post de ExLlamaV3 — 2026-09-14

## Conclusión

El post confirma una dirección técnicamente interesante para Qwen3.8
Flash-Next, pero no aporta todavía un perfil ejecutable y reproducible para
LlamaCode. ExLlamaV3/EXL3 no es un cambio de argumentos de `llama-server`:
requiere pesos EXL3, TabbyAPI y un proceso Python separado.

No se descargó el quant: el modelo `4.05bpw_h6_ng6` y su tabla n-gram ocupan
del orden de 100 GB o más, mientras que la partición de modelos tiene poco
espacio libre. Todos los modelos de LlamaCode deben seguir en
`/media/cristian/7CFE1E0FFE1DC1F6/models`.

## Qué aporta el post

| Idea | Aplicabilidad local | Decisión |
|---|---|---|
| CPU-offload de expertos MoE | Podría ser útil para Qwen Flash-Next y DeepSeek, pero sólo dentro de ExLlamaV3 | Pendiente de pesos EXL3 y benchmark |
| N-gram/PLE desde disco | Reduce RAM, pero puede aumentar latencia e I/O; no equivale al `lazy-mode` de nuestra build llama.cpp | No activar en ASTRA |
| `vision_offload` | Puede liberar VRAM en TabbyAPI a cambio de latencia; no existe como opción equivalente del perfil llama.cpp actual | Sólo para una futura campaña EXL3 |
| SC quants / 3.05–4.05 bpw | Prometen mejor relación calidad/VRAM, pero el post mezcla reportes no controlados y algunos advierten colapso en 2.2 bpw | No promover sin BCB/tool-use |
| MTP + n-gram | Puede elevar throughput, pero la estabilidad depende del modelo y backend | Medir después del baseline sin especulación |

### Evidencia adicional del mismo hilo

Los comentarios agregan tres referencias que conviene separar:

- Un **Qwen3.8-27B EXL3 de 5 bpw** habría alcanzado ~43 tok/s frente a ~35
  tok/s con GGUF en una combinación 5070 Ti + 3060. El prefill fue similar,
  pero no se publicaron BCB, HE0 ni pruebas de tool-use.
- Otro usuario informa **60–70 tok/s y 160K** con Qwen3.8 EXL3 en una 3090,
  frente a 80–100 tok/s con vLLM de menor calidad. Es una referencia útil para
  investigar, pero no es reproducible con nuestro artefacto ni nuestro
  harness.
- También se reporta que **Qwen3.8 Flash-Next Q3** puede empezar en 22–25
  tok/s y degradar con contexto, mientras que el perfil Q4 local de LlamaCode
  ronda 36 tok/s con BeeLlama/KVarN5 cuando la salida es válida. Esto no
  justifica bajar de Q4 en nuestra máquina.

La propia discusión contiene advertencias sobre tool calling incompleto,
disponibilidad limitada de modelos y dependencia de NVIDIA. Por eso no se
consideran equivalentes a una validación de LlamaCode.

## Comparación contra LlamaCode

Las mediciones locales existentes siguen siendo la referencia:

| Perfil | Resultado local |
|---|---|
| SOL / Qwen3.8 | BCB 8/8; aproximadamente 74 tok/s narrativo y 102 tok/s código |
| ASTRA / Qwen Flash-Next GGUF | Contexto largo, pero BCB no válido; no es agente principal |
| GALACTA / DeepSeek V4 IQ3_S | BCB 8/8 histórico; aproximadamente 9,65 tok/s |
| BeeLlama KVarN5 | Tool-call/JSON válidos y aproximadamente 36 tok/s sostenidos hasta 131K; experimental texto-only |

También se probó en nuestra máquina la idea relacionada de dejar la tabla PLE
en modo lazy:

- `lazy-mode on`: produjo salida corrupta (`////`) aunque el TPS bruto pareciera
  mayor.
- `lazy-mode on-direct`: salida válida, pero aproximadamente 49% más lento que
  el control.
- Resultado: ASTRA conserva `mmap`, caché MoE 188 y KV Q8; no se promociona
  `lazy-mode`.

## Estado del backend ExLlama local

La carpeta de TabbyAPI y su configuración existen en
`/media/cristian/Disco local/llamacode-exllama`, y el esquema ya contempla
`cpu_moe_split_experts`, `ngram_ram` y `vision_offload`. Sin embargo, la
verificación actual del entorno no pudo importar `torch` ni `exllamav3`; sólo
está disponible el paquete TabbyAPI. No hay pesos EXL3 completos en la carpeta
de modelos autorizada.

Por lo tanto no se midieron TPS, VRAM, BCB ni tool-use EXL3 y no se agregó un
perfil visible o un backend roto al dropdown.

La comprobación actual confirma que no hay pesos EXL3 completos en
`/media/cristian/7CFE1E0FFE1DC1F6/models`; sólo están disponibles los artefactos
AutoRound de Qwen en safetensors. El entorno TabbyAPI ocupa aproximadamente
4,8 GB en la otra partición, pero no contiene un modelo cargable. La partición
de modelos activa tiene unos 22 GB libres, insuficientes para descargar el
Qwen3.8 EXL3 de 4–5 bpw y conservar margen para la prueba.

## Plan si se retoma

1. Reparar el entorno Python sin descargar modelos todavía.
2. Conseguir una variante EXL3 completa dentro de la partición autorizada.
3. Medir primero sin MTP y sin n-gram: carga, TTFT, prefill, decode, RAM/VRAM y
   estabilidad a 32K/131K/196K.
4. Repetir con CPU-MoE, `ngram_ram`, `vision_offload` y MTP por separado.
5. Ejecutar HE0, tool-use y BCB antes de compararlo con SOL y ASTRA.

Sólo se promovería si mantiene salida válida y supera a SOL o ASTRA en el caso
de uso correspondiente; los números publicados en Reddit no son suficientes.

## Decisión posterior a esta referencia

No se modifica ningún perfil ni el default. EXL3 queda como línea de
investigación para una futura comparación con Qwen3.8-27B, pero no como
reemplazo inmediato de SOL. La mejor acción actual sería conseguir primero
espacio en la partición autorizada y luego medir un único quant EXL3 de 4–5 bpw
con baseline sin especulación, CPU-offload separado, contexto 32K/131K/160K,
HE0, tool-use y BCB. No corresponde descargar un quant de 2,2 bpw o una
variante Flash-Next Q3 sólo para perseguir la velocidad publicada.
