# BigBang-v1 Q4_K_M

Perfil experimental para comparar `endless-frontier/BigBang-v1` contra los
perfiles KAT-Coder existentes. Usa el GGUF Q4_K_M de bartowski y el projector
bf16 publicado en el mismo repositorio.

## Variantes

- baseline: 131k, KV q8, sampling conservador;
- throughput: 131k, batch 8192 / ubatch 2048;
- contexto: 196k, KV q4;
- receta del post: `temp 0.70`, `top-p 0.08`.

La comparación debe ejecutarse con la misma suite, seed, contexto efectivo y
cantidad de repeticiones que KAT-Coder. El repositorio consultado no contiene un
draft MTP separado ni declara MTP autocontenido; por eso el perfil no activa
speculative decoding todavía.
