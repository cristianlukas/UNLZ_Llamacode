# Resultados — Q-20261010-UNSLOTH-MTP-AB

**Cierre:** screening detenido según el corte de interés indicado por el usuario: no considerar perfiles cuyas corridas Hard Mode individuales superen 30 minutos. No se modificó producción.

## Configuración

- Modelo base: Unsloth Qwen3.8-Flash-Next UD-Q4_K_XL, revisión 38bb39ee97821de2c9009abb7e93950eec396e66, cuatro shards locales; hashes en receipts/base-model-hashes.json.
- Candidato MTP: sidecar autocontenido Q8_0, revisión efc50b7c3195a10eebd8d3e32f83b27b2aeb239d, SHA-256 58a47d6a216307e9b97172d5bfdc3436a8994b632f5e436b9bb6edf8951da8d1.
- Runtime: llama.cpp 836d57176dc699a726c55418e4f96b8ca628e1bf, binario SHA-256 ab7828696af2694981037b7114d834d310c1c5f24b39ab24267898748334cbb4; dos RTX 3090, split por capas 1:1, contexto 32768, KV Q8_0, un slot. A MTP-on se añadieron sólo el sidecar y draft MTP con n-max 3.
- HarnessSpec: cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef. Fingerprint LCH: MTP-on 69aacf099a61a10b4370ec10d0fec4d7fa83c93135b6cf57ada8302b664d32b8; MTP-off 7f84727070a2fb93d008a42c90391f3904d800f7d7c2e67f173813ab0435ff89.
- Hard Mode: tool-eval-bench 2.8.0, commit 0a1ba68c7709f429298bc92417a9e003f61de4e3, 28 escenarios TC-70…TC-97, variant seed 20261010; seeds 42/43/44, serial, temperatura 0,6, top-p 0,95, top-k 20, thinking medium.

## Velocidad de generación

Tres pares con el mismo prompt fijado de 23.598 tokens de entrada y 256 de salida. La prueba corta mide generación y no representa la duración de una tarea Hard Mode completa.

| Brazo | Seed 42 | Seed 43 | Seed 44 | Media |
|---|---:|---:|---:|---:|
| MTP-off | 21,20 tok/s decode; 215,02 s | 21,26; 214,98 s | 21,18; 215,10 s | 21,22 tok/s; 215,03 s |
| MTP-on | 30,29 tok/s decode; 213,30 s | 30,86; 212,48 s | 31,25; 212,71 s | 30,80 tok/s; 212,83 s |

MTP-on aumentó decode 45,18%, mantuvo prefill prácticamente igual (115,38 vs 116,25 tok/s), redujo el tiempo de la solicitud 1,02% y aceptó 553 de 629 tokens draft (87,92%).

## Calidad de tool-use

| Brazo | Seed 42 | Seed 43 | Seed 44 | Media y tiempo total |
|---|---:|---:|---:|---:|
| MTP-on | 78,57 — 41:19,09 | 85,71 — 37:53,83 | 82,14 — 40:13,82 | 82,14 — 1:59:26,74 |
| MTP-off | 83,93 — 44:33,26 | 75,00 — 44:32,79 | 82,14 — 46:20,71 | 80,36 — 2:15:26,76 |

Las seis corridas completas excedieron el límite de 30 minutos por semilla. MTP-on ganó 1,79 puntos de media y tardó 11,8% menos que MTP-off, pero ambos quedan fuera de los perfiles de interés definidos por el usuario. TC-89 y TC-92 fallaron en las tres semillas de ambos brazos; TC-97 fue parcial en las seis corridas. La comparación histórica Q4/Strata promedió 77,38 y registró 27:28 para las tres semillas juntas; sus tiempos individuales no están desglosados en el recibo histórico. Cambian runtime y perfil completo, así que no se atribuye esa diferencia sólo al modelo.

## Coding/agentes

- MTP-on: HE0 válido 1/1; HE20 válido 20/20 en 3660,385 s (61:00,4), sin reparaciones. Un primer BCB8 quedó inválido por transporte; el reintento fue válido, 3/8 inicial y 3/8 final tras tres reparaciones, en 4969,087 s (1:22:49,1).
- MTP-off: HE0 válido 1/1; HE20 válido 20/20 en 4313,804 s (71:53,8), sin reparaciones. BCB8 se canceló por el corte de 30 minutos tras generar 2/8 tareas; quedó incompleto y no tiene score válido. Los archivos parciales y eventos se conservaron en runtime y receipts/lch.
- TaskFlow ULTRA no se corrió: las corridas Hard Mode ya excedían el límite de duración elegido.

## Decisión y límites

No se promueve MTP-on ni MTP-off a perfil de interés ni se cambia HarnessSpec o producción. El aumento de decode de la solicitud corta no compensa, para este uso, que las corridas Hard Mode duren más de media hora cada una. HE20 y BCB8 se informan como evidencia observada, no como recomendación de uso. No se evaluaron GUI E2E, visión, audio ni contexto largo.

Recibos principales: receipts/tool-eval/mtp-ab-summary.json; receipts/speed-prompt-manifest.json; receipts/sidecar-manifest.json; receipts/lch/mtp-on-he-20261013-timeout10800.json; receipts/lch/mtp-on-bcb8-retry-20261013.json; receipts/lch/mtp-off-he-20261013-timeout10800.json y su archivo .events.jsonl; runtime/lch/xdg-data/LlamaCode/LlamaCode/benchmark-runs/BigCodeBench-Hard_8_tems__20261013_130818/ conserva la evaluación cancelada.
