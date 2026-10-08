# Auditoría de referencia externa: 2× RTX 3090 y Qwen3.8-27B — 2026-09-18

## Resultado

La publicación aporta referencias útiles de hardware y concurrencia, pero no
una mejora reproducible para LlamaCode.

El autor informa aproximadamente **70 tok/s sostenidos** con Qwen3.8-27B Q4 en
dos RTX 3090 y otra respuesta informa **~50 tok/s de generación y ~1.000 tok/s
de prefill** con Q8 y contexto completo. No se publican BCB8, HE, tool-use,
visión, aceptación MTP ni una receta completa que permita aislar modelo,
backend, KV, contexto y batch.

## Comparación con nuestra evidencia

| Ruta | Resultado local registrado | Interpretación |
| --- | ---: | --- |
| SOL, vLLM TP2/P2P + MTP4 | 74 narrativo / 102 código tok/s | Sigue siendo superior como agente; BCB 8/8 y tool-use estable |
| GGUF Qwen3.8 por capas | ~60,75 tok/s | Cerca de la referencia Q4, pero no tiene la validación agentiva de SOL |
| QWEN38-Q8 llama.cpp | 41,3 tok/s a 8K / 22,1 a 262K | El resultado externo de ~50 tok/s no es comparable sin fijar KV, contexto y backend |
| Dos sesiones concurrentes externas | ~2×70 tok/s agregados a ~50K | Es throughput agregado, no velocidad de una sesión; sirve como hipótesis para subagentes |

La diferencia entre ~60,75 y ~70 tok/s no justifica reemplazar SOL: puede provenir
de otra revisión de llama.cpp, otro quant Q4, batch/ubatch, KV, temperatura,
contexto real o medición warm. Faltan las métricas de calidad que definirían una
promoción.

## Qué sí es transferible

### Concurrencia

La observación de dos sesiones simultáneas es coherente con el diseño de
subagentes de LlamaCode, pero debe medirse como throughput agregado y con una
cuota de contexto por worker. No debe presentarse como “140 tok/s para un único
agente”. La configuración segura sigue siendo perfil-dependiente:

- una sesión principal con el máximo contexto;
- dos workers con contexto dividido cuando la prioridad es throughput;
- no reservar tres sesiones largas sin medir VRAM, KV y prefill concurrente.

### Hardware y estabilidad

El autor menciona un riser sin marca con problemas de conectividad. En nuestra
máquina las dos GPU están en el mismo root complex, P2P lectura/escritura ya
fue validado y la topología local es `PHB`. No hay evidencia de que cambiar
nuestro montaje o comprar un riser mejore los perfiles actuales; sí sería una
recomendación de estabilidad si aparecieran errores PCIe, resets o corrupción.

La sugerencia de 128 GB de RAM puede ayudar a modelos MoE con mmap/SSD-offload,
pero no convierte Q4/Q8 en un perfil agentivo mejor ni arregla tensor split.
Para SOL, el cuello validado es el backend/modelo, no la falta de RAM del host.

### Acceso remoto

Tailscale + SSH es una alternativa operativa razonable para administrar una
máquina de inferencia. No cambia PP/TG ni la calidad del modelo y no requiere
modificar los perfiles de LlamaCode.

## Decisión

- No descargar otro Q4 sólo por esta publicación.
- No cambiar SOL ni sus argumentos.
- Mantener la ruta GGUF Q4 como experimental si se necesita comparar
  llama.cpp, pero exigir A/B en la misma máquina.
- Mantener QWEN38-Q8 como referencia de fidelidad/contexto, no como default.
- Registrar la concurrencia como una prueba futura de subagentes, con métricas
  de throughput agregado, TTFT por worker, VRAM y tasa de éxito del harness.

## Prueba futura bien aislada

Si se vuelve a disponer del GGUF Q4 local, la comparación válida sería:

1. mismo commit de llama.cpp y misma build CUDA;
2. contexto 8K, 32K, 64K y 131K;
3. KV fijo y documentado;
4. MTP apagado y MTP encendido en corridas separadas;
5. una sesión y dos sesiones concurrentes;
6. PP, TG, TTFT, VRAM, BCB8 y tool-use;
7. visión sólo en una matriz separada con `mmproj` idéntico.

Hasta completar esa matriz, la publicación es una referencia de rendimiento
externo, no evidencia para promover un perfil.
