# Auditoría: NInfer Qwen3.8-27B NVFP4 — 2026-09-14

## Qué afirma la referencia

El post muestra Qwen3.8-27B NVFP4 servido con NInfer y estima unos 4.500
tokens/s de prefill para un prompt de 90K. Los comentarios indican que MTP3
funciona mejor que MTP4 en algunos usos y que la receta resulta útil para un
harness de coding.

La publicación no identifica en el texto disponible la GPU, la versión exacta
del artefacto ni una medición BCB/HE/tool-use. Por lo tanto, el número de
prefill no puede compararse directamente con nuestros perfiles.

## Pruebas locales previas

NInfer-3090 ya fue compilado y probado sobre nuestras dos RTX 3090 (SM86) con
el artefacto Qwen3.8 histórico compatible:

| Variante local | Prefill | Decode | Calidad |
| --- | ---: | ---: | --- |
| GPU1, MTP3, KV INT8/Q8, 8K | — | 73–75 tok/s | Smoke válido |
| GPU1, MTP3, KV INT8/Q8, 80K | 745,3 tok/s | 50,1 tok/s | Long-context válido |
| GPU1, MTP3, KV INT8/Q8, 120K | 660,7 tok/s | 62,9 tok/s | Long-context válido |
| BCB con thinking 2048 | — | Estable | **3/8** |

La ruta GPU0 produjo corrupción y quedó descartada. La ruta GPU1 es funcional,
pero no alcanza la calidad de SOL. El artefacto actual con DFlash2 tampoco es
consumido por el runtime local porque contiene el objeto
`dflash2/feature_projection`.

## NVFP4 y compatibilidad

Las RTX 3090 reportan compute capability 8.6. La ruta NVFP4/A4 tensor-core de
NInfer está orientada a hardware Blackwell; el runtime NInfer-3090 local no
ofrece una variante NVFP4 validada para SM86. En el árbol de modelos sólo están
los dos artefactos `.ninfer` de Qwen3.8 ya conocidos, no un artefacto NVFP4
nuevo.

Tampoco corresponde inferir una mejora desde el prefill publicado: el prefill
depende mucho de GPU, batch, backend, layout de pesos y si la medición es
interactiva o agregada. Nuestra medición local de contexto largo es la
referencia válida para LlamaCode.

## Comparación con los perfiles principales

| Perfil | Resultado local | Decisión |
| --- | ---: | --- |
| **SOL** | 74 narrativo / 102 código · BCB 8/8 · 262K | **Default** |
| **QWEN35-A3B** | 123,98 tok/s · visión 4/4 · BCB 4/8 | Experimental multimodal |
| **NINFER-QWEN38** | 73–75 a 8K; 50–63 a 80–120K · BCB 3/8 | Experimental, no principal |

NInfer puede ser interesante si aparece una build SM86 mejorada con un artefacto
compatible y BCB superior. La referencia actual no demuestra eso.

## Decisión

- No se descarga NVFP4 ni se cambia el artefacto local.
- No se modifica el perfil `NINFER-QWEN38`.
- No se agrega una variante NVFP4 al dropdown.
- SOL continúa como default.

Referencias locales:

- `docs/ninfer-3090-linux-evaluation-20260908.md`
- `docs/dual-3090-profile-audit-20260908.md`
- `assets/system_profiles.json`
