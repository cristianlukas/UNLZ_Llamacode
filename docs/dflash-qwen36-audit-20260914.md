# Auditoría DFlash + n-gram para LlamaCode — 2026-09-14

## Resultado

La receta compartida para Qwen3.8 (DFlash2 + `ngram-mod`) no se puede promover en
LlamaCode con los artefactos actuales: no hay un drafter Qwen3.8 DFlash2 GGUF
compatible instalado y las pruebas anteriores del candidato vLLM fallaron con
`CUDA device-side assert` usando KV FP8. La variante que evita el assert usa KV
BF16, que supera el límite operativo del proyecto (máximo Q8), y pierde rendimiento
en sesiones largas.

Sí se pudo validar una implementación local de DFlash para Qwen3.6 base. Es un
runner separado (`lucebox-hub/dflash`), no el servidor LlamaCode, y por eso se
usó como prueba de rendimiento/estabilidad contra TERRA, no como reemplazo
automático.

## Artefactos usados

- Target: `/media/cristian/7CFE1E0FFE1DC1F6/models/Qwen3.6-27B-GGUF/Qwen3.6-27B-Q4_K_M.gguf`
- Draft: `/media/cristian/Disco local/Models/llamacpp/lucebox-hub/dflash/models/draft/model.safetensors`
- Runner: `/media/cristian/Disco local/Models/llamacpp/lucebox-hub/dflash/build-linux2/test_dflash`
- GPU: 2× RTX 3090, SM86, Linux, driver 595.71.05
- KV probado: Q8 para K/V; también Q4 para el escenario largo. No se usó BF16.

El GGUF ThinkingCap usado por TERRA no era intercambiable con este runner: tiene
65 capas, mientras que la implementación DFlash disponible exige el Qwen3.6 base
de 64 capas. Por eso se descargó el Qwen3.6 base Q4 en la carpeta de modelos
configurada por el proyecto.

## Pruebas locales

| Escenario | Configuración | Resultado | Lectura |
|---|---|---:|---|
| Coding corto | Target-only, KV Q8, 25 tokens de prompt, 64 tokens | 29,58 tok/s | Baseline del mismo target |
| Coding corto | DFlash + DDTree budget 16, KV Q8 | 51,21 tok/s | 1,73× sobre el baseline; salida válida |
| Coding corto | DFlash + DDTree budget 16, KV Q8 | aceptación media 3,76 tokens/paso | Aceptación modesta para este prompt |
| Contexto de 8K | DFlash + DDTree, KV Q8, 128 solicitados | 10,75 tok/s; aceptación 1,17 | La ventaja desaparece y el drafter casi no acepta |
| Contexto de 8K | DFlash + DDTree, KV Q4, 64 solicitados | 28,44 tok/s; aceptación 2,46 | Mejora frente a Q8, pero sigue debajo de TERRA corto |

La prueba Q8 de 8K terminó naturalmente en 7 tokens porque el modelo emitió el
fin de turno; no se contó como fallo. La variante Q4 generó los 64 tokens sin
error. En ambas configuraciones el target cargó correctamente y no hubo asserts,
crashes ni corrupción observable del runtime.

## Comparación con perfiles actuales

TERRA está medido en LlamaCode en aproximadamente 56–58 tok/s con MTP4, BCB
histórico 6/8 y visión. El DFlash local obtiene 51,21 tok/s sólo en el caso
corto, no tiene integración con el servidor de LlamaCode, no ejecuta el contrato
de tools de la aplicación y cae a 10,75 tok/s con contexto de 8K usando KV Q8.

Por lo tanto:

1. No reemplaza a SOL: no es Qwen3.8, no tiene la validación BCB 8/8 de SOL y
   carece de integración estable con el flujo de lanzamiento.
2. No reemplaza a TERRA: en el caso corto queda por debajo de 56–58 tok/s y en
   contexto largo es claramente inferior.
3. No se agregó un perfil ni se cambió ningún default del dropdown.
4. La idea de combinar DFlash con `ngram-mod` queda pendiente para un artefacto
   Qwen3.8 DFlash2 compatible y una prueba dentro del mismo `llama-server`; el
   runner Luce probado aquí no implementa esa combinación como perfil LlamaCode.

## Decisión para la tabla

No hay mejora superadora validada. Se conserva el orden y los defaults actuales:

- SOL: principal para coding/agentes.
- TERRA: razonamiento/visión.
- ASTRA: contexto grande experimental.
- GALACTA: máxima calidad con baja velocidad.

El runner DFlash queda como experimento externo documentado, no como perfil
prioritario. El modelo base descargado queda en `models/Qwen3.6-27B-GGUF` para
repetir la prueba cuando haya un draft Qwen3.6 actualizado o una integración
compatible con LlamaCode.
