# Q39 — Reanudación después del reinicio y preparación NInfer Flash-Next · 2026-10-22

**Lock:** `Q-20261022-VF-ITERATION-39` · token vigente en `WORK_QUEUE.lock`.

## Pregunta y alcance

Preparar la comparación local de Qwen3.8 Flash-Next IQ2_XS con NInfer v0.16.1 contra Strata, sin modificar perfiles productivos, ASTRA, SOL, pesos originales ni PeritoSoft. El host disponible sigue siendo Ubuntu 24.04; por eso esta iteración sólo podrá descargar/verificar artefactos oficiales y convertir el GGUF en CPU. No ejecutar NInfer ni inferencia GPU hasta disponer de ejecución Windows nativa.

La revisión de la fuente primaria encontró una ruta de conversión Python/CPU para el IQ2_XS, con salida esperada de aproximadamente 39,2 GB `.ninfer` y 29,1 GB de volumen n-gram. Se reabre la preparación fuera del checkout, aunque Q38 había diferido conversión al estar en Ubuntu; la ruta convertidora no requiere emular ni compilar el ejecutable Windows. Esto adelanta un prerequisito que permite que una sesión Windows ejecute la comparación, pero no cuenta como medición de velocidad o calidad.

## Material y destino

- Entrada exacta: `/media/cristian/Disco local/Models/FlashNext-IQ2XS-ISTA-Strata-eval-20261012/IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf` y `...00002-of-00002.gguf` (Q38: 39.225.954.592 B + 28.800.138.432 B).
- Fuente de conversión/runtime: release oficial `Don-Chad/ninfer-3090` tag `v0.16.1-rtx3090`, commit completo `8d509aefc3b27738627ac9c6eeec01e0ada089e4`. El ZIP Windows publicado mide 1.190.370.069 B y su SHA-256 `e5f76bef32388dae5c5519e5db8177dfe04e46c311730fa6db347cf45056ab16` coincide con el archivo oficial de checksums; `unzip -t` no detectó errores. El source tarball del commit fijado mide 13.841.491 B, SHA-256 `c94c43cc3dd2d8a5d7d27c13e267496b37ec323fa61ce113a7beac0e1d3e848a`; inventario de 2.866 miembros, 55.948.993 B sin comprimir y ninguna ruta absoluta, `..` ni link inseguro.
- Destinos fuera del repo: runtime/source en `/media/cristian/HDD extra/Modelos-eval/Q39-NInfer-v0.16.1-FlashNext-IQ2XS/`; artefacto NInfer en `.../artifact/qwen4exp.ninfer`; tabla n-gram en `/media/cristian/Disco local/Modelos-eval/Q39-NInfer-v0.16.1-FlashNext-IQ2XS/qwen4exp.ninfer.ngram`. El modelo se lee una vez al cargar; la guía dice que el n-gram se lee durante prefill, por eso va al SSD.
- Presupuesto de salida: aproximadamente 39,2 GB para el contenedor v3 (posiblemente dividido por el máximo de archivo) y 29,1 GB de tabla. Preflight previo: 118 GiB libres en HDD extra y 88 GiB en Disco local; repetir `df` y verificar destinos vacíos inmediatamente antes de escribir. Mantener intactos los dos shards originales.

## Experimento preregistrado C39-01 · preparación y conversión (CPU-only)

1. Confirmar que `WORK_QUEUE.lock` conserva el task id Q39 y el token propio; no reservar ni detener procesos de terceros.
2. Reconfirmar ausencia de inference server, listeners de evaluación y unidades propias activas; registrar OS, RAM/swap y espacio del destino.
3. Descargar desde la release oficial fijada el runtime Windows v0.16.1 y el source archive del mismo tag a una carpeta de trabajo de Q39 en HDD extra; guardar URL/nombres/checksums oficiales y verificar hash externo antes de extraer. No instalar ni ejecutar binarios Windows en Ubuntu.
4. Inspeccionar el convertidor y sus dependencias en el tag, `--help`, licencia y requisitos de metadatos. La guía fijada declara que el GGUF aporta la metadata/tokenizer y que `--device cpu` usa la receta `qwen4_exp_gguf`; no requiere bajar un checkpoint HF para este brazo.
5. Verificar SHA-256 de los GGUF de entrada contra marcadores/manifest disponibles; si no hay hash de origen confiable, registrar los hashes calculados y comprobar metadata/arquitectura y tamaños esperados.
6. Convertir el componente de texto y el volumen n-gram en una invocación con `python3 -m tools.convert --model <primer-shard.gguf> --recipe qwen4_exp_gguf --device cpu --rows-per-chunk 65536 --out <HDD>/artifact/qwen4exp.ninfer --ngram-out <SSD>/qwen4exp.ninfer.ngram`, sin MTP ni visión en este primer brazo. El artefacto esperado es v3; conservar bloques GGML exactamente y no re-quantizar.
7. Ejecutar el convertidor dentro de una unidad efímera de system manager, separada de `user@1000.service`, `background.slice`, `MemoryHigh=12G`, `MemoryMax=16G`, `MemorySwapMax=0`, `OOMPolicy=kill`, `KillMode=control-group`, `TasksMax=256` y `CPUQuota=200%`. Antes de iniciar, leer de vuelta propiedades efectivas; ante fallo, detener y conservar logs/parciales identificados, sin tocar la fuente.
8. Verificar archivos finales, tamaños, hashes, encabezado/container v3, manifest del volumen y relación de pertenencia modelo↔n-gram. No cargar modelo ni usar GPU en esta etapa.

**Criterio de parada:** bloqueo de lock, inference server activo, destino no vacío, espacio insuficiente para salida + 20 GiB de margen, checksum/metadata incompatible, dependencia no reproducible, unidad sin límites efectivos o error de conversión. No borrar artefactos fuente ni outputs ajenos.

## Comparación posterior C39-02 (pendiente; no autorizada por el entorno actual)

Cuando la sesión Codex exponga Windows nativo y el runtime/artefactos v3 sean verificables, registrar un preregistro separado antes de GPU. Comparar con Strata 0.1.41 sobre el mismo IQ2_XS, mismos prompts/contexto ≤32K soportados por el preview, parámetros conservadores y seeds; separar velocidad (prefill, TTFT, decode, E2E), calidad (holdout de coding con grader y control) y estabilidad. No declarar superioridad con una corrida ni cambiar ASTRA/SOL/PeritoSoft. Si el preview no ofrece fixture/calidad emparejable, cerrar sólo el brazo de velocidad como screening y mantener calidad sin resolver.

## Revisión posterior al reinicio

- Host Linux Ubuntu 24.04.5; volúmenes NTFS montados `rw`; sin inference process/listener.
- `systemd-oomd` activo; `user@1000.service` conserva `ManagedOOMMemoryPressure=kill` y límite efectivo 70%; RAM disponible 115.834.028 KiB y swap libre 8.387.924 KiB.
- La sesión previa del journal sólo contiene start/stop de `systemd-oomd`; no aparece otro cierre por OOMD en ese log. Esto no demuestra ausencia de cualquier otra causa de cierre.
- El benchmark model-backed sigue pendiente por ejecución Windows y artifacts compatibles. El aislamiento global de launchers continúa como P0 separado.

## Preflight C39-01, fijado antes de la conversión · 2026-10-22

- Los marcadores `.done` de los dos shards dicen `whole (checked against its own tensor directory)` pero no publican un hash externo. Huellas SHA-256 calculadas antes de convertir: shard 1 `92cee27ae5bbadcd732416a0f7a7f0acc092399dbbe8f5a5efa707c2ec0a49d7`; shard 2 `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`. Mantener ambos archivos fuente intactos.
- El archivo `tools/convert/qwen4_exp.py` coincide con el blob fijado por Git (`06309a5c8f6d227ee219bf8be8653ae6bbbccb3c`). El CLI `python -m tools.convert --help` carga desde el árbol extraído y confirma los flags `--device`, `--rows-per-chunk` y `--ngram-out`.
- Entorno separado de conversión en HDD extra: Python 3.12, `numpy==2.5.3`, `torch==2.14.1+cpu`, `safetensors==0.8.0`. La rueda instalada declara `torch_cuda_build=None` y `torch.cuda.is_available()==False`; no se instala backend CUDA.
- Canary de aislamiento systemd: una unidad de sistema efímera con la misma slice y límites propuestos inició y se detuvo correctamente. Lectura efectiva: `Slice=background.slice`, `ControlGroup=/background.slice/llamacode-q39-cgroup-preflight.service`, `User=1000`, `MemoryHigh=12884901888`, `MemoryMax=17179869184`, `MemorySwapMax=0`, `OOMPolicy=kill`, `KillMode=control-group`, `TasksMax=256`, `CPUQuotaPerSecUSec=2s`. Canary cerrada con `Result=success`; no dejó proceso activo.
- Destinos ausentes antes de escribir. `df -BG`: HDD extra 116 GB disponibles; Disco local 88 GB disponibles. Frente a presupuestos de 39,2 GB y 29,1 GB respectivamente, ambos dejan más de 20 GiB de margen. No hay listeners en los puertos de evaluación comprobados.
- Ejecución sólo después de volver a leer propiedades efectivas de la unidad de conversión; un wrapper espera una señal de liberación creada únicamente tras verificar el cgroup real. Tiempo máximo preregistrado: 2 h; logs y parciales permanecen identificados dentro de la carpeta Q39. Proceso único, CPU-only, dos cores máximos; detener sólo la unidad Q39 si el cgroup, los destinos o el espacio no coinciden.
