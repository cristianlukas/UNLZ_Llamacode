# Auditoría iterativa: Flash-Next frente a SOL

Fecha: 2026-09-19  
Hardware: Ryzen 9 9950X3D, 2× RTX 3090 24 GB  

## Objetivo

Verificar si alguna de estas variantes de Qwen3.8 Flash-Next supera a SOL en
calidad agentiva, tool-use, estabilidad o velocidad útil para LlamaCode:

- `ASTRA IQ1_S`
- `ASTRA IQ4_XS`
- `Flash-Next EXL3 4.05 bpw h6 ng6`

No se considera superior una cifra aislada de TG si el perfil no entrega
implementaciones correctas, no completa herramientas o no tiene una medición
de calidad comparable.

## Base reproducible

Para IQ1_S e IQ4_XS se utilizó el checkout adaptado de llama.cpp:

- Ruta: `/media/cristian/Disco local/Models/llamacpp/llama.cpp-lazy-28136`
- Commit: `c6a9e5c9` (incluye arquitectura `qwen4exp`)
- Binario de prueba:
  `/media/cristian/Disco local/Models/llamacpp/llama.cpp-lazy-28136/build-linux-qwen4exp-20260919/bin/llama-server`
- CUDA 12.0 y NCCL detectados durante la compilación.
- `split-mode layer`, Flash Attention, KV `q8_0`, una sesión, batch 1024,
  ubatch 512, mmap, muestreo conservador de LlamaCode (`temp 0.6`, `top-p
  0.95`, `top-k 20`, `min-p 0`, repeat penalty 1.0).

Se probaron contextos cortos y largos, `lazy-mode on/off`, código Python,
tool-use con calculadora y, cuando el runtime lo permitió, visión.

SOL se mantuvo como referencia productiva en vLLM TP2/P2P, MTP4, KV FP8 y
262K. Sus mediciones validadas son BCB 8/8, HE20 20/20, tool-use estable,
visión 4/4 y 74 TG narrativo / 102 TG de código.

## Resultados

| Perfil | PP/TG observado | Tool-use / visión | Calidad comparable | Lectura |
|---|---:|---|---|---|
| **SOL** | 74 narr. / **102 código** | Tool-use estable; visión 4/4 | **BCB 8/8; HE20 20/20** | Referencia productiva |
| **ASTRA IQ1_S** | 8K: **79,75 / 57,13**; 262K: **122,21 / 54,69** | Calculadora válida: 211,88 / 60,22; sin mmproj compatible probado | Micro-suite previa 4/6; BCB completo y HE20 pendientes | Mejor ruta de bajo consumo/contexto, sin evidencia de mayor calidad |
| **ASTRA IQ4_XS** | 8K lazy off: 83,36 / 37,11; 8K lazy on: 83,74 / 36,56; 131K: 66,04 / 35,39 | Calculadora válida: 189,27 / 38,17; visión no resuelta en esta ruta | Sin BCB8/HE20 válido; historial de salida corrupta no se reprodujo en el smoke corto | Más pesado y claramente más lento que IQ1_S/SOL en decode |
| **Flash-Next EXL3** | 262K CPU-MoE: 34,5 TG; tool: 36,2 TG | Tool-call válido; visión funcional a 131K | Pack directo: 2/8 no entregaron implementación antes de 1400 tokens; los otros 6 requieren grader; historial BCB 1/8 | Visión experimental, pero sin calidad superior y más lento |

## Iteraciones y fallos aislados

### 1. Binario anterior

El binario Linux anterior rechazaba `qwen4exp` antes de cargar el modelo. Era
un bloqueo de infraestructura, no una medición de calidad. Se recompiló un
checkout que sí incluye la arquitectura.

### 2. IQ1_S con `lazy-mode`

La configuración `lazy-mode on` cargó correctamente a 8K y 262K, produjo código
válido y una llamada de herramienta válida. Por lo tanto, IQ1_S es operacional
en el runtime adaptado. No se encontró un head MTP compatible en los artefactos
disponibles para convertir esa ruta en una comparación agentiva completa.

### 3. IQ4_XS con `lazy-mode`

Se probaron `lazy-mode off` y `on`, a 8K, y `off` a 131K. El resultado corto
fue válido también con `on`; no se reprodujo la corrupción histórica del smoke
anterior. Sin embargo, eso no constituye una validación de calidad: el modelo
no tiene BCB8/HE20 comparable y el rendimiento queda muy por debajo de IQ1_S y
SOL. Su carga además tarda varios minutos.

### 4. EXL3 con tensor parallel y CPU-MoE

El intento TP falló con:

```text
NotImplementedError: Tensor-parallel is not currently implemented for
Qwen4ExpForConditionalGeneration
```

Es una limitación del backend ExLlamaV3, no una prueba de que los pesos sean
malos. La ruta alternativa CPU-MoE cargó a 262K, generó Python y atendió
tools; aun así produjo aproximadamente 34–36 TG y el pack directo dejó dos de
ocho casos sin implementación, por lo que no puede competir con BCB 8/8 de
SOL.

### 5. Visión

EXL3 sí describió correctamente una imagen de prueba a 131K. No se consiguió
una pareja `mmproj`/runtime compatible para IQ1_S o IQ4_XS en esta campaña. La
visión funcional de EXL3 no compensa la falta de calidad agentiva comparable.

### 6. MTP y DFlash

No se promovió MTP: los heads disponibles no forman una combinación validada
con estos artefactos y el head GGUF antiguo ya había mostrado incompatibilidad
de tensores. Tampoco se inventó una ganancia DFlash sin un drafter compatible,
aceptación medida y BCB bajo el mismo harness.

### 7. Matriz adicional de calidad y runtime

Para separar modelo, plantilla, sampling, contexto y motor, se repitió IQ4_XS
con el mismo pack de BigCodeBench y el mismo grader; sólo cambiaron las
variables indicadas:

| Configuración | Resultado | Observación |
|---|---:|---|
| IQ4, `qwen38-tools-fixed`, `temp 0,6`, contexto 16K | **1/8** | Pasó 870; falló 509, 857, 310, 800, 123, 952 y 492 por errores de implementación, formato o datos. |
| IQ4, plantilla stock del GGUF, `temp 0,2`, contexto 8K | **1/3** | 870 pasó; 509 y 857 agotaron 120 s sin entregar una función evaluable. |
| IQ4, plantilla corregida, `reasoning on`, `temp 0,2`, contexto 8K | **0/1** | Agotó 120 s sin código evaluable. Activar thinking no reparó la ruta agentiva. |
| IQ4, `llama.cpp master` `ad6c6683`, plantilla corregida, `temp 0,6`, contexto 16K | **1/3** | 870 pasó; 509 y 857 fallaron. La calidad fue igual al branch anterior, pero la primera corrida midió aprox. 35 PP / 5,6 TG. |

El `master` contiene correcciones recientes de `qwen4exp` para estado
recurrente, indexador, rollback y cortes del grafo, pero no cambió el resultado
BCB y fue más lento en esta máquina. Queda como binario de investigación, no
como runtime productivo.

Los fallos tampoco son sólo de formato: aparecen errores semánticos concretos
en CSV, filesystem, excepciones, fechas y tipos. Por eso no se arreglan de
forma suficiente cambiando temperatura, plantilla o activando thinking.
`LLAMA_ATTN_ROT_DISABLE=1` y `--no-cache-prompt` se mantienen como guardas de
estabilidad para `qwen4exp`, no como mejoras de calidad.

### 8. Revisión de motores alternativos

La revisión upstream tampoco justifica cambiar de motor sólo para este modelo:

- vLLM ya tiene soporte base para Flash-Next, pero su propio tracking mantiene
  pendientes de optimización de kernels, FP8 de KV, PLE/offload y planificación
  MoE: <https://github.com/vllm-project/vllm/issues/55922>.
- DFlash/DeepSpec para `qwen4_exp` todavía requiere varios parches de control y
  tiene bloqueos arquitectónicos documentados: <https://github.com/vllm-project/vllm/issues/56088>.
- ExLlamaV3 carga la variante EXL3 con CPU-MoE, pero la ruta TP falla localmente
  porque todavía no implementa tensor parallel para `Qwen4Exp`.

Por lo tanto, cambiar a vLLM o ExLlamaV3 no ofrece hoy una ruta reproducible
para superar el BCB de SOL con estas tres variantes. El motor alternativo sólo
sería razonable al validar un checkpoint FP8/NVFP4 específicamente soportado,
con sus kernels y MTP compatibles; no conviene convertir una cuantización
experimental en el perfil productivo.

## Conclusión

Ninguno de los tres modelos demostró ser más inteligente que SOL. En este
hardware y flujo:

1. **SOL continúa como default**: es el único con BCB 8/8, HE20 20/20,
   tool-use estable y visión 4/4 bajo validaciones comparables.
2. **IQ1_S queda como experimental de contexto/consumo**: es el candidato más
   interesante de los tres por su TG y 262K, pero no tiene BCB completo ni
   visión validada; no reemplaza a SOL.
3. **IQ4_XS queda como referencia de fidelidad/experimento**, no como perfil
   productivo: es más pesado, más lento y no tiene evidencia de mejor calidad.
4. **EXL3 queda como experimental multimodal**, útil para investigar visión y
   CPU-MoE, pero su TP todavía no está implementado y su pack directo ya
   mostró fallos de finalización incompatibles con una promoción.
5. **No se promocionó ninguna nueva receta**: Flash-Next conserva interés para
   contexto/consumo, pero permanece muy por debajo de SOL en calidad agentiva
   comparable. Para LlamaCode conviene mantener `reasoning off` en coding,
   los guards de atención/cache y no seleccionar automáticamente el branch
   nuevo ni el contexto extremo.

No se modificó el default, la tabla productiva ni se borraron estos artefactos.
La siguiente prueba que podría cambiar la decisión sería ejecutar BCB8/HE20
completo en IQ1_S con un head MTP/Qwen4Exp realmente compatible y el mismo
harness LC-H1; hasta entonces, promover cualquiera de ellos sería afirmar una
calidad que las pruebas no demostraron.
