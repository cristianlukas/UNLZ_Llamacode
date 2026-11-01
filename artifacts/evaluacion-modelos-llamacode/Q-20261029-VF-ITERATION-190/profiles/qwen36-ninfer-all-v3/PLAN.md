# Q190 — Qwen3.6-35B-A3B · NInfer-all v3 · Q173 → Q172

**Estado (2026-11-01):** evaluación completa. Artefacto oficial verificado, build NInfer-all Linux PASS, preflight PASS, Q173 completo hasta 261888 y arranques cold/warm medidos. Q172 semillas 42/43/44 completadas (28/28 cada una; 73/70/79, media 74/100); el gate de seguridad falló en las tres semillas. No promover como perfil seguro hasta corregir TC-91 y los fallos asociados y repetir Q172. El bloqueo previo de NInfer-3090 v0.4.0 (Windows) y su artefacto truncado quedan separados de esta evaluación.

## Hipótesis y decisión

Medir si el artefacto `groupwise-int` de Qwen3.6-35B-A3B bajo NInfer-all Linux tiene throughput Q173 y calidad Q172 local que puedan justificar conservarlo como perfil alternativo. Los números publicados por el upstream sirven para justificar una prueba, pero no cuentan como resultado local. No transferir el Q172 del GGUF UD-Q4_K_XL, de otro quant, ni del runtime NInfer antiguo.

## Artefactos y runtime fijados

- Pesos exactos: `neroued/Qwen3.6-35B-A3B-NInfer`, `qwen3_6_35b_a3b.ninfer`, v3, **22,790,484,480 bytes**, SHA-256 `3e33297645dc33557751be1a3c407a74ed7c00f34909b5d4e8cfdce91b3dbe84`. El `.ninfer` local de 124,428,288 bytes es un artefacto parcial distinto; no se sobrescribe ni se carga.
- Runtime: `iamwavecut/ninfer-all`, release/tag `2026-11-01.2`, commit `8bde0c064cb6cb7f7f86710ea4a614e7a821dceb`; construir desde ese commit en Linux x64, CUDA Toolkit 12.8.93, CMake Release, Ninja, SM86, targets `ninfer-serve` y `ninfer-calibrate`. No instalar paquetes del sistema. El CUDA 12.8 instalado soporta SM86; la ruta NVFP4 de ese modelo queda excluida porque requiere `sm_120a`.
- Pesos en `/media/cristian/Disco local/Modelos-eval/Qwen3.6-35B-A3B-NInfer-all-20261101/qwen3_6_35b_a3b.ninfer` (D/NVMe); source/build/scratch en `/media/cristian/HDD extra/Modelos-eval/Q190-ninfer-all-qwen36-v3` (HDD). Mantener al menos 10 GB libres en D, 20 GB en HDD y 2 GB en `/`; si cualquier piso no se cumple, parar antes de descargar/compilar/iniciar.
- Runtime y artefacto quedan aislados de LlamaCode, PeritoSoft y el `.ninfer` truncado. No cambiar perfiles productivos.

## Perfil de medición

- Hardware: **2× RTX 3090**, dispositivos `0,1`, NInfer-all `--tensor-parallel`; registrar UUID, topología, worker 3090 HELPER, cuarentena de VRAM ASUS, P2P y `gpu_unlock` en ambas tarjetas. No hacer fallback a una sola GPU.
- Configuración: `--model-id qwen3.6-35b-a3b --devices 0,1 --tensor-parallel --host 127.0.0.1 --port 18493 --max-context 262144 --kv-capacity 262144 --kv-dtype rk4v4 --gdn-state-fp16 --spec mtp --draft-tokens 3 --lm-head-draft --mtp-experts-q4 --prefill-chunk 512 --no-prefix-reuse`; vision desactivada para la cohorte textual. Sampling Q172: temperature 0.6, top-p 0.95, top-k 20, min-p 0, repeat penalty 1, presence penalty 0. Usar argumentos aceptados por esta revisión; registrar cualquier parámetro ignorado o no soportado, sin cambiarlo silenciosamente.
- Q173 primero: contextos de entrada 8,192 (3 repeticiones), 32,768, 65,536, 131,072 y 261,888 tokens (1 repetición cada uno), 128 tokens de salida, serial, sin warmup ni prefix-cache. `max-context` y `kv-capacity` 262,144; el máximo del ladder queda por debajo del límite y no se prueba 512K/523K.
- Promedios: media de repeticiones válidas por nivel y luego media aritmética entre niveles válidos. Publicar puntos, `n`, TTFT, tokens reales, decode, errores e init cold/hot; nunca mezclar con otro runtime/quant.
- Ejecución Q173: usar, en orden lexicográfico y con deduplicación exacta de segmentos, los textos de `bench/fixtures/ttft/text/*.json` del commit NInfer-all fijado. El servidor tokeniza localmente con su tokenizador embebido (`POST /tokenize`, `parse_special=false`, `add_special=false`); se envían prefijos exactos de IDs por `POST /v1/completions`, sin chat template, con `cache_prompt=false`. Cada respuesta debe confirmar el número exacto de tokens de entrada y 128 de salida. Prefill efectivo = tokens reales/TTFT E2E al primer contenido; decode = timing de generación del servidor. No se guarda texto generado en logs.
- Sync por etapas: registrar y leer de vuelta en Sheets el arranque frío, smoke, cada contexto Q173, reinicio caliente y cada semilla Q172 antes de continuar al siguiente hito. Mantener D/E/F sin métricas hasta que su etapa correspondiente sea válida.
- Q172 después del cierre de Q173: Tool-Eval Hard Mode 2.8.0, TC-70..TC-97, seeds 42/43/44 seriales, `variant_seed=20261010`, `max_turns=8`, `trials=1`, `parallel=1`, `no_warmup`, timeout 120 s, `fail_on_safety`. Completar las tres corridas válidas de 28 escenarios; safety gates se informan aparte del score.
- Init: medir proceso→`/health` y `/v1/models`; para cold usar `POSIX_FADV_DONTNEED` solo sobre el `.ninfer` y verificar `mincore` (≤5% residente); hot es reinicio inmediato con page-cache retenida. Nunca descartar globalmente la cache.

## Gates de detención

- Lock Q190 cambia, aparece un inference server ajeno, falta una GPU, se altera P2P/worker/unlock, checksum o tamaño no coincide, el servidor no usa ambas 3090, `MemAvailable` cae por debajo de 32 GiB, almacenamiento bajo los pisos anteriores, OOM/Xid/CUDA/runtime fault, o Q173 no entrega el conteo real de tokens solicitado.
- No detener procesos ajenos; detener sólo el servidor iniciado por este perfil. Antes de cada nueva etapa, sincronizar el Sheet y leer la fila de vuelta.

## Secuencia

1. Revalidar lock, disco, runtime/toolchain, servidor ausente y servicios 3090 HELPER.
2. Revalidar SHA del upstream y descargar el artefacto exacto a D; verificar SHA/tamaño.
3. Compilar el commit fijado con CUDA 12.8/SM86 fuera de `/`; verificar `--help`, dependencias y build receipt.
4. Smoke/startup y Q173 ladder completados hasta 261888. Promedio equiponderado de las cinco medias por contexto: 5155.87 prefill / 230.02 decode tok/s; cold init 46.776 s y warm restart 44.597 s. Sheets y recibos sincronizados.
5. Q172 seeds 42, 43 y 44 ejecutadas en serie con `scripts/run_q172.py`; Sheets se actualizó tras cada semilla y al cerrar el cohorte. `RESULTS.md` y recibos conservan resultados por seed.
6. Decisión: conservar el artefacto como alternativa de evaluación no dominada en throughput/calidad, pero no promoverlo como seguro hasta corregir los fallos de autorización/safety y repetir Q172. La media 74/100 se informa con la salvedad de que la puerta de seguridad pasó 0/3.

## Fuentes primarias revisadas

- Release NInfer-all 2026-11-01.2: https://github.com/iamwavecut/ninfer-all/releases/tag/2026-11-01.2
- Pipeline/tensor parallel y perfiles Linux: https://github.com/iamwavecut/ninfer-all
- Launcher profiles Qwen3.6: https://github.com/iamwavecut/ninfer-all/blob/master/docs/maintainer/launcher-profiles.md
- Model card exacto/hash: https://github.com/Neroued/ninfer/blob/master/model-cards/Qwen3.6-35B-A3B-NInfer/README.md
