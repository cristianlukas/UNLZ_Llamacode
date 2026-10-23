# Q54 — gate de calidad baseline Qwen3.8-27B MTP2, seed 43

Estado: activo; preregistro antes de iniciar el servidor.

## Pregunta y valor de decisión

La suite Hard Mode baseline seed 42 completó 28 escenarios, pero TC-72 y TC-88 fallaron por errores PEG/server y se excluyeron los scores comparables. La prueba única de seed 43 comprobará si el bloqueo se limita a seed 42 o si el baseline llama.cpp MTP2 continúa inestable en esos casos. Si falla, detener la calidad OpenJet sin repetir. Si pasa, deja una seed completa válida para preregistrar una nueva matriz matched. No afirma superioridad ni adopción por sí sola.

## Prerregistro

- Brazo único: baseline `llama.cpp` MTP2, commit `39eab74a05d3e68ac822b6dc6cd78c90cb985c19`; GPU0 RTX 3090. No se inicia OpenJet en esta iteración.
- GGUF Q4_K_M MTP fijado en Q47: `/media/cristian/HDD extra/Modelos-eval/Q47-OpenJet/Qwen3.8-27B-Q4_K_M.gguf`, SHA-256 `7e78da5d7e3ae28d178121f58646953305f3e5bd3cb46f4a75584e8b6c6fe169`; stat anchor Q47 obligatorio; sin descarga/copia.
- Tool-Eval Bench 2.8.0, mismo commit `0a1ba68c7709f429298bc92417a9e003f61de4e3`, categoría Hard Mode completa TC-70–TC-97 (28 escenarios), seed 43, variant seed 20261010, temperature 0.6, top-p .95, top-k 20, min-p 0, repeat penalty 1, reasoning medium en `chat_template_kwargs`, contexto 16384, timeout 120 s, max 8 turns, paralelismo 1.
- El cambio respecto de la suite baseline/42 es únicamente la seed (42→43); se conserva suite, GGUF, template, backend y sampling. La smoke de herramientas medium 3/3 previamente aprobada para baseline/d3/d4 se reutiliza; no se vuelve a ejecutar ni se repite seed42.
- Validación: exit 0, versión/configuración exactas, 28 IDs en orden, sin errores API/parser/PEG, auditoría independiente de puntos y score. Registrar aparte TC-74/84/92 y safety warnings; una suite técnicamente válida no implica pase de seguridad.

## Guardas y parada

El controlador corre como servicio transient del usuario bajo cgroup systemd 86/96 GiB y swap 1 GiB, sin cambiar los requisitos de memoria del modelo. Preflight fresco exige lock Q54, model stat anchor, hashes/revisiones exactos, Tool-Eval 2.8.0, cero inference servers externos, MemAvailable ≥24 GiB, SwapFree ≥1 GiB, GPU0 <85 °C, cgroup efectivo y espacio libre ≥1 GiB en destino. Guards cada 30 s. Abortar ante inference externo, OOM/max, memoria/swap bajo umbral, GPU ≥85 °C, error inesperado o 90 min; cleanup sólo del servicio Q54.

Los resultados y logs van al directorio Q54 sobre el volumen de evaluación; el GGUF se usa desde HDD extra y no se copia. No matar procesos ajenos ni la GUI; no cambiar ni borrar ASTRA, SOL, Flash-Next productivo, PeritoSoft, perfiles o modelos.

## Continuación

Si seed 43 es válida, no afirmar calidad suficiente: actualizar accionables y preregistrar nueva matriz matched con seeds 43/44/45, baseline/d3/d4, full suite y runtimes seriales; evitar `MK_PREFILL=mk` por el marcador CUDA ilegal repetido. Si vuelve PEG/API, cerrar con evidencia y buscar una corrección concreta antes de más GPU.
