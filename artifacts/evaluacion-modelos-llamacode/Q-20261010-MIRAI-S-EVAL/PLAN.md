# Plan — Q-20261010-MIRAI-S-EVAL

## Objetivo

Auditar el post «Mirai S 70 tok/s, 262k context, 12GB GPU» y el parche `mirai-s-ada`: separar qué parte es el modelo Mirai S, qué parte son cambios de runtime/caché/MTP, y si sus mejoras de agentes y contexto sirven para LlamaCode.

## Candidatos y controles

- Candidato anunciado: `trymirai/Qwen3.8-27B-S-experimental` en codec trellis de 2,4 bpw, convertido a GGUF por `alesha-pro`, servido con el engine `mirai-s-ada` basado en un fork de llama.cpp. La conversión añade tipos ggml propios; el stock llama.cpp de LlamaCode no es compatible. El perfil debe fijarse a revisiones y hashes exactos antes de cargar.
- Capa opcional: proxy OpenAI-compatible `mirai-s-ada/layer`, con API cards/check y `run_python` en WASI. Evaluar como perfil completo por separado; LlamaCode suele enviar herramientas cliente y eso cambia qué comportamiento del proxy se activa.
- Controles existentes: ASTRA IQ3_S y Flash-Next Q4 sobre Strata; SOL Qwen3.8-27B AutoRound INT4 sobre vLLM. Son perfiles completos distintos, no controles aislados de pesos. Reutilizar resultados actuales y no repetir fingerprints si no hay pregunta nueva.

## Protocolo preregistrado y gates

1. Verificar post, README, archivos/repositorios upstream y revisión/commits; distinguir la cifra de 70 tok/s a prompt corto de 262K de contexto disponible.
2. Revisar localmente si GGUF/runtime ya existen, el uso de GPUs, espacio y RAM. No descargar ni compilar hasta cerrar el preflight de origen, hashes, espacio y recursos.
3. Sin importar la cifra del post, no iniciar una suite de calidad si la proyección de tres semillas por perfil supera 30 minutos de pared. Usar Hard Mode v2.8.0/28 tareas × seeds 42/43/44 sólo si cabe el run completo. Máximo 29 min por perfil, preservando toda salida y deteniendo nuevas seeds si la proyección cruza el límite.
4. Si no cabe la suite de 28 casos, no usar un subset nuevo como si fuera el benchmark completo; cerrar como auditoría o proponer un screen corto con su propio nombre, si aporta una pregunta distinta y puede terminar en ≤30 min para tres semillas.
5. Aislar la capa y sus herramientas. No dar acceso a archivos/red/procesos al código generado; inspeccionar qué solicitudes de LlamaCode pasan por el proxy y cómo se tratan herramientas cliente. No activar el vector opcional de eliminación de refusals.
6. Para medir la receta de 12 GB, mantener caché q8_0 y límite documentado de posiciones KV en GPU, registrar VRAM/RAM/contexto efectivo/PCIe. Si no se puede reproducir ese límite, etiquetar comparación como perfil completo en 3090, no como réplica de 4070/12 GB.
7. Sin cambios a perfiles productivos, HarnessSpec o defaults. Reportar primera pasada separada de reparaciones; ninguna mejora general con una suite sola.

## Criterio de interés

Una comparación de calidad sólo entra en la shortlist si sus tres semillas por perfil terminan dentro de 30 minutos acumulados. Reportar score y tiempo total en la misma celda. No recomendar para agentes con permisos sin pasar los gates de aislamiento/tenant y herramientas; no inferir retrieval de contexto por configurar 262K.

## Estado inicial

Plan registrado antes de descarga, build del engine o uso de GPU. Fuentes identificadas; falta preflight local de artefactos y recursos. No hay aún hash de modelo/runtime fijado para una corrida.
