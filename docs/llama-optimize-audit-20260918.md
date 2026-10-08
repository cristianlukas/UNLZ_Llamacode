# Auditoría `bigattichouse/llama-optimize` — 2026-09-18

## Veredicto

`llama-optimize` es útil como capa de diseño de experimentos para optimizar
recetas de `llama.cpp` en perfiles GGUF. No es un modelo, no mejora los pesos
ni valida por sí solo BCB, HE, tool-use o visión. Por eso no reemplaza a SOL y
no cambia ningún perfil ni default de LlamaCode en esta auditoría.

Repositorio revisado: [`bigattichouse/llama-optimize`](https://github.com/bigattichouse/llama-optimize), commit local
`40ac13f7aee8ec76fd3f4890ed1fa9bd35a1d2b2`, con el submódulo `robust` en
`5ce25ddf112e3e000e263298be9fecd889d71818`.

## Pruebas reproducibles

Se ejecutaron en un checkout temporal para no contaminar el repositorio de
LlamaCode:

| Prueba | Resultado |
|---|---|
| `python3 llama-optimize.py --selftest` | `selftest: all checks passed` |
| `make -C robust all` | Compiló los binarios DOE, incluido `taguchi` |
| `make -C robust test` | Suite C/CLI completa OK; 25/25, 14/14, 21/21, 15/15, 17/17, 6/6, 19/19, 149/149, integración y ejemplos OK. Python bindings y valgrind quedaron omitidos por dependencias ausentes, sin convertirlos en aprobados. |
| `--fingerprint` sobre `Qwen3.8-27B-ByteShape-IQ4_XS-ASCII-P1M.gguf` | Detectó Ryzen 9 9950X3D, 16/32 cores, 126472 MiB RAM, 48 GiB VRAM, 65 capas y contexto nativo 262144 |
| Plan `--use-case agents --levels 3 --min-kv q8_0 --min-context 8192 --max-context 32768 --task 'coding task'` | Generó una matriz L125 de 125 corridas, con MTP on/off, KV F16/Q8, contexto 8/20/32K, microbatch, threads, offload y parámetros especulativos; sin usar GPU |

La matriz estimó aproximadamente 1 h 45 min para ejecutarse completa. La
campaña no se lanzó porque no había un binario Linux completo disponible: el
`llama-server` encontrado requiere `libllama-common.so.0`, que no está presente,
y los demás builds locales son ejecutables Windows. Esto es un bloqueo de
infraestructura, no un fallo de `llama-optimize` ni un resultado de calidad.

## Qué aporta frente a las pruebas anteriores

La utilidad no está en probar otra combinación aislada que ya medimos, sino en
hacer una campaña reproducible y estadísticamente controlada:

- Morris identifica qué knobs mueven PP/TG y cuáles interactúan.
- Taguchi reduce una búsqueda factorial enorme a una matriz balanceada y
  entrega efectos principales.
- `--confirm` comprueba la predicción del óptimo; el modo térmico evita
  comparar una corrida fría con otra ya calentada.
- Registra OOM, señales, timeout y resultados implausibles como datos, evitando
  reintentos infinitos y permitiendo construir una frontera de Pareto
  velocidad/contexto.
- El fingerprint permite invalidar resultados cuando cambian CPU, GPU, modelo,
  build o contexto.

LlamaCode ya tiene `AutoTuner`, fingerprints, matrices de benchmark, BCB/HE y
validación de visión. Por tanto, el optimizador externo complementaría la
exploración de flags crudos de `llama.cpp`, pero la promoción seguiría pasando
por el Harness de LlamaCode.

## Aplicabilidad por perfil

| Perfil | Aplicación | Decisión |
|---|---|---|
| **SOL** (`vLLM` TP2/P2P) | El optimizador sólo genera comandos de `llama.cpp`; no puede optimizar el runtime vLLM de SOL. | Sin cambios. SOL sigue default. |
| **QWEN35-A3B GGUF** | Candidato prioritario para campaña `agents`, con MTP, KV, contexto y concurrencia. | Ejecutar sólo con binario Linux completo y luego repetir BCB/HE/visión. |
| **METEOR / BigBang** | Puede separar el beneficio de MTP, visión, microbatch y 64K. | Experimental; no promover por TG solamente. |
| **Qwen3.5-9B/4B/2B** | Puede optimizar auxiliares, MTP, visión y coste de subagentes. | Útil para una campaña corta por perfil; la calidad debe medirse con Harness. |
| **NINFER `.ninfer`** | No es un GGUF y el optimizador no es su herramienta de tuning. | Sin cambios. |

La regla de calidad usada en el plan fue `--min-kv q8_0`; no se exploraron KV
inferiores para no repetir el riesgo de degradación que ya documentamos. La
optimización tampoco convierte automáticamente una visión funcional ni un
BCB pendiente en una validación.

## Campaña pendiente, sin repetir corridas

Cuando haya un `llama-server` Linux completo con CUDA y sus bibliotecas junto al
binario, la campaña recomendada queda:

1. Ejecutar la matriz L125 sobre QWEN35-A3B GGUF, METEOR y los tres auxiliares,
   separando texto, visión y concurrencia; guardar `results.csv` y fingerprint.
2. Repetir sólo las configuraciones Pareto con `--confirm`, no toda la matriz.
3. Pasar los ganadores por el Harness: HE0, HE20, BCB8, tool-use y visión en
   8K/32K/64K/131K/262K según el techo real.
4. Promover una receta únicamente si mejora el perfil anterior en la métrica
   objetivo sin perder calidad, estabilidad o visión.

Comando base pendiente:

```bash
python3 llama-optimize.py /media/cristian/7CFE1E0FFE1DC1F6/models/<modelo>.gguf \
  --use-case agents --screen --iterate 2 --confirm --full \
  --min-kv q8_0 --ctx-scan --task 'coding task' --run
```

Esta campaña queda anotada para no repetir el plan de 125 corridas ni mezclar
sus resultados con BCB. No se descargó ningún modelo nuevo.
