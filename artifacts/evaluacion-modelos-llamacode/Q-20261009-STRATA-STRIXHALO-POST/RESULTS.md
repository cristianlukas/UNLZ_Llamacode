# Auditoría del reporte Strix Halo / Qwen3.8-Flash-Next / Strata

## Resultado y recomendación

La evidencia publicada confirma que Strata puede ejecutar Qwen3.8-Flash-Next UD-IQ4_XS en una laptop Strix Halo (Radeon 8060S/gfx1151, Ryzen AI Max+ 395 y 128 GB de memoria unificada) con decode mediano de 59,2 tok/s a 8K, 57,8 a 32K y 42,0 a 128K. Es un resultado comunitario detallado, pero no valida el comentario de 515 minutos ni un contexto de 1M: el informe mide prompts hasta 131.072 tokens, con 4–6 procesos nuevos por longitud; el contexto de cada corrida era prompt + 512.

La ficha de Qwen declara 262.144 tokens nativos y una extensión hasta 1.000.000 con YaRN. Eso es capacidad anunciada del modelo, no una prueba de recuperación efectiva a 1M en Strix Halo. El informe de Strata tampoco contiene una medición a 262K o 1M.

No hay un A/B local válido: este host tiene Ryzen 9 9950X3D, dos RTX 3090 y un dispositivo AMD de pantalla PCI `1002:13c0`; no se confirmó Ryzen AI Max+ 395 ni Radeon 8060S/gfx1151. Cambian arquitectura, memoria, runtime y configuración. No se emuló Strix Halo sobre las RTX 3090 y no se usó GPU para esta auditoría.

**Decisión:** no cambiar perfiles, HarnessSpec ni contexto recomendado. La publicación sirve como referencia de rendimiento para esa laptop y como señal de compatibilidad de Strata; no establece superioridad frente a SOL, ASTRA o Q4 en LlamaCode. Para comparar, hace falta el mismo equipo o un perfil local medido por separado, con suite y métricas comunes.

## Contraste de las afirmaciones

| Afirmación | Evidencia encontrada | Evaluación |
|---|---|---|
| Comentario: “largest quant”, highs in the 50s, mínimo 35 tok/s durante 515 minutos | El comentario no identifica el quant exacto, tamaño de contexto, MTP, ejecución concurrente con RTX 5070, build ni adjunta el JSON prometido. | **No reproducible / anecdótico.** El informe comunitario aporta datos más completos, pero no identifica que sea la misma sesión. |
| Strix Halo ejecuta Qwen3.8-Flash-Next con Strata | Informe comunitario del 2026-10-09: Unsloth UD-IQ4_XS, Strata v0.1.41, Ryzen AI Max+ 395/Radeon 8060S gfx1151, ROCm 7.14.1, 128 GB LPDDR5X, límite de paquete 70 W. | **Confirmado por un reporte comunitario documentado**, no réplica independiente. |
| Rendimiento sostenido de decode | Medianas 59,2 tok/s a 8.192 tokens de prompt (n=6), 57,8 a 32.768 (n=5) y 42,0 a 131.072 (n=4); rangos 58,5–59,6, 57,1–58,7 y 38,0–44,6. | Describe esa configuración; a 128K se observa caída y dispersión mayor. No es la velocidad atribuible al comentario de 515 minutos. |
| Contexto 1M en Strix Halo | Runs de 8K, 32K y 128K; el flag `--max-context` fue prompt + 512. El modelo admite 262.144 nativos y menciona extensión YaRN a 1M. | **No evaluado a 1M.** No se informa carga, recuperación, calidad ni estabilidad a 1M en Strix Halo. |
| Agentes / recuperación | El informe registra 15/15 needles en un fixture propio de ~83K con tres seeds y 5/5 tareas Go con hidden tests vía opencode. | Evidencia inicial del autor; corpus pequeño y distinto de LlamaCode. No compara perfiles ni generaliza a coding amplio. |

## Configuración del benchmark comunitario

- Modelo: `unsloth/Qwen3.8-Flash-Next-GGUF`, UD-IQ4_XS; sin encoder de visión.
- Strata v0.1.41, commit `fb58e0d`, build para gfx1151; ROCm 7.14.1; pack de expertos y draft MTP incluidos.
- `--spec 5 --spec-min-p 0.5 --mtp-window 8192`; KV int8; greedy; prefill auto 16384; caché de expertos 24.576 (55,43 GiB); todas las corridas fueron procesos nuevos y excluyeron carga del modelo.
- El equipo sostuvo 66–69 W (tope 70 W). El informe atribuye el prefill relativamente bajo al límite de potencia; la latencia de prompt fue 8,5 s/30,7 s/127 s para 8K/32K/128K.
- Con cuatro clientes, throughput agregado de salida incluyendo prompt: 32,7 tok/s secuencial, 28,2 con parallel=2, 27,8 con parallel=4 y 30,6 con `--batch-mtp`; no mezclarlo con decode de una sola secuencia.
- Configuración de caché automática sin presupuesto residente explícito causó OOM global en esa máquina; las cifras publicadas usaron argumentos de caché explícitos.

## Estado local y límites

- Preflight local: Ryzen 9 9950X3D, 2× RTX 3090 de 24 GiB; GPU 0 usaba 1.052 MiB y GPU 1, 108 MiB al consultar. La pantalla AMD `1002:13c0` no se identificó como Strix Halo/gfx1151.
- La evidencia local de contexto de Flash-Next llega a pruebas diferentes: existe un intento de 115.015 tokens interrumpido a 65.536 por cierre de transporte y no tiene score; no debe citarse como recuperación válida. El smoke separado de 262K fue bloqueado antes de cargar por la guarda de swap. Ninguno valida 1M.
- No se descargaron pesos, no se inició inferencia/servidor, no se usó GPU, ni se modificaron perfiles o datos productivos.
- No hay huella local de modelo/perfil/suite para este informe externo. Las fingerprints publicadas pertenecen a otra máquina, cuantización, runtime y suite; se guardan como configuración de referencia, no como fingerprint de LlamaCode.

## Fuentes

- [Hilo y comentario original de r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1wx3g89/strata_takes_the_promise_of_moe_models_just_need/)
- [Informe comunitario Strix Halo de Strata, con runs.json](https://github.com/Niko1221/Strata/blob/main/bench/results/2026-10-09-community-strix-halo-laptop-70w/README.md)
- [Guía oficial de Strata para Strix Halo](https://github.com/Niko1221/Strata/blob/main/docs/STRIX_HALO.md)
- [Ficha oficial Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next)

