# Qwen3.8-Flash-Next W4A16-FP8PLE de albucino — auditoría 2026-09-26

## Veredicto

**No promover como perfil superior de agente ni como reemplazo de SOL.** El
runtime publicado el 25 de septiembre reporta una mejora grande de throughput
en el mismo tipo de hardware (2× RTX 3090), pero esas cifras son externas y no
miden calidad agentiva. La receta requiere 128 GiB de RAM; esta sesión informa
61,7 GiB. No se inició el servidor ni se descargaron los 116 GiB del checkpoint.

Clasificación por uso:

| Área | Veredicto | Evidencia y límite |
|---|---|---|
| Throughput de Flash-Next | **Superior según el reporte del mantenedor; sin réplica local** | El perfil actualizado publica hasta 104,5 tok/s de decode y 2.752 tok/s de prefill en una petición con 131.072 tokens de entrada. A 260.096 tokens publica hasta 103,1 tok/s y 2.654 tok/s. No es un A/B de LlamaCode ni demuestra más calidad. |
| Agente de código y tools | **Sin mejora demostrada; no promover** | La campaña local previa del mismo checkpoint con el runtime anterior dejó 1/8 en BCB directo, errores de JSON y tool-use limitado. El nuevo runtime cambia inferencia/rendimiento, no los pesos objetivo. Falta repetir HE0/HE20/BCB8 con el runtime nuevo. |
| Visión / Computer Use | **Candidato manual, calidad amplia pendiente** | El repositorio del runtime incluye una configuración de visión hot80 y registra tres smokes con imágenes sintéticas. El mismo repositorio aclara que visión no se volvió a medir en el perfil fast-256k; no hay prueba con Computer Use de LlamaCode. |
| Charla | **Sólo podría reemplazar el backend de texto** | El checkpoint es un modelo de generación de texto con encoder de visión opcional; no es un modelo de audio y no reemplaza STT/TTS. Su integración exigiría un servidor vLLM externo y 128 GiB de RAM. No se midió latencia extremo a extremo de Charla. |
| Adecuación a esta PC | **Inferior / no ejecutable con el hardware de esta sesión** | Hay 2× RTX 3090, pero Windows reporta 61,7 GiB de RAM y WSL ve 30 GiB con 8 GiB de swap. El mantenedor especifica 128 GiB y al menos 32 GiB de swap rápido para cargarlo; no alcanza con bajar el contexto. |

Por eso quedaron tres perfiles **manuales y fuera de la cola automática** en
`assets/system_profiles.json`, todos con requisito de 128 GiB de RAM: el fast256k
actual hot84, una réplica del post con hot88/220k y una variante de visión hot80.
Comparten el endpoint local `127.0.0.1:8000`; sólo se puede ejecutar una
variante a la vez. LlamaCode conecta al servidor, pero no instala ni inicia el
runtime externo.

## Qué contiene el checkpoint y qué cambió

El checkpoint está fijado a
`albucino/Qwen3.8-Flash-Next-W4A16-FP8PLE@ef554143369a706525336f6b42a09094835dc077`.
Su target combina AutoRound W4A16 con capas sensibles BF16 y la tabla PLE en
FP8; el paquete reporta 116,183 GiB de payload más 3,855 GiB para el draft MTP.
No es un GGUF. La receta publicada requiere el runtime vLLM con overlay del
repositorio
[`DominikBucko/qwen38-flash-next-2x3090`](https://github.com/DominikBucko/qwen38-flash-next-2x3090),
Linux, dos RTX 3090 y RAM abundante.

El texto de Reddit reporta hot88, contexto 220k, alrededor de 80 tok/s y más de
2k tok/s de prefill. La página del checkpoint ahora describe además el runtime
fast-256k publicado el 25 de septiembre: hot84, MTP3, KV BF16 y optimizaciones
de prefill/P2P. Sus tres corridas de 131k dan 94,2–104,5 tok/s de decode y
2.693–2.757 tok/s de prefill. Para 260.096 tokens da 92,6–103,1 tok/s y
2.653–2.654 tok/s de prefill. El mantenedor dice que los pesos objetivo no
cambiaron. Estas cifras son throughput de servicio; no son una evaluación de
respuestas, herramientas ni Computer Use.

El hot88 del post no es la recomendación actual del mantenedor: hot84 es el
valor publicado por defecto para dejar más margen de prefill. El perfil hot88
se conserva sólo como réplica experimental, no como configuración preferida.

## Pruebas y límites locales

No se inició vLLM en esta sesión:

- El host Windows reportó **61,7 GiB de RAM física**, frente a 128 GiB requeridos
  por el runtime. WSL expone **30 GiB** y sólo 8 GiB de swap.
- El checkpoint albucino de 116 GiB no está en el cache local. El cache contiene
  una variante GGUF de Unsloth, que no sirve para este runtime W4A16.
- La conexión del cliente Docker al motor Linux falló porque no estaba
  disponible `dockerDesktopLinuxEngine`.
- Ya había un `llama-server.exe` de otro proyecto usando ambas GPU. No se lo
  detuvo ni se alteró su sesión.

El repositorio ya conserva pruebas previas del checkpoint albucino con un
runtime anterior. En la evaluación de septiembre el modo texto midió
23,6–40,2 tok/s de pared, con un caso JSON que no respetó el esquema y **1/8 BCB
directo**. Un smoke de visión sobre una imagen sintética respondió
`red blue 5` sin MTP; la combinación MTP3+visión falló en warmup por una aserción
CUDA. Son resultados de aquella versión, no del runtime fast-256k actual. El
detalle está en
[`qwen38-flash-next-zram-audit-20260919.md`](qwen38-flash-next-zram-audit-20260919.md).

Contra SOL, la referencia local vigente conserva BCB8 8/8, tool-use estable y
visión 4/4. El nuevo reporte de velocidad no revierte esa comparación de
calidad. Para Computer Use sólo hay un smoke visual sintético público; no se
midieron capturas reales, cambios de resolución/idioma, secuencias de control
ni tasa de éxito de tareas.

## Siguiente campaña si se dispone de 128 GiB

La comparación debe usar el runtime y checkpoint fijados, primero hot84, con
una sola variante activa:

1. Repetir 131.072 + 2.048 y 260.096 + 2.048 para contrastar TTFT, prefill,
   decode sostenido, swap y RAM con el reporte del 25 de septiembre.
2. Comparar hot84/256k contra hot88/220k con el mismo prompt y suite. Registrar
   OOM, margen de VRAM, fallos de prefill y tráfico de swap; no inferir ganador
   desde el valor máximo publicado.
3. Ejecutar HE0 → HE20 → BCB8 con el mismo `agent-maximo`, prompt pack y
   condiciones que SOL. Hasta cerrar esta prueba, no declararlo superior como
   harness de código.
4. Activar la variante hot80 y validar una imagen por request, Computer Use con
   capturas reales y sensibilidad a resolución/idioma. La prueba sintética no
   alcanza para promoverla.
5. Conectar el endpoint a Charla y medir latencia extremo a extremo con el
   mismo STT/TTS actual; el modelo sólo aporta la parte de texto.

## Fuentes primarias

- [Checkpoint y mediciones publicadas](https://huggingface.co/albucino/Qwen3.8-Flash-Next-W4A16-FP8PLE)
- [Resultados reproducibles del 25 de septiembre](https://github.com/DominikBucko/qwen38-flash-next-2x3090/blob/main/benchmarks/2026-09-25/README.md)
- [Configuración y límites de rendimiento](https://github.com/DominikBucko/qwen38-flash-next-2x3090/blob/main/docs/performance.md)
- [Perfil y smokes de visión](https://github.com/DominikBucko/qwen38-flash-next-2x3090/blob/main/docs/vision.md)
- [Memoria, swap y riesgo de OOM](https://github.com/DominikBucko/qwen38-flash-next-2x3090/blob/main/docs/memory.md)
