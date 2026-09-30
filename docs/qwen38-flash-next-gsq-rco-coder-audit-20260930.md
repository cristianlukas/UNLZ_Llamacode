# Qwen3.8 Flash-Next GSQ/RCO Coder — revisión para LlamaCode

Fecha: 2026-09-30

Candidato: [`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF), quant `IQ1_M`
Estado: **en evaluación; no agregar al catálogo ni reemplazar un perfil todavía**.

## Qué aporta

Es una variante experimental específica para coding que retiene 256 de los 512
expertos por capa y guarda los expertos retenidos a 3,5 bpw. El modelo card
publica 58,4 GB en total, de los cuales 29,6 GB corresponden al working set
residente; el shard n-gram de 28,8 GB puede permanecer en SSD con `--lazy-mode
on`. La comparación publicada es SWE-bench Verified 75,60 vs. 82,80 en BF16 y
LiveCodeBench v6 86,28 vs. 87,43, ambos a xhigh. Son resultados del publicador,
no del harness local.

GSQ y RCO asignan precisión por tensor bajo un presupuesto; RCO también elige
expertos contra KL en datos de calibración. La idea relevante es la
cuantización no uniforme y el pruning dirigido por capacidad. LlamaCode no
necesita implementar esos algoritmos para usar un GGUF ya preparado.

## Evidencia local existente que se reutiliza

No se repiten estos controles:

| Control ya registrado | Resultado disponible | Para qué sirve en esta revisión |
|---|---|---|
| Swift Qwen3.8-27B Genesis NVFP4, contrato de tools, 64K | 5/5 pasadas con `read_file` seguido de `write_file` | Control de formato/orden de tool calls |
| Genesis, BCB directo, 64K | 1/8, transporte 8/8 | Control local de coding; comparar con el mismo pack, aclarando que no es LC-H1 |
| Genesis, Computer Use prompt-order, 48 estados, 5 pasadas y 3 órdenes | 100% exactitud, validez, seguridad y transporte en cada variante; gate total falló por latencia | El benchmark de decisiones está en techo de calidad; no promete ventaja por prompt |
| Genesis, decode 64K, cinco pasadas | mediana 56,35 tok/s | Referencia de velocidad, sin MTP equivalente para este candidato |
| Qwen3.8 GSQ/RCO 27B y otras variantes Flash-Next | Las auditorías previas ya registran problemas de latencia/infraestructura y ausencia de superioridad local | No repetir esas descargas ni confundirlas con el artefacto Coder de ISTA-DASLab |

Fuentes locales: `artifacts/swift-genesis-evaluation-20260929/`;
`docs/qwen38-flash-next-gsq-rco-audit-20260915.md`;
`docs/qwen38-gsq-rco-dflash2-q2-audit-20260918.md`;
`docs/computer-use-sandwich.md`.

## Compatibilidad y pruebas de esta revisión

La notebook expone 2× RTX 3090 de 24 GB, 123 GiB de RAM y 8 GiB de swap. El
working set informado de 29,6 GB cabe en la VRAM agregada, pero deja margen
para KV, buffers y `mmproj`; hay que validar el reparto real y no asumir que
la afirmación de “una GPU de 32 GB” garantiza la receta dual 3090. El runtime
local inspeccionado es `llama.cpp` LlamaCode 0.3.0-dev, commit `9bd97fe`, con
flags `--lazy-mode`, `--tensor-split`, KV Q8 y soporte multimodal. La carga del
GGUF y la compatibilidad efectiva de esta variante siguen pendientes.

El proyector BF16 de 907,5 MB y el README se descargaron en
`/media/cristian/7CFE1E0FFE1DC1F6/models/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF/`.
La carpeta ocupa 4,3 GB, incluidos 3,37 GiB parciales de los shards. La
transferencia se pausó; la velocidad observada fue muy variable y todavía
quedaban más de 55 GB por bajar. Se conservó la caché parcial de Hugging Face
para reanudar la misma descarga, sin duplicar archivos. No se reporta ningún
resultado local de inferencia del Coder.

Comando para continuar sobre esa misma carpeta:

```bash
hf download ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF \
  --local-dir /media/cristian/7CFE1E0FFE1DC1F6/models/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF \
  --include 'IQ1_M/*.gguf'
```

Después de cargar sin OOM, el orden de evaluación previsto es:

1. Smoke de texto y health/API con contexto 64K, KV K/V `q8_0`, lazy mmap y
   medición de VRAM/RAM por GPU.
2. Reproducir `harness_tool_contract_v1` (5 pasadas) y `BigCodeBench-Hard-8`
   directo con el endpoint local, la misma semilla/sampling y el pack ya
   existente `artifacts/bigcodebench-hard-ubuntu-8.json`.
3. Ejecutar el fixture Computer Use existente (48 estados, control state-first
   y mismo sampling) como prueba de paridad; ese corpus representa decisiones
   sobre texto de UI, no automatización E2E de escritorio.
4. Ejecutar un smoke real de visión con `mmproj` y una imagen local conocida.
   Si los pasos previos pasan, ejecutar HE0 → HE20 → BCB LC-H1; no promover con
   sólo resultados directos o benchmarks del publicador.

## Lectura por subsistema

- **Coding/modelo:** es la oportunidad principal. LiveCodeBench y SWE-bench
  hacen plausible probarlo, pero el SWE publicado ya pierde 7,2 puntos frente
  al BF16 y no se compara directamente con SOL ni con nuestras recetas.
- **Computer Use:** puede evaluarse como decisión de herramientas, pero el
  control Genesis ya marca 100% en el fixture de 48 estados. Sólo sería útil si
  conserva calidad/seguridad y mejora latencia o generaliza a una prueba E2E con
  visión y herramientas reales.
- **Harness:** no hay base para cambiar el HarnessSpec, el orden de prompt ni
  los guardrails. Las métricas del modelo no cambian la autoridad del host, la
  validación de argumentos o las aprobaciones.
- **Ingi Charla:** no aplica. El artefacto es texto/imagen; no incluye ASR, TTS
  ni evaluación acústica. No reemplaza los perfiles de voz ya probados.

## Decisión provisional

No modificar perfiles ni harness sin terminar las pruebas locales. Mantener los
resultados del publicador separados de las mediciones LlamaCode. La evaluación
de carga, coding, Computer Use y visión queda pendiente hasta completar la
descarga; esta limitación de transferencia no es un fallo de calidad del modelo.
