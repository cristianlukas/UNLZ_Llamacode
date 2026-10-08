# Auditoría del tuning AMD/Vulkan de Qwen3.8-Flash-Next — 2026-09-14

## Resultado

El post es un estudio útil de un sistema híbrido AMD/Vulkan con una RX 9060 XT
de 16 GB, Ryzen 5950X y 64 GB de RAM. No es directamente transferible a nuestra
configuración de dos RTX 3090 con CUDA/P2P, y ninguna de sus variantes supera los
perfiles principales de LlamaCode.

La recomendación operativa no cambia: **SOL** queda como principal para coding,
**TERRA** como perfil estable de razonamiento/visión y **ASTRA** sigue siendo
experimental para contexto grande.

## Comparación de las hipótesis del post con nuestras pruebas

| Idea del post | Evidencia local | Decisión |
|---|---|---|
| Ajustar cantidad de threads | Es relevante en híbridos CPU/RAM/GPU, pero SOL/TERRA corren principalmente en GPU y ASTRA ya tiene mediciones CUDA específicas | No cambiar defaults |
| KV Q8 frente a F16 | Nuestro límite máximo es Q8. ASTRA con KV Q8 ya fue probado; F16 no corrige su problema de calidad | Mantener Q8 |
| Mover más expertos a GPU | En CUDA, `-ot` ahorró sólo ~32 MiB y podía ser más lento. La ubicación alineada de expertos sí importa en DeepSeek, pero no mejora ASTRA automáticamente | No agregar overrides genéricos |
| `lazy-mode on` | ASTRA: reportó TPS bruto alto pero devolvió `////`, salida corrupta | Rechazado |
| `lazy-mode on-direct` | Salida válida, pero ~7,54 tok/s contra ~14,87 tok/s del control comparable | Rechazado |
| `load-mode none` | Carga ~67,6 s contra ~10 s, con generación esencialmente igual | Mantener mmap |
| Afinidad CPU manual | La medición previa perdió rendimiento (~0,93%) | No fijar afinidad |
| MTP para Flash-Next | El cabezal/sidecar disponible fue incompatible; con expert-cache produjo acceso ilegal CUDA | No activar |
| Buscar 20 tok/s por tuning | Las variables restantes dieron cambios negativos o neutros; no hay evidencia de +23,5% | No seguir ajustando al azar |

## Números locales relevantes

| Perfil/variante | Resultado local | Calidad/estado |
|---|---:|---|
| ASTRA, cache MoE 188 | ~16–41 tok/s según contexto; ~16 tok/s en la matriz estable | HE0/BCB no válidos; salida corrupta o no confiable |
| ASTRA, `lazy off`, Q8 | 14,87 tok/s decode en prueba comparable | Código válido, pero perfil experimental |
| ASTRA, `lazy on-direct`, Q8 | 7,54 tok/s decode | Correcto, pero 49% más lento |
| TERRA, Qwen3.6/ThinkingCap MTP | ~56–58 tok/s histórico; 70,37 tok/s en la campaña corregida | BCB 8/8, visión, tool-use válido |
| SOL, Qwen3.8-27B MTP/vLLM | 74 narrativo / 102 código | BCB 8/8, tool-use y visión validados |
| Qwen3.8-27B vs Flash-Next | El 27B ganó 1/9 pares válidos; Flash 0/9; 8 empates | Flash no demostró superioridad de calidad |

El post reporta 16,19 tok/s para Flash-Next en su RX 9060 XT. Ese número es
coherente con nuestro ASTRA estable, pero no representa una mejora frente a
TERRA o SOL y proviene de otra plataforma, backend y reparto de memoria.

## Lecciones metodológicas reutilizables

Sí son útiles para futuras campañas, aunque no justifican un cambio de perfil:

1. Hacer un preflight de 2–3 prompts y exigir `finish_reason=stop`, contenido
   final presente y ausencia de bucles de razonamiento antes de lanzar una
   batería de calidad.
2. Separar velocidad de generación, prefill, tiempo de carga y estabilidad.
3. No interpretar mayor utilización de GPU como mayor rendimiento cuando hay
   expertos híbridos y transferencias CPU↔GPU.
4. No comparar un resultado de throughput agregado o de otra arquitectura con
   el decode single-stream de LlamaCode.
5. Mantener una configuración control y cambiar una sola variable por vez.

## Decisión

No se modificaron perfiles, argumentos ni defaults. No se descargaron modelos:
el target Flash-Next y los artefactos necesarios ya están presentes y todas las
variables relevantes del post cuentan con pruebas locales previas.

ASTRA permanece útil sólo cuando se priorizan documentos/contexto grande y se
acepta su carácter experimental. Para agentes y coding siguen siendo superiores
SOL y TERRA por calidad validada, estabilidad y tool-use.
