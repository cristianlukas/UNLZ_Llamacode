# Auditoría Agention Precision Qwen3.8-27B — 2026-09-26

> **Actualización:** la prueba local ya se completó. AP queda superior en PPL local frente a UD-Q3_K_XL y ByteShape IQ4_XS, y empata con ByteShape en los smokes de coding y Computer Use. Ver el [informe de medición local](qwen38-agention-ap-local-benchmark-20260926.md); el estado inicial que sigue corresponde a antes de descargar los modelos.

## Decisión

Se agrega el perfil manual
`sys-bench-qwen38-agention-ap-q3kxl-32k` para probar AP-Q3_K_XL con visión,
KV Q8 y la plantilla Qwen3.8 que ya usa LlamaCode. MTP queda apagado para que
la comparación mida el quant, no la aceleración especulativa.

**Clasificación basada sólo en el reporte publicado por quien creó el quant:**

- **SUPERIOR en KLD sobre mixedweb público** frente a UD-Q3_K_XL del mismo
  tamaño: 0,0250 vs. 0,0270 (−7,6%, 5σ reportadas). Un KLD menor significa
  que el quant conserva mejor la distribución de siguientes tokens de BF16.
- **INFERIOR en WikiText-2** frente al mismo control: 0,0359 vs. 0,0337
  (+6,5% de KLD).
- En el texto técnico el reporte indica 0,0380 vs. 0,0421 (−9,9%), pero ese
  corpus es interno y no se distribuye. No cuenta como resultado reproducible.
- **Sin clasificación local** frente a ByteShape, SOL o en calidad de tareas.
  AP-Q3_K_XL ocupa 12,24 GiB según la ficha, cerca del ByteShape IQ4_XS local
  (12,18 GiB), pero los tipos de quant no son iguales y no existe aquí un
  resultado directo AP-vs-ByteShape.

Por eso el perfil lleva SUPERIOR/INFERIOR por dimensión en el nombre, pero
permanece `manualOnly`, `best=false` y no reemplaza ningún perfil activo.

## Qué aporta a cada parte de LlamaCode

| Área | Evaluación |
|---|---|
| Modelos y perfiles | Sí aporta una variante candidata para medir fidelidad con presupuesto de memoria cercano al ByteShape instalado. La ficha del autor recomienda Q8 o F16 para KV; el perfil usa Q8. |
| Harness de coding | KLD no mide reparación de código, tool calling, coste ni éxito del agente. El relato de Pi Harness y la plantilla fija es anecdótico y el comentarista dice que no lo midió. No se copia Pi ni se cambia el harness; hace falta A/B en LC-H1. |
| Ingi-Charla | No mide reconocimiento de voz, WER, latencia STT/TTS ni calidad de audio. No hay motivo para retocar sus perfiles de voz con este resultado. |
| Computer Use con visión | La ficha describe KLD de texto; no prueba comprensión visual, selección de controles ni ejecución. Se debe medir con las mismas imágenes y tareas de Computer Use, incluyendo `computer_use_prompt_order_v1.json` y `computer_use_prompt_order_hard_v1.json`. |
| Plantilla Qwen | La plantilla v22.5 externa declara correcciones de historial, aliases de reasoning y serialización de tools. La plantilla local `qwen38-tools-fixed.jinja` ya cuenta con una validación previa 12/12 en seis prompts deterministas. Sin una A/B actual bajo el mismo binario, no se importa ni se marca superior la externa. |

## Medición publicada y límites

El autor informa que comparó cada quant con Qwen3.8-27B BF16 usando
`llama-perplexity`, 60 fragmentos de 2.048 tokens por corpus y el mismo build
y logits base. Para Q3_K_XL contra UD-Q3_K_XL publica estos KLD:

| Corpus | Agention AP-Q3_K_XL | Unsloth UD-Q3_K_XL | Resultado informado |
|---|---:|---:|---|
| mixedweb-v1 público | 0,0250 | 0,0270 | AP menor; −7,6%, 5σ |
| texto técnico interno | 0,0380 | 0,0421 | AP menor; −9,9%, 8,1σ; no auditable |
| WikiText-2 test | 0,0359 | 0,0337 | AP mayor; +6,5% |

La conclusión del autor es estrecha: fidelidad a BF16, no un leaderboard de
tareas. La propia ficha separa calibración de evaluación y declara no usar el
split test para calibrar. Para nuestra repetición, mixedweb y WikiText test
quedan sólo como evaluación: no se incorporan a imatrix ni a ningún ajuste.
También se omite la columna interna del ranking porque no se puede reconstruir.

El dataset público `mixedweb-v1` contiene 301 documentos y 800.789 caracteres;
MD5 del texto publicado: `51e0045e8cabf37922aa82766a25b7b4`. La ficha indica
que la referencia Qwen BF16 corresponde a revisión `1d4bf0f2` y pesa
54.657.733.888 bytes. La prueba local necesitará esa referencia, el corpus,
los quants AP y de control, y un mismo build de llama.cpp:

```powershell
llama-perplexity -m Qwen3.8-27B-BF16.gguf -f mixedweb-v1.txt `
  --kl-divergence-base base-mixedweb.bin -c 2048 --chunks 60 -ngl 99
llama-perplexity -m Qwen3.8-27B-AP-Q3_K_XL.gguf -f mixedweb-v1.txt `
  --kl-divergence-base base-mixedweb.bin --kl-divergence -c 2048 -ngl 99
llama-perplexity -m Qwen3.8-27B-UD-Q3_K_XL.gguf -f mixedweb-v1.txt `
  --kl-divergence-base base-mixedweb.bin --kl-divergence -c 2048 -ngl 99
```

Registrar KLD medio y error estándar, `Same top p`, `Mean PPL(Q)`, build,
revisión/hash de modelos y corpus. Repetir con WikiText-2 test. El corpus
técnico no se agrega al gate hasta ser público con builder y hash.

## Estado inicial antes de la prueba local

No se ejecutó inferencia AP ni KLD en esta corrida: el AP GGUF y la referencia
BF16 no están instalados, y ya estaba activo el servidor
`llama-server` que carga LFM2.5-VL para otra prueba de visión. No lo reinicié
ni lancé una segunda carga de GPU para evitar contaminar ese benchmark. No se
descargaron los pesos AP (12,24 GiB) ni BF16 (54,7 GB).

La comprobación local realizada fue que la ficha publica los archivos
`Qwen3.8-27B-AP-Q3_K_XL.gguf` y `mmproj-BF16.gguf`, y que el runtime instalado
expone `--kl-divergence` y `--kl-divergence-base`. El perfil queda registrado
como pendiente, no como ganador medido por LlamaCode.

Para la siguiente corrida, separar y etiquetar resultados por eje:

1. KLD frente a BF16 sobre los corpora públicos.
2. Calidad del harness con los mismos prompts abiertos de HE0/HE20/BCB y la
   misma plantilla, reasoning y política de reparación.
3. Computer Use con la misma imagen, resolución, idioma y suite visual.
4. Ingi-Charla en su propio benchmark de WER, latencia y calidad TTS.

No combinar estas puntuaciones en un único “mejor modelo”; una mejora de
fidelidad de texto no implica una mejora en voz o control visual.

## Fuentes

- [Ficha Agention Precision Qwen3.8-27B](https://huggingface.co/agentionai/Qwen3.8-27B-AP-GGUF)
- [Dataset público quant-fidelity-corpora](https://huggingface.co/datasets/agentionai/quant-fidelity-corpora)
- [Qwen Fixed Chat Templates v22.5](https://huggingface.co/froggeric/Qwen-Fixed-Chat-Templates)
- [Integración de Qwen AP con Pi Coding Agent en la ficha del modelo](https://huggingface.co/agentionai/Qwen3.8-27B-AP-GGUF#how-to-use-with-pi)
