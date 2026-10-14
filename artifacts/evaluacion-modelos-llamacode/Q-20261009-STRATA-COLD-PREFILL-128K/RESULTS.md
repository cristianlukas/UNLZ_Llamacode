# Resultados — Q-20261009-STRATA-COLD-PREFILL-128K

- **Estado:** completada, 6/6 corridas técnicamente válidas (3 pares A/B).
- **Objetivo:** medir prefill frío de ~120K y compactación Codex con
  `codex_compaction_cache` apagado/encendido en el mismo perfil ASTRA IQ3_S.
- **Conclusión:** el flag reutilizó de forma repetible alrededor de 120,4K de
  120,5K tokens al compactar; el prefill medido cayó de 33,35 s a 0,448 s en
  promedio. Sin embargo, una de las tres salidas cache-on no recuperó ningún
  valor sembrado y acabó en texto corrupto. La señal de rendimiento es fuerte;
  la fiabilidad de resumen no queda confirmada. Se conserva el default actual
  apagado y no se cambia ningún perfil de producción.

## Perfil y protocolo ejecutados

- **Modelo:** ASTRA calibrado Qwen3.8-Flash-Next IQ3_S; shards SHA-256
  `4c1eb2ceb4915e1192f4f386021897bde56a97f40a0bb78bb86465e0f7d2aca3` y
  `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`.
- **Runtime:** Strata 0.1.41, commit
  `fb58e0dbc8399662c0e47c76578c6e878b14f6cf`, engine SHA-256
  `770ecf303a4c6271654339c639392ecb455de3a999bf5d2e8dbc73c879103602`, CUDA
  12.8.93.
- **Hardware:** 2× GeForce RTX 3090 24 GiB, driver 610.57.04, RAM física 123
  GiB. Expert cache/prefill auto, MTP4, KV int8 con 32768 resident, contexto
  máximo 131072, split auto, PCIe 0.00, una solicitud a la vez.
- **A/B:** mismas rutas, pesos, runtime, contexto, sampling y prompt; el único
  cambio semántico entre configuraciones es
  `codex_compaction_cache=false/true`. Configuración control SHA-256
  `0690c267aa7f9bf32fe9410121cd0057a369422faea0fc6e310de23ea9647ba6`; candidata
  `0d42afb86a7daec14175bbcb33627da9ea4f38b1e4d0b82ff7be9ad811f18727`. Se
  comprobó que son idénticas al retirar el flag; cada corrida tiene además un
  archivo runtime con ruta de log propia y su hash en el recibo.
- **Protocolo:** orden A-B, B-A, A-B; proceso nuevo por corrida. Cada primera
  petición registró las tools y respondió `READY`; la compactación posterior
  envió `tools=[]`, metadatos Codex de la misma sesión/thread y cuatro valores
  de control. `tool_choice=auto` en el primer turno, con instrucción explícita
  de no llamar herramientas; no hubo acciones externas.
- **Cold/warm:** reiniciar el servidor limpió KV y prompt-cache del engine. No
  se vació la page cache del SO; pesos/modelo/expertos no son “cold” en ese
  sentido. El prefill inicial mide prefijo/KV frío, con inicialización del
  modelo informada aparte.
- **Prompt:** renderizado con el tokenizer y la plantilla de Strata 0.1.41,
  6000 entradas, cuatro valores sembrados en comienzo/medio/95%/final. Primer
  turno 120412 tokens; petición de compaction cache-off 120216 y cache-on
  120478. El cache-on vuelve a incluir 262 tokens de esquema de herramienta,
  tal como requiere el feature. Contexto máximo 131072; salida limitada a
  16/512 tokens. `scenario.json` SHA-256
  `aeee353da01f15a6e9e8930353a0b21627c4027e88cb1c9ef69d00fb1e6d24d3`.
- **Sampling/seed:** temp 0.6, top-p 0.95, top-k 20, min-p 0, repeat penalty
  1.0, presence penalty 0, seed 42, thinking desactivado.

## Corridas

Los tiempos de prefill y tok/s vienen de los logs crudos del engine. “API total”
es la latencia completa de la petición de compaction, incluida generación.

| Par/orden | Cache | Prefill inicial: tiempo / tok/s | Compactación: reutilizados / leídos | Prefill compactación | API total | Valores recuperados |
|---|---|---:|---:|---:|---:|---|
| 1-A | Off | 34,127 s / 3528,3 | 0 / 120216 | 33,680 s, 3569,3 tok/s | 34,155 s | 4/4 |
| 1-B | On | 33,552 s / 3588,8 | 120405 / 73 | 0,465 s, 157,0 tok/s | 2,140 s | 4/4 |
| 2-B | On | 33,620 s / 3581,6 | 120405 / 73 | 0,502 s, 145,4 tok/s | 2,069 s | 4/4 |
| 2-A | Off | 33,694 s / 3573,7 | 0 / 120216 | 33,138 s, 3627,7 tok/s | 33,727 s | 4/4 |
| 3-A | Off | 33,891 s / 3552,9 | 0 / 120216 | 33,227 s, 3618,0 tok/s | 33,666 s | 4/4 |
| 3-B | On | 33,776 s / 3565,0 | 120415 / 63 | 0,376 s, 167,3 tok/s | 1,067 s | **0/4** |

## Resumen estadístico (n=3 por brazo)

| Métrica | Cache off: media / mediana (rango) | Cache on: media / mediana (rango) |
|---|---:|---:|
| Prefill inicial 120412 tokens | 33,904 / 33,891 s (33,694–34,127); 3551,6 / 3552,9 tok/s (3528,3–3573,7) | 33,649 / 33,620 s (33,552–33,776); 3578,5 / 3581,6 tok/s (3565,0–3588,8) |
| Tokens leídos al compactar | 120216 / 120216 (fijo) | 69,7 / 73 (63–73); 120408,3 tokens reutilizados en media |
| Tiempo engine leyendo el prompt de compaction | 33,348 / 33,227 s (33,138–33,680); 3605,0 / 3618,0 tok/s | 0,448 / 0,465 s (0,376–0,502); 156,6 / 157,0 tok/s sobre el sufijo pequeño |
| Latencia total API de compaction | 33,849 / 33,727 s (33,666–34,155) | 1,759 / 2,069 s (1,067–2,140) |
| Inicialización del modelo, separada | 46,012 / 44,009 s (42,008–52,018) | 43,342 / 44,007 s (42,009–44,010) |
| Tiempo proceso completo por corrida | 115,740 / 113,507 s (111,421–122,292) | 80,767 / 80,870 s (79,740–81,692) |

Cache-on reutilizó 99,94% del prompt de compactación medido y leyó unas 1726
veces menos tokens que el control. El tiempo de prefill del compaction bajó
98,66% y la latencia total de esa petición bajó 94,80% en promedio. Los tok/s
de prefill del candidato no deben compararse con los del control como una
medida de velocidad equivalente: el candidato midió sólo 63–73 tokens nuevos,
mientras el control reprocesó más de 120K.

La respuesta inicial fue `READY` y terminó normalmente en 6/6. Las seis
compactaciones devolvieron HTTP 200 y `status=completed`, sin timeout, OOM,
fallo CUDA ni error de transporte. El control recuperó los cuatro valores en
3/3 corridas. El candidato los recuperó en 2/3; en 3-B produjo texto corrupto
que terminaba en `Repeterexpression ... p。。` y omitió los cuatro valores. Ese
es un **fallo de calidad válido**, no un fallo de infraestructura ni una
medición para descartar.

## Recursos y decisión

Durante la carga, cada GPU llegó a ~23,8 GiB usados de 24 GiB. RAM del sistema
se mantuvo alrededor de 68–69 GiB usados y ~53–54 GiB disponibles; swap usado
fue ~1,7 MiB. Los seis servidores terminaron por SIGINT con exit code 0; el
puerto 8352 quedó cerrado y ambas GPU volvieron a 0% (GPU0 conserva memoria de
escritorio/Xorg). No se tocó la configuración productiva. Las seis corridas
sumaron 589,522 s de proceso, aproximadamente 9 min 50 s, incluyendo la carga
del modelo de cada una.

**Decisión:** la caché de compactación de Strata demuestra una reducción grande
y repetible del trabajo de prefill en este perfil y esta conversación
sintética, pero la recuperación de hechos falló una vez de tres con el flag
encendido. Mantener `codex_compaction_cache` apagado por defecto; no promoverlo
como cambio general. Antes de recomendarlo para conversaciones reales, medir
más seeds/conversaciones y comprobar resumen fiel, tool-use posterior y
recuperación de hechos con validadores independientes. No extrapolar el
resultado a coding general, contextos de 1M ni otros modelos.

## Huellas y recibos

- Prompt y manifiesto: [`inputs/scenario.json`](inputs/scenario.json),
  [`inputs/prompt-manifest.json`](inputs/prompt-manifest.json).
- Configuraciones base: [`configs/control.json`](configs/control.json),
  [`configs/candidate.json`](configs/candidate.json).
- Scripts: [`prepare_inputs.py`](scripts/prepare_inputs.py),
  [`prompt_utils.py`](scripts/prompt_utils.py),
  [`run_comparison.py`](scripts/run_comparison.py). SHA-256 respectivos:
  `0d0cffe22e9cbe71d41cc1e10ca3e4a169c3de8f2e6ae6f2495fd73e81075f32`,
  `ff511f9d7be30cfa6e3f4441ec58ac616c69a48ec376a5ddaf439619c2e49d09`,
  `05a50807105150293685329e30d9e990643a1d277f35045d4e1f739b4bb1c9ef`.
- Agregado, JSON por corrida, requests/responses, configuración efectiva,
  logs y telemetría GPU: [`receipts/`](receipts/), en especial
  [`comparison.json`](receipts/comparison.json).
- Conf. de sistema: RTX 3090, driver 610.57.04; engine Strata y perfil ASTRA
  permanecen fijados por las configuraciones y hashes listados arriba.
