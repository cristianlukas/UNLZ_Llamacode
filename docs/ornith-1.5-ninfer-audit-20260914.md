# Auditoría: Ornith 1.5 35B-A3B con NInfer — 2026-09-14

## Resumen

Ornith 1.5 35B-A3B es un MoE multimodal con aproximadamente 3B de parámetros
activos, visión y un cabezal MTP. La referencia promete más calidad agéntica
que otros modelos A3B y una velocidad muy alta con NInfer, pero esas cifras
corresponden a RTX 5090/SM120 y no son reproducibles en nuestras RTX 3090/SM86.

El repositorio de la receta declara explícitamente que NInfer apunta a RTX 5090
(`sm_120a`). También indica que el artefacto Ornith necesita alrededor de 110 GB
para la conversión y que el servidor se ejecuta en una 5090. El artefacto
publicado encontrado pesa aproximadamente 22,78 GB y contiene pesos
cuantizados, visión, DFlash y un cabezal MTP entrenado, pero el formato no
implica compatibilidad con SM86.

## Qué se pudo comprobar localmente

| Prueba | Resultado |
| --- | --- |
| Artefacto Ornith `.ninfer` en `/media/cristian/7CFE1E0FFE1DC1F6/models` | No encontrado |
| Artefacto GGUF Ornith local | No encontrado |
| Runtime NInfer SM86 funcional | No disponible |
| RTX 3090 local | SM86; no coincide con el objetivo SM120 de la receta |
| Resultados Ornith históricos encontrados | Vulkan/Radeon 8060S y otras máquinas; no son una medición local de LlamaCode |
| Descarga nueva | No realizada: la partición de modelos sólo tiene ~22 GB libres |

En los artefactos históricos del directorio de benchmarks aparece Ornith 1.5
Q4_K_M con unos 77 tok/s de decode en una Radeon AI MAX+ 395, pero esa medición
es de otro equipo, otro backend y otra memoria. No incluye BCB ni tool-use de
LlamaCode. También aparecen pruebas MTP con aceptación variable; no son una
validación del runtime NInfer en nuestra máquina.

## Comparación con nuestros perfiles

| Perfil | Evidencia local | Estado |
| --- | --- | --- |
| **SOL** | 74 tok/s narrativo / 102 código, BCB 8/8, tool-use válido, 262K | **Default** |
| **QWEN35-A3B** | 123,98 tok/s en BCB, 262K, visión 4/4, BCB 4/8 | Experimental multimodal |
| **CyberTiel 35B-A3B** | ~183 tok/s código, ~219 JSON, visión y 262K; HE/BCB pendientes | Experimental rápido |
| **Ornith 1.5 NInfer** | 415–429 tok/s publicados a través de router en 5090 | No reproducible en RTX 3090 |

Ornith podría ser un candidato fuerte para una máquina Blackwell, pero no hay
base para afirmar que supere a SOL o QWEN35-A3B en nuestro hardware. Su ventaja
publicada es principalmente de runtime/hardware y throughput, no una medición
apareada contra nuestro BCB.

## Decisión

- No se descarga Ornith mientras la ruta NInfer no tenga soporte SM86 y no haya
  espacio suficiente en la carpeta autorizada de modelos.
- No se agrega al dropdown ni se reemplaza SOL.
- No se reutiliza el perfil `NINFER-QWEN38`: es otro modelo y el runtime
  histórico de 3090 ya mostró limitaciones/corrupción.
- Si aparece un GGUF Ornith Q4/Q5 compatible con llama.cpp, sería el camino
  correcto para una prueba futura: carga, 32K/131K/262K, visión, MTP,
  HE0/HE20, tool-use y BCB bajo el mismo harness.

## Referencias

- Artefacto NInfer de Ornith 1.5 35B-A3B: `knoopx/Ornith-1.5-35B-A3B-NInfer`.
- Receta y limitaciones de NInfer: `j842/ninfer-qwen-uncensored`.
- Benchmarks locales históricos: `Models/llamacpp/llama.cpp-adaptive/bench/results-ornith-*.jsonl`.
- Perfiles comparables: `docs/cybertiel-35b-a3b-audit-20260914.md` y
  `docs/dual-3090-profile-audit-20260908.md`.
