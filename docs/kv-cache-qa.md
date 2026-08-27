# QA de KV cache y contexto largo

LlamaCode incluye un fixture de recuperación larga y un probe opt-in para
comparar `q4_0`, `q8_0`, `f16` o un runtime especializado contra el mismo
`llama-server`. El probe no forma parte de `ctest`: necesita un modelo cargado,
puede enviar prompts de 131K y su duración depende del hardware.

## Qué mide

- Recuperación de una passkey única en siete profundidades: 5%, 15%, 25%, 50%,
  75%, 90% y 95%.
- Salida exacta, no sólo una coincidencia parcial.
- Prefill y decode por separado usando los `timings` de `llama-server`.
- Latencia por request, errores HTTP, timeouts y throughput agregado.
- Con `--users N`, N requests concurrentes por profundidad, cada una con una
  passkey y un stream distintos para comprobar aislamiento.

El relleno usa una aproximación de cuatro caracteres por token. Sirve para
comparar variantes con la misma carga, no para afirmar una cantidad exacta de
tokens del tokenizer del modelo.

## Uso

Compilar el candidato Debug y localizar el probe:

```powershell
build.bat Debug NOPAUSE
```

Con un `llama-server` ya levantado:

```powershell
.\build\Debug\qa_kv_cache.exe http://127.0.0.1:8080 `
  --contexts 8192,32768,131072 `
  --depths 0.05,0.15,0.25,0.50,0.75,0.90,0.95 `
  --users 1 `
  --n-predict 32 `
  --timeout-ms 120000 | Tee-Object kv-cache-qa.json
```

Para comprobar concurrencia, repetir con el mismo modelo, contexto y flags,
cambiando sólo `--users`:

```powershell
.\build\Debug\qa_kv_cache.exe http://127.0.0.1:8080 --contexts 32768 --users 4 |
  Tee-Object kv-cache-qa-users4.json
```

Para una comparación válida, detener y volver a levantar el servidor entre
variantes, mantener fijo el modelo, `ctx-size`, batch, ubatch, GPU layers,
flash-attention y número de usuarios, y guardar cada recibo por separado. Un
resultado sólo es candidato si todas las passkeys pasan exactamente y no hay
requests sin timings, timeout u OOM.

## Runtime especializado

Un runtime que necesite sidecars o variables propias puede probarse con el mismo
probe siempre que conserve el endpoint `/v1/chat/completions` y el formato de
timings de llama-server. El probe usa el chat template del modelo y muestreo
determinista para no confundir el razonamiento/formato de salida con un fallo de
recuperación. Para un servidor que sólo exponga `/completion`, hay que adaptar
el probe explícitamente antes de comparar resultados. Los argumentos y el
entorno deben quedar explícitos en el perfil; no se deben promover a default
hasta repetir la prueba en el modelo y hardware objetivo.

La prueba unitaria de `tests/long_context_probe.cpp` garantiza que el fixture es
determinista, que cada passkey aparece una sola vez y que las profundidades se
mantienen ordenadas. La prueba no valida la calidad general del modelo: para
eso hay que combinarla con HumanEval/BCB, tool-calling y una corrida normal del
benchmark de LlamaCode.

## A/B completo con dos runtimes

Para comparar dos configuraciones que requieren reiniciar el servidor —por
ejemplo `q8_0` contra un runtime con sidecars— usar
[`tools/kv_cache_ab.py`](../tools/kv_cache_ab.py). El runner es portable entre
Windows y Linux, arranca y detiene cada `llama-server`, espera `/health`, corre
el mismo probe en ambos lados y guarda los comandos, logs, recibos y deltas
pareados. No descarga modelos ni sidecars.

Si un servidor termina durante el arranque o antes de responder `/health`, el
runner conserva también las últimas líneas de su log dentro del campo `error`
del registro de esa variante, además de `logPath`. Esto permite diagnosticar un
fallo de runtime desde el JSON sin perder la evidencia original.

Copiar y editar
[`assets/benchmarks/kv_cache_ab.example.json`](../assets/benchmarks/kv_cache_ab.example.json)
con las rutas reales. Después:

```powershell
python tools/kv_cache_ab.py `
  --config assets/benchmarks/kv_cache_ab.example.json `
  --probe build/Debug/qa_kv_cache.exe `
  --passes 3 `
  --include-aa `
  --out kv-cache-ab.json
```

En Linux se puede usar `python3` y el binario `qa_kv_cache` correspondiente.
`--include-aa` repite el baseline como control de ruido; si el control resulta
estadísticamente inestable, `validForPromotion` queda en `false`. El proceso
termina con código distinto de cero ante fallos de arranque, timeouts, pérdida
de passkeys, filas no pareadas o resultados que no pasan el control de calidad.

### Windows con WSL2

El runner admite `launcher.kind = "wsl"`: el probe sigue ejecutándose en
Windows y `wsl.exe` inicia cada servidor dentro de la distribución indicada. El
runtime fraQtl debe estar en rutas Linux absolutas; usar como base
[`assets/benchmarks/kv_cache_ab.wsl.example.json`](../assets/benchmarks/kv_cache_ab.wsl.example.json),
reemplazar `/home/your-user` y ejecutar desde PowerShell:

```powershell
python tools/kv_cache_ab.py `
  --config assets/benchmarks/kv_cache_ab.wsl.example.json `
  --probe build/Debug/qa_kv_cache.exe `
  --passes 1 `
  --out kv-cache-ab-wsl.json
```

El runtime publicado por fraQtl es Linux x86_64/CUDA y requiere una GPU de las
arquitecturas que declara el paquete; WSL2 no convierte ese binario en un
runtime Win32 nativo. `FRAQTL_MEMBRANE_EXCLUSIVE=1` debe mantenerse durante la
validación: ante un dispatch no soportado el proceso debe fallar, no continuar
con una ruta de cache que ya no representa la variante candidata.
