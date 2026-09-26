# Auditoría: NInfer-4090 Windows + Ternary Bonsai 2 27B — 2026-09-26

## Qué afirma el post

Un post de r/LocalLLM presenta un fork Windows de NInfer para **RTX 4090**
(`JGamboa/ninfer-4090-windows`, rama `feat/bonsai-ternary`) con:

- Qwen3.8-27B completo (Q4/Q5 oficiales): ~5.000 tok/s de prefill a 2K con
  prefill int8 (1,8× llama.cpp en la misma placa), 107 tok/s de decode con MTP
  y hasta 289 tok/s con MTP + n-gram en ediciones.
- Ternary Bonsai 2 27B (6,1 GiB): 188 tok/s con MTP y 532 tok/s con MTP +
  n-gram en ediciones.
- KV E8-lattice 4-bit (`rk4v4-e8`), 262K por request, visión y servidor
  OpenAI/Anthropic.

Son cifras del autor, en una 4090, con su eval propio de 45 tareas.

## ¿Corre en nuestra máquina?

**No, el motor del post.** Nuestra máquina tiene 2× RTX 3090 (SM 8.6):

- `CMakeLists.txt` aborta si `CMAKE_CUDA_ARCHITECTURES != 89`.
- En runtime, `startup.cpp` lanza `Qwen3.5 family runtime requires compute
  capability 8.9`.
- Usa `mma.sync ... e4m3` (FP8 de Ada), que no existe en SM86, y fija
  `kTargetSmCount = 128` para dimensionar lanzamientos cooperativos (la 3090 tiene 82).
- Los `.ninfer` del post (`qwen3_8_27b_a8`, `bonsai2_27b_vl_mtp_q4q5`) están
  empaquetados para ese runtime.

Portarlo de vuelta a SM86 implicaría rehacer la ruta FP8, los presupuestos de
CTAs y re-tunear kernels: no es un cambio de flag. No se intentó.

## Qué ideas del post ya tenemos o están en curso

| Idea del post | Estado en LlamaCode |
|---|---|
| N-gram encadenado tras MTP | Ya existe en llama.cpp como `--spec-type draft-mtp,ngram-mod`. `sys-bench-qwen38-udq4-mtp3-ngram` hizo BCB8 8/8 en 524 s a 59,7 tok/s. |
| Prefill int8 (W4A8) | El upstream SM86 `Don-Chad/ninfer-3090` lo activó por defecto el 2026-09-22 (`NINFER_W4A8_PREFILL` para desactivar). Otra sesión evalúa hoy el release 0.6.1; no se duplicó esa prueba. |
| KV E8-lattice 4-bit | Sólo existe en los forks SM89. El NInfer-3090 ofrece `bf16`, `int8` y `rk8v4`. |
| Ternary Bonsai 2 27B | **Probado localmente** vía el fork llama.cpp de PrismML (abajo). |

## Prueba local: Ternary Bonsai 2 27B PQ2_0

### Entorno

- RTX 3090 (GPU1), Windows 11, driver actual. La GPU0 maneja el escritorio.
- Binario: `PrismML-Eng/llama.cpp` release `prism-b10743-adfffbe`,
  `win-cuda-12.4-x64` (CUDA 13.3 crashea en Windows según `KNOWN_ISSUES`).
- Modelo: `prism-ml/Ternary-Bonsai-2-27B-gguf`, `Ternary-Bonsai-2-27B-PQ2_0.gguf`
  (6,70 GiB, 2,13 bpw) + `mmproj-Q8_0` (0,6 GB).
- Se esperó a que no hubiera procesos de inferencia de otras sesiones en las GPU.

### Velocidad (llama-bench, FA, KV q8_0, 3 repeticiones)

| Prueba | tok/s |
|---|---:|
| pp512 | 1.234,1 ± 16,5 |
| pp2048 | 1.233,3 ± 3,1 |
| tg128 | 59,4 ± 0,1 |

Sin especulación: el fork rechaza MTP para estos archivos y acepta
`--spec-type ngram-*` sin especular. El 532 tok/s del post depende de NInfer
SM89 + MTP + n-gram y no es reproducible acá.

VRAM: **12,3 GB** con visión, KV q8_0 y 64K de contexto en una sola placa.

### Smoke funcional (llama-server, reasoning medium)

Aritmética, JSON estricto, tool call (`read_file` con argumentos correctos),
función de código ejecutada contra casos y lectura de una captura de Ajustes:
todo correcto. Con `max_tokens` 1024 una respuesta larga quedó vacía porque el
razonamiento consumió el presupuesto (issue documentado por PrismML: usar
`--predict 16384`).

### Computer Use (`tools/benchmark_computer_use_prompt_order.py`)

Razonamiento off, 24 estados, 3 pasadas, semillas 11/42, 216 requests por corpus.

| Corpus | Variante | Exactitud | Seguridad | Mediana | P95 |
|---|---|---:|---:|---:|---:|
| v1 | state-first | 100% | 100% | 335 ms | 372 ms |
| v1 | question-first | 100% | 100% | 318 ms | 353 ms |
| v1 | sandwich | 100% | 100% | 419 ms | 452 ms |
| hard | state-first | 100% | 100% | 378 ms | 423 ms |
| hard | question-first | 100% | 100% | 350 ms | 402 ms |
| hard | sandwich | 100% | 100% | 445 ms | 486 ms |

Referencia (Qwen3.5-9B productivo, Linux, 7 pasadas): hard question-first
91,67% / seguridad 90,48%, mediana ~134–173 ms. Bonsai no se equivoca en el
corpus difícil pero tarda ~2,6× más por decisión. `promotion_gate=FAIL` se
refiere al gate del sandwich vs state-first por latencia, no al modelo.

### Escalera de agente (LlamaCode headless, LC-H1, target `agent`)

Perfil `sys-bench-bonsai2-27b-pq2-64k`, huella `18c73c66dcdc…`.

| Etapa | Resultado | Tiempo | tok/s | VRAM GPU0/GPU1 |
|---|---:|---:|---:|---:|
| HE0 | 1/1 | 50 s | 24,3 | 10.712 / 1.643 MB |
| HE20 | 20/20 (19 primer intento) | 219 s | 42,6 | 10.727 / 1.744 MB |
| BCB8 | **2/8** (2 primer intento, 2 reparaciones) | 1.361 s | 44,3 | 10.729 / 1.624 MB |

Comparación: los perfiles Qwen3.8 UD-Q4 con MTP hacen BCB8 **8/8 en
366–750 s**; ThinkingCap/KAT/BigBang, 3/8; NInfer-3090 Qwen3.8, 3/8.

## Veredicto

**`[INFERIOR agente / SUPERIOR VRAM]` Ternary Bonsai 2 27B PQ2_0.**

- **Inferior** como agente de código: BCB8 2/8, peor que todo perfil Qwen3.8
  de la tabla y que los FAST (3/8), y ~2,7× más lento para cerrar la suite.
- **Superior** en huella: un 27B con visión en 12,3 GB y una sola 3090. Es la
  opción más barata de VRAM que resuelve Computer Use hard al 100%.
- Uso sugerido: visión / Computer Use o backend de texto de Charla en la
  segunda placa mientras SOL ocupa la otra. No reemplaza SOL ni entra en la
  selección automática (`manualOnly`, `extra`).
- NInfer-4090 del post: **no aplicable** a 2× RTX 3090. Sin perfil.

## Integración

- `EngineCatalog`: entrada `prism-ternary` (repo PrismML, build CUDA desde
  source con `GGML_CUDA_FA_ALL_QUANTS=ON`). El flavor propio evita que un
  binario oficial se use con PQ2_0 (el oficial lo rechaza, o con Q2_0 genera
  basura sin avisar). El prebuilt se registra a mano con flavor `prism-ternary`.
- Perfil `sys-bench-bonsai2-27b-pq2-64k`: una GPU, visión, KV q8_0, 64K,
  `--predict 16384`, sin MTP/ngram.
- Tests: `test_engine_catalog` y
  `SystemProfilesTests::bundle_bonsaiTernaryUsesPrismBinaryAndVision` (resuelve
  al binario PrismML aunque haya uno oficial antes en la lista).

## Fuentes

- [Post en r/LocalLLM](https://www.reddit.com/r/LocalLLM/) (NInfer-4090 Windows, Qwen3.8 + Bonsai)
- [JGamboa/ninfer-4090-windows](https://github.com/JGamboa/ninfer-4090-windows)
- [Don-Chad/ninfer-3090](https://github.com/Don-Chad/ninfer-3090)
- [prism-ml/Ternary-Bonsai-2-27B-gguf](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf)
- [PrismML-Eng/llama.cpp](https://github.com/PrismML-Eng/llama.cpp)
