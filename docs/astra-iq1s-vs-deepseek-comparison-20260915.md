# Validación detallada: ASTRA IQ1_S vs DEEPSEEK FUSION vs GALACTA

Fecha: 2026-09-15  
Equipo: Ubuntu, 2× RTX 3090, P2P disponible, Ryzen 9 9950X3D, ~123 GiB de RAM  
Runner: `cuda-flashnext-2x3090/llama-server`, build `9bd97fe`  
Límite respetado: KV y pesos cuantizados no mayores que Q8.

## Alcance

Se repitieron pruebas con el mismo runner y una receta comparable para los tres
artefactos. Se midieron:

- respuesta de código, lógica, aritmética y JSON;
- PP (prefill) y TG (decode) en solicitudes cortas;
- carga y respuesta con contexto largo;
- estabilidad de la sesión y errores CUDA;
- evidencia previa de HE0, HE20, BCB y tool-use.

La micro-suite es diagnóstica, no reemplaza BCB: seis tareas cortas no tienen la
dificultad, reparación ni ciclo de herramientas del benchmark agentivo.

## Recetas probadas

| Perfil | Modelo | KV | Contexto | Configuración relevante |
|---|---|---:|---:|---|
| ASTRA IQ1_S | Qwen3.8 Flash-Next UD-IQ1_S | Q8 | 8K y 262K | `lazy-mode on`, `split-mode layer`, caché experto 188; a 262K `fit on`, `batch 256`, `ubatch 64`, `gpu-layers auto` |
| GALACTA | DeepSeek V4 Flash UD-IQ3_S | Q4 | 8K y 131K | 44 capas GPU, 39 expertos CPU, Flash Attention, `batch 1024`, `ubatch 512` |
| DEEPSEEK FUSION | DeepSeek V4 antirez Q2/Q4 | Q4 | 8K y 131K | expertos 37–42 en CUDA1, resto CPU, `cpu-moe`, `cache-ram 32 GiB`, Flash Attention |

No se usó BF16 para KV, no se habilitó un quant superior a Q8 y no se mezcló un
`mmproj` ajeno. Los dos artefactos DeepSeek no tienen una ruta visual compatible.

## Rendimiento fresco

Los números de esta tabla corresponden a la primera solicitud después de cargar
el servidor, salvo donde se indica lo contrario.

| Perfil | Prueba | PP | TG | Resultado |
|---|---|---:|---:|---|
| ASTRA IQ1_S | 8K, código/lógica, sin MTP | 149,40 | 56,52 | Python válido |
| ASTRA IQ1_S | 8K, repeticiones con prefijo cacheado | 51,40–54,11 | 58,86–62,65 | Válido; PP no es comparable con el cold start |
| ASTRA IQ1_S | 262K, marcador exacto | 37,80 | 36,44 | `CONTEXT_262K_OK` exacto |
| GALACTA | 8K, consulta larga de código | 19,51 | 12,35 | Python válido |
| GALACTA | 8K, dos repeticiones warm | 9,91–11,24 | 12,41–12,47 | JSON y código válidos |
| GALACTA | 131K, marcador exacto | 8,63 | 11,66 | `GALACTA_131K_OK` exacto |
| DEEPSEEK FUSION | 8K, consulta larga de código | 31,82 | 13,85 | Python válido |
| DEEPSEEK FUSION | 8K, tres repeticiones warm | 20,38–20,78 | 13,46–13,94 | JSON y código válidos |
| DEEPSEEK FUSION | 131K, marcador exacto | 21,47 | 11,52 | `FUSION_131K_OK` exacto |

La diferencia de ASTRA entre 8K y 262K no implica que sea un agente más rápido:
el resultado de 262K usa una solicitud mínima y buffers mucho más pequeños. En
sesiones reales con contexto lleno, la referencia conservadora sigue siendo
24–26 TG para IQ1_S sin MTP, según la auditoría específica del modelo.

## Micro-suite funcional común

La suite contiene: `add`, `is_prime`, `reverse_words`, `37*19`, JSON semántico
`{"ok":true,"value":42}` y una respuesta lógica exacta.

| Perfil | Resultado | TG observados por tarea | Observación |
|---|---:|---:|---|
| ASTRA IQ1_S | **6/6 semánticamente** | 34,32–57,00 | El primer conteo estricto fue 5/6 sólo porque el matcher exigía espacios en JSON; la salida `{"ok":true,"value":42}` era JSON válido. |
| GALACTA | **6/6** | 3,48–8,75 | Todas las respuestas fueron evaluables; es correcto pero muy lento con esta receta de CPU-MoE. |
| DEEPSEEK FUSION | **6/6** | 12,00–13,87 | Todas las respuestas fueron evaluables y fue el DeepSeek más rápido en esta micro-suite. |

Este resultado no autoriza a convertir ASTRA en BCB 6/6: la suite no cubre
edición de archivos, reparación, ejecución de tests ni múltiples turnos.

## Contexto, estabilidad y visión

### ASTRA IQ1_S

- **262K:** carga y responde correctamente usando `fit on`; quedó demostrado con
  un marcador exacto.
- **MTP:** el head Q4 original no es compatible; el head compartido Q8 sí tiene
  los tensores `nextn` correctos. Sin embargo, la receta MTP actual reprodujo un
  **OOM durante `cudaGraphInstantiate`** al atender la primera solicitud a 8K.
  La campaña anterior sí obtuvo 41,63–58,49 TG y aceptación 48/48 con ese head,
  por lo que queda como evidencia experimental, no como ruta estable.
- **Visión:** no validada. El `mmproj` oficial de Flash-Next ya fue probado antes:
  con proyector GPU terminó en acceso ilegal CUDA y con proyector CPU produjo
  salida repetitiva. No se debe marcar como multimodal.
- **Calidad/agencia:** la IQ1_S tiene micro-suite válida y un BCB parcial de un
  ítem, pero no HE20/BCB completo reproducible. No es comparable con SOL ni con
  GALACTA en calidad agentiva.

### GALACTA

- **131K:** carga y responde correctamente con marcador exacto.
- **Calidad:** conserva la evidencia fuerte de **HE0 1/1, HE20 20/20 y BCB
  8/8**, con ~9,65 tok/s en la corrida agentiva registrada.
- **Tool-use:** el resultado histórico BCB 8/8 es la evidencia válida de agencia;
  un smoke directo nuevo con `tool_choice=required` no terminó dentro del límite
  práctico de la receta mínima y no se convirtió artificialmente en fallo.
- **Visión:** no aplica: el artefacto es text-only en nuestro catálogo.

### DEEPSEEK FUSION

- **131K:** carga y responde correctamente con marcador exacto.
- **Calidad/agencia:** el histórico del antirez exacto informa **BCB 8/8 y
  10,55 tok/s**, pero las repeticiones actuales de variantes Q2/Q4 no son
  uniformes: hay campañas registradas con **2/8 y 4/8**. Por eso el 8/8 se
  conserva como histórico de esa variante/configuración y no como garantía del
  archivo actual.
- **Velocidad:** fue algo más rápido que GALACTA en las pruebas cortas
  actuales, pero no alcanza una diferencia suficiente para compensar la menor
  consistencia agentiva documentada.
- **Visión:** no aplica: no hay `mmproj` compatible.

## Comparación final

| Dimensión | 1.º | 2.º | 3.º | Lectura correcta |
|---|---|---|---|---|
| Calidad agentiva validada | GALACTA | FUSION histórico | ASTRA IQ1_S | GALACTA tiene la evidencia más sólida y reproducible |
| Velocidad de decode corto | ASTRA IQ1_S | FUSION | GALACTA | ASTRA gana, pero la cifra cae con contexto real y no equivale a BCB |
| Prefill en la receta actual | ASTRA IQ1_S | FUSION | GALACTA | FUSION supera a GALACTA; ASTRA usa otra familia/receta y caché de prefijos |
| Contexto operativo validado | ASTRA IQ1_S: 262K | FUSION: 131K | GALACTA: 131K | ASTRA es el único candidato de contexto extremo de esta comparación |
| Visión | Ninguno | Ninguno | Ninguno | No se agrega una marca visual a ninguno de los tres |
| Estabilidad de promoción | GALACTA | FUSION histórico | ASTRA IQ1_S | ASTRA queda experimental por MTP/BCB/visión pendientes |

## Decisión para LlamaCode

1. **No reemplazar SOL.** SOL sigue siendo el default por BCB 8/8, tool-use,
   visión validada en su receta vLLM/AutoRound y mejor equilibrio de velocidad.
2. **GALACTA** sigue siendo la opción de máxima calidad cuando el tiempo no es
   crítico.
3. **DEEPSEEK FUSION** conserva sentido como alternativa DeepSeek algo más
   rápida, pero debe mostrar sus resultados como históricos por variante; no se
   debe presentarlo como superior a GALACTA en calidad.
4. **ASTRA IQ1_S** queda como perfil experimental de contexto extremo/menor
   presión de VRAM. No se promueve a agente principal, no se le agrega visión y
   no se activa MTP por defecto mientras la receta actual falle con OOM de CUDA.
5. No se cambiaron pesos, dropdown, límites de quant/KV ni Windows. Al terminar
   las pruebas no quedó ningún `llama-server` activo.

