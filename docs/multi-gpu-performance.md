# Diagnóstico y rendimiento multi-GPU

LlamaCode conserva el detalle de cada GPU detectada por `nvidia-smi` dentro de
`hardwareSummary.gpus`. Cada entrada incluye VRAM total/libre, bus PCIe,
generación, lanes, temperatura y potencia cuando el driver los informa.

El resumen también incluye:

- `hardwareFingerprint`: identificador estable para no mezclar benchmarks de
  máquinas o topologías distintas.
- `recommendedSplitMode`: recomendación conservadora (`layer` o `tensor`).
- `performanceRecommendation`: modo, KV sugerido, confianza y explicación.
- `p2pAvailable` / `nvlinkAvailable`: señales best-effort de `nvidia-smi topo -m`
  y `nvidia-smi nvlink -s`.
- `topology`: relaciones entre GPU (`NV*`, `PIX`, `PXB`, `PHB`, `SYS`) cuando el
  driver las publica.

## Regla inicial

Con una sola GPU se conserva `layer` como valor seguro. En multi-GPU, si el
enlace mínimo conocido es menor que `PCIe generation × lanes = 16`, se sugiere
`split-mode layer`, porque reduce la comunicación frecuente durante el decode.
Con P2P/NVLink y enlaces más rápidos se permite probar `tensor`; la
recomendación sigue siendo una hipótesis y debe validarse con benchmark. Si el
driver no publica topología, el sistema conserva `layer` como fallback.

La selección de KV es orientativa:

- `q8_0` para equilibrio y contexto largo.
- `f16` para calidad cuando hay memoria suficiente.

El sistema no recomienda drivers P2P modificados ni reemplazos de motherboard.
Esas alternativas son dependientes del equipo y quedan fuera del flujo seguro
de perfiles.

## Pruebas

El parser y las reglas se prueban sin GPU real en `test_hardware_diagnostics`.
La validación de rendimiento real debe comparar, con el mismo modelo y prompt,
`pp/s`, `tg/s`, TTFT, VRAM por GPU, estabilidad y versión de `llama.cpp`.

### Smoke headless

El contrato completo, incluyendo el probe asíncrono y la recomendación, se
prueba sin QML ni modelo con:

```powershell
.\tests\headless_smoke.ps1 -Exe .\build\Debug\LlamaCode.exe
```

El script inicia `--agent-daemon`, invoca `runStartupScan`, espera
`hardwareSummary.hardwareFingerprint`, invoca
`performanceRecommendation("balanced")`, genera candidatos, anota una muestra
realista y valida el ranking. También valida que `splitMode` sea `layer` o
`tensor`. En una máquina sin NVIDIA también debe pasar, usando el fallback CPU.
El script borra el directorio temporal y detiene el daemon al finalizar.

### Matriz declarativa

`performanceMatrixCandidates(target, withVision)` devuelve candidatos seguros
para medir. Cada fila contiene `splitMode`, `kvCache`, `ctxSize`, `mmproj`,
`target`, `id` y `status=pending`. Luego de una medición, el cliente puede
enriquecer la muestra con `annotatePerformanceMatrix(sample, candidate)` y
ordenar varias muestras con `rankPerformanceMatrix(samples, target)`. El score
acepta tanto métricas técnicas (`promptTps`/`generationTps`) como artefactos de
benchmark (`avgTps`, `qualityScore/qualityTotal`, `failed`, `timedOut`). Agrega
`performanceMatrixId`, fingerprint, estado, `performanceScore` y `rank` donde
corresponde. Ninguna fila queda marcada como medida sin haber ejecutado
realmente el servidor.
