# Q39 · Resultados

Estado: C39-01 preparación y verificación completadas. C39-02 pendiente de ejecución Windows nativa.
Lock: Q-20261022-VF-ITERATION-39, token 42eaaf29-f2a5-4176-a545-8bb185ad1e42.
Última actualización: 2026-10-22 17:05 UTC.

## C39-01 · conversión CPU y verificación

Resultado: aprobado como preparación técnica. No es una medición de inferencia ni evidencia de superioridad.

- Fuente exacta: GGUF Flash-Next IQ2_XS en /media/cristian/Disco local/Models/FlashNext-IQ2XS-ISTA-Strata-eval-20261012/IQ2_XS/. El shard 1 conserva SHA-256 92cee27ae5bbadcd732416a0f7a7f0acc092399dbbe8f5a5efa707c2ec0a49d7; shard 2 316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113.
- La fuente de conversión tools/convert/qwen4_exp.py coincide con el blob Git 06309a5c8f6d227ee219bf8be8653ae6bbbccb3c del commit oficial fijado 8d509aefc3b27738627ac9c6eeec01e0ada089e4.
- Comando preregistrado ejecutado: python -m tools.convert --model <shard1> --recipe qwen4_exp_gguf --device cpu --rows-per-chunk 65536 --out <HDD>/artifact/qwen4exp.ninfer --ngram-out <SSD>/qwen4exp.ninfer.ngram.
- Entorno aislado en HDD extra: Python 3.12, numpy 2.5.3, torch 2.14.1+cpu, safetensors 0.8.0. torch.version.cuda es None y torch.cuda.is_available() es False.
- Conversión exit code 0, tiempo 452,320846 s, 998 objetos, 2 archivos de modelo NInfer v3, payload 39.224.865.536 B. Artifact ID dc24febd8b34494282caf0e2c6910d8c.
- Volumen externo: ggml_iq4_nl, 320.001.536 filas × 90 B, 7.111.146 bloques, tamaño 29.127.258.112 B, volume ID 5e3d9d27b9a5f9d026d9a1b06628a9a0.
- Verificación aprobada: reader v3 valida entry y continuation; header del n-gram valida geometría y tamaño; el volume ID coincide con la configuración del modelo; el check oficial de reutilización compara 512 filas deterministas contra la tabla del GGUF original y pasa.
- SHA-256 de salida: entry 411c08d2a1223c03a10c6c7b2bfc8e804fc980184d78c33f221514b666461baa; parte qwen4exp.ninfer.part-0001 c73c5535cddc8241557d13d64d7eafa582f50e648ff5bb2445b3a4d8565fea55; volumen n-gram 0478dd2f62a4d02b5cf3ab64d69229bd88dd95366498ad7c72828f95b99135b6; JSON conversión a423f76e6a93c33d52b7df6a85815a049d592c7cb3b03e8882ac80ecb0ca84e4.
- Evidencia de hashes y formato: /media/cristian/HDD extra/Modelos-eval/Q39-NInfer-v0.16.1-FlashNext-IQ2XS/logs/artifact-validation.json. Log de conversión y validación bajo la misma carpeta. HDD extra y Disco local conservaron 79 GB y 61 GB libres.

## Aislamiento y memoria

Ambas operaciones corrieron en unidades system-manager distintas, en /background.slice, fuera de user@1000.service: MemoryHigh 12 GiB, MemoryMax 16 GiB, sin swap, OOMPolicy=kill, KillMode=control-group, TasksMax 256, CPUQuota 200%; los límites efectivos se comprobaron antes del trabajo. La conversión y la validación acabaron Result=success, ExecMainStatus=0. Durante hashing, cerca de 12 GiB de memory.current correspondían principalmente a caché de archivo inactiva; anónimo cerca de 0,24 GiB, oom=0, oom_kill=0, MemAvailable cerca de 108 GiB. Los servicios quedaron inactivos; no se mató ningún proceso ajeno.

No se identificó servidor LlamaCode/NInfer/vLLM/Ollama ni listener de evaluación. nvidia-smi mostró procesos de escritorio/GUI y una app ArtCraft con loopback 47413; no se identificó como servidor de inferencia ni se detuvo. La conversión usa CPU, no CUDA.

## Lectura de contexto y decisión

El artefacto conserva max_position_embeddings=262144 en metadata. El preview NInfer v0.16.1 tiene un límite de ejecución documentado de 32K; la conversión no amplía el límite operativo y no cuenta como test de contexto. No se ejecutó inferencia, por lo que no hay TPS, puntuación de calidad, latencia o estabilidad para recomendar adopción.

## C39-02 · pendiente por condición externa

Probar en Windows nativo el runtime oficial v0.16.1 contra Strata, con el mismo IQ2_XS y prompts/contexto ≤32K del preview, en serie y con seeds preregistrados. Separar prefill/TTFT/decode/E2E, quality holdout y estabilidad. No comparar con cifras publicadas de otra plataforma, no adoptar con una sola corrida y no cambiar perfiles productivos. La sesión actual sigue en Ubuntu 24.04 y no expone powershell.exe, pwsh ni cmd.exe; C39-02 permanece pendiente hasta que Codex tenga acceso a ejecución Windows nativa.

## Fuentes primarias

- Release NInfer v0.16.1 Windows x64: https://github.com/Don-Chad/ninfer-3090/releases/tag/v0.16.1-rtx3090
- Guía oficial de conversión en el commit fijado: https://github.com/Don-Chad/ninfer-3090/blob/8d509aefc3b27738627ac9c6eeec01e0ada089e4/docs/weight-conversion.md
- Guía oficial de instalación PyTorch CPU: https://docs.pytorch.org/get-started/locally/
