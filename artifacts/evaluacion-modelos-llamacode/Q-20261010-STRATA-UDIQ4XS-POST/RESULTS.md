# Resultados — Q-20261010-STRATA-UDIQ4XS-POST

**Estado: auditoría documental completada; UD-IQ4_XS no evaluado localmente ni promovido.** Se identificó el post exacto, sus tres solicitudes, el artefacto oficial de 93,7 GB y una medición posterior publicada por el propio repositorio Strata. No se descargó el modelo ni se usó GPU: el único candidato local no existe, el NVMe está al 95% y su margen nominal sobre el peso ronda 11,5 GB; usar el HDD alteraría la ruta de expertos/SSD que define el resultado.

## Post recuperado

El post de r/Qwen_AI reporta Qwen3.8-Flash-Next Unsloth UD-IQ4_XS con Strata 0.1.41 en RTX 5090 Laptop de 24 GB, Ryzen 9 9955HX3D, 128 GB RAM y Windows 11. El contexto estaba configurado a 32.768, KV INT8, caché híbrida de expertos y MTP; reasoning apagado. Midió tres solicitudes iguales de 40 tokens de prompt y 320 de salida:

| Corrida | Decode tok/s | End-to-end tok/s | Expert-cache hit | Lectura PCIe de expertos |
|---|---:|---:|---:|---:|
| 1 | 46,2 | 38,95 | 80,2% | 12,8% |
| 2 | 52,6 | 51,20 | 84,8% | 9,7% |
| 3 | 51,1 | 49,72 | 83,7% | 10,3% |

El autor aclara que son prompts cortos, con caché caliente en las corridas posteriores. Los 55 GiB asignados eran presupuesto de expertos residentes, no RSS total: no midió el pico total de RAM/VRAM. Las velocidades de decode y end-to-end no son comparables entre sí sin conservar la metodología. El post no contiene coding con verificador, efectos de agente, Computer Usage E2E, visión, audio ni retrieval largo. La comparación con Swift IQ2_XS no es A/B controlado.

## Evidencia externa de Strata, separada del post

El repositorio de Strata publicó después el issue #2097: UD-IQ4_XS en una RTX 3090 con Strata 0.1.43, contexto configurado a 262.144, temperature 0. El ensayo descartó warm-up, hizo tres muestras de chat corto, prompts frescos de 4K/16K/32K y tres sesiones de agente de cinco turnos. Decode mediano en chat corto: 43,0 tok/s (rango 33,4–53,2); sesión agente: 52,6 (41,8–65,5). TTFT mediano 0,56 s en chat y 4,82 s en la sesión; 68,7% de cache hit en follow-ups. Todo el speed suite tardó 295 s. El mantenedor indica que es sólo una prueba de velocidad, que el modelo ya estaba servido (el tiempo de carga no cuenta), y no midió corrección. No es la misma versión, sistema ni protocolo del post 0.1.41; tampoco es una corrida local LlamaCode.

## Evaluación para LlamaCode

- El post es una referencia válida de velocidad breve en el equipo del autor, no evidencia de calidad coding/agente.
- El issue #2097 ofrece una idea de speed suite útil y compatible con el límite temporal (295 s), pero sólo bajo configuración específica y con calidad sin medir. La suite no debe añadirse a la tabla score+tiempo de calidad como si tuviera un score.
- La historia de un dashboard de demostración que fue publicado en vivo no tiene prompts, permisos, historial ni trazas para atribuir el resultado al modelo. No se usa como evidencia de seguridad o autonomía.
- El benchmark anterior de Strata local comparó IQ3_XXS y ASTRA IQ3_S, no IQ4_XS; no hay resultado local que pueda trasladarse a esta cuantización.

## Preflight y decisión

La búsqueda de modelo, shards y cachés no encontró UD-IQ4_XS en `/media/cristian/Disco local/Models`, `/media/cristian/HDD extra` ni `/home/cristian/.cache/huggingface/hub`. Hugging Face declara 93,7 GB y distribuye tres archivos de 10,9 MB, 49,8 GB y 43,8 GB. NVMe: 105.175.375.872 bytes disponibles, partición al 95%; HDD: 352.570.773.504 bytes disponibles; raíz/caché por defecto: 7.749.070.848 bytes libres. Guardar 93,7 GB en el NVMe dejaría poco margen de trabajo/descarga; el HDD sí tiene lugar, pero introduciría un origen de lectura distinto al SSD del post y del perfil de expertos. No descargué ni llené almacenamiento para una prueba sin control comparable.

**Decisión:** conservar la tabla local existente; no agregar un score de calidad para UD-IQ4_XS. No promover el modelo por tres solicitudes de 40+320 tokens. Reconsiderar una prueba local cuando el quant esté ya disponible o haya espacio holgado en SSD, un runtime local compatible y una pregunta de calidad/velocidad cuya suite completa de tres seeds termine en ≤30 minutos por perfil. Si se hace sólo speed screening, fijar por separado el protocolo del issue #2097, incluir la carga si es parte del uso real y etiquetar el resultado como velocidad, no calidad. Este tope excluye los perfiles llama.cpp MTP-on/off, cuyos seis runs individuales ya superaron 30 minutos; no se reutiliza esa comparación como candidata de calidad.

## Continuación local — 2026-10-18

**Estado: screening local parcial; no promovido.** Esta continuación respondió al pedido de ejecutar las pruebas locales. Se conservó el cierre documental original del 13-10 como evidencia histórica; el HDD produce un perfil de I/O diferente y sus cifras no son comparables directamente con el post SSD.

- **Instalación y runtime:** el snapshot UD-IQ4_XS y sus tres shards se verificaron por SHA-256; instalación retenida en `/media/cristian/HDD extra/Models/LlamaCodeEval/Q-20261010-STRATA-UDIQ4XS-POST/`. Strata `v0.1.41`, revisión `fb58e0dbc8399662c0e47c76578c6e878b14f6cf`. El primer arranque agotó readiness a 900 s; al reintentar con 1800 s el servidor quedó listo en 11 min 24 s. Smoke de API aislado: HTTP 200, `READY`, 0,377 s.
- **Speed screen:** RTX 3090 GPU0, HDD rotacional, contexto 32.768, KV INT8, MTP spec 4. Tres respuestas HTTP 200 al mismo prompt sintético de 40 tokens/320 máximos: decode **48,0 / 56,7 / 62,9 tok/s**, mediana **56,7 tok/s**; tiempo total 23,594 s. El primer prompt consumió 7,958 s de prefill y los warm runs reutilizaron 87 tokens de cache. La segunda salida llegó al límite de 320 tokens (`finish_reason=length`). No reproduce la carga del post ni mide calidad.
- **LlamaCode / HumanEval:** HumanEval/0 (`has_close_elements`) pasó la aceptación `code_tests` en el primer intento, 1/1, con un tool call. Como el recibo conserva `response="[turno cancelado por el usuario]"`, se anotó el estado de early-acceptance y se reejecutaron por separado el código exacto y el grader original: tests oficiales OK; compilación Python OK; bordes vacío, un elemento, distancia igual al umbral y distancia menor al umbral OK. Hash del artefacto: `fadd9db3f7ac06c933c7997bd013cfa0c342b20239dc81021745cd04c0455b4c`. La corrida LlamaCode tomó 285,289 s; el resultado cuenta como aceptación del único caso, no como evaluación amplia de calidad.
- **Límite de cobertura:** no se inició HE20, BCB8 ni TaskFlow. Un solo HE0 tardó 285,3 s; a esa velocidad HE20 se proyecta en ~95 min, sin contar otro arranque frío, por encima del corte vigente de 30 min por perfil. CU E2E, visión, audio y retrieval tampoco se probaron; necesitan fixtures/campañas separadas. No se cambia ni recomienda un perfil por este screen.
- **Cierre:** se detuvieron Strata y el daemon aislado de LlamaCode; el puerto privado 18354 y el endpoint 8354 quedaron cerrados. GPU0 quedó libre; no se tocó el proceso de LlamaCode del usuario. Los pesos se conservaron. Sin cambios de código de producto, por lo que no correspondían build ni `tests-linux.sh`.

Recibos: [speed screen](receipts/continuation-20261018/speed-screen.json), [smoke API](receipts/continuation-20261018/smoke-retry.json), [resultado LlamaCode HE0](receipts/continuation-20261018/llamacode-he0.json), [revalidación de HE0](receipts/continuation-20261018/he0-independent-check.json), [preflight](receipts/continuation-20261018/preflight.json) y [setup](receipts/continuation-20261018/setup-check.json).

## Artefactos y fuentes

- [Plan](PLAN.md)
- [Recibo de fuentes](receipts/source-review.json)
- [Preflight local](receipts/local-preflight.json)
- [Post exacto de r/Qwen_AI](https://www.reddit.com/r/Qwen_AI/comments/1x1c7gz/qwen38flashnext_udiq4_xs_94gb_on_rtx_5090_laptop/)
- [Árbol y tamaño del GGUF en Hugging Face](https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF/tree/main/UD-IQ4_XS)
- [Benchmark upstream Strata #2097](https://github.com/Niko1221/Strata/issues/2097)
- [Release notes Strata 0.1.41](https://github.com/Niko1221/Strata/releases/tag/v0.1.41)
