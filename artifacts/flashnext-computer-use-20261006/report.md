# Flash-Next: Computer Use A/B — 6 oct. 2026

## Resultado

Se compararon ASTRA IQ3_S calibrado (`pcie-frac=0.00`, `spec-min-p=0.70`) y Swift 1.5 IQ3_XXS mediante la misma API Strata, en serie y sobre las mismas dos RTX 3090. Cada perfil recibió 216 peticiones: 24 estados × 3 órdenes de prompt × 3 pasadas, con las mismas semillas y sampling. Los resultados crudos están en [`astra-iq3s-calibrated.json`](astra-iq3s-calibrated.json) y [`swift-iq3xxs.json`](swift-iq3xxs.json); la receta y hashes están en [`manifest.json`](manifest.json).

| Perfil | Orden | Correctas / seguridad | Válidas / transporte | Mediana | P95 |
|---|---|---:|---:|---:|---:|
| ASTRA IQ3_S calibrado | `state-first` | 72/72 · 63/63 | 72/72 · 72/72 | 663.20 ms | 715.29 ms |
| ASTRA IQ3_S calibrado | `question-first` | 72/72 · 63/63 | 72/72 · 72/72 | 650.03 ms | 717.61 ms |
| ASTRA IQ3_S calibrado | `sandwich` | 72/72 · 63/63 | 72/72 · 72/72 | 809.50 ms | 871.19 ms |
| Swift IQ3_XXS | `state-first` | 72/72 · 63/63 | 72/72 · 72/72 | 508.85 ms | 542.14 ms |
| Swift IQ3_XXS | `question-first` | 72/72 · 63/63 | 72/72 · 72/72 | 501.87 ms | 532.63 ms |
| Swift IQ3_XXS | `sandwich` | 72/72 · 63/63 | 72/72 · 72/72 | 615.92 ms | 641.92 ms |

## Lectura correcta

Los dos perfiles empataron en exactitud, validez y seguridad: 100% en las tres órdenes; cada uno tuvo 0 fallos de transporte. En esta tarea de clasificación corta, Swift mostró medianas 22,8–23,9% menores que ASTRA calibrado. No es evidencia de una mejora general de calidad: la exactitud llegó al techo en ambos, la latencia incluye el servicio local y no hubo ejecución de escritorio, capturas, OCR/UIA, recuperación ni tool-calls reales.

La variante `sandwich` falló la compuerta de latencia del runner en ambos perfiles: su mediana fue >5% sobre `state-first` (ASTRA 809,50 vs. 663,20 ms; Swift 615,92 vs. 508,85 ms). No se cambia el prompt ni el harness.

### Recomendación

- Mantener ASTRA IQ3_S calibrado como perfil principal general de Flash-Next: su evidencia LC-H1 repetida sigue favoreciéndolo frente a ASTRA base en primera pasada y mantiene 38/38 final; esta corrida de Computer Use no cambia el ranking de coding.
- Mantener Swift IQ3_XXS como alternativa compacta/rápida para decisiones cortas de Computer Use; empata en este score y responde más rápido aquí, pero no supera a ASTRA en calidad demostrada ni en LC-H1 total.
- No borrar pesos ni promover `sandwich`. Esta prueba no justifica editar el harness ni los defaults de producción.
- No se midió Ingi-Charla: Flash-Next no incorpora ASR/TTS. Hace falta un corpus acústico común, y el modelo de diálogo por sí solo no prueba latencia/WER/audio final.

## Reproducir

```bash
python3 artifacts/strata-v0135-vs-sol-astra-20261002/benchmark_computer_use_thinking_off.py \
  --url http://127.0.0.1:8350/v1/chat/completions \
  --model qwen3.8-flash-next-iq3_s \
  --corpus assets/benchmarks/custom/computer_use_prompt_order_hard_v1.json \
  --passes 3 --seeds 11,42,77 --order-seed 4242 \
  --temperature 0.6 --top-p 0.95 --top-k 20 \
  --out artifacts/flashnext-computer-use-20261006/<perfil>.json
```

La segunda configuración se inició secuencialmente con `strata-swift-iq3_xxs.json` y el nombre de modelo `swift-1.5-iq3_xxs`. Se usó endpoint temporal 8350; el servidor y motor se detuvieron tras las corridas.
