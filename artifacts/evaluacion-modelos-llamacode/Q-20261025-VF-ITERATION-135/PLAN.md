# Q135 — Revisión secuencial de seis fuentes nuevas

## Alcance

Procesar IA local filas 59–64 del Sheet, en orden, cotejando cada afirmación con fuentes primarias y evidencia local. Registrar fingerprints y duplicados. Las entradas son: JetBrains Qwen3.8/3.6 27B blend; Promethevs DeepSeek V4.1; Gyro Coder Large Flash-Next; comparación NVFP4 Basalt/Infernix/capy/Strata; Strata Huihui v2 UD-IQ4_XS; Strata Qwen3.6-35B-A3B.

## Reglas y gates

- Mantener ASTRA, SOL, Flash-Next productivo y PeritoSoft intactos. Comparar en dual RTX 3090 + 128 GB cuando la carga esté justificada; no usar una GPU como sustituto de la configuración acordada.
- No descargar grandes pesos ni hacer build/inferencia hasta identificar archivos locales, compatibilidad del runtime, fixture/holdout, criterios de aprobación y espacio. GPU y pruebas seriales.
- No repetir Q32/Q34/Q51/Q56/Q97 u otros tests concluidos salvo cambio material que afecte la decisión.
- Un resultado de autor o una sola corrida sólo abre un screen candidato, nunca una afirmación de superioridad general.
- Registrar cada test antes de ejecución; comprobar inference servers y procesos inmediatamente antes de cualquier inferencia.

## Progreso

- Fuentes identificadas en Sheet, IA local!A59:O64.
- Próximo: validar JetBrains blend (ítem 59) contra documentación oficial y comprobar si hay pesos locales + fixture/harness compatible.
- Después: continuar ítems 60–64 en orden, anotando `sin prueba aplicable`, `duplicada`, `accionable` o `bloqueada` con condición concreta.


## Prerregistro Q135-A/B JetBrains Blend (ítem 59)

- **Pregunta:** en el harness local de coding/agentes, ¿Qwen3.8-3.6-27B-blend Q4_K_M mantiene calidad/seguridad del Qwen3.8-27B Q4_K_M y reduce tokens o tiempo E2E en la máquina completa?
- **Candidato exacto:** JetBrains GGUF repo revision `d9c54de0a7d89d34fa4f07c482e35b86a12923f6`, archivo `Qwen3.8-3.6-27B-blend-Q4_K_M.gguf`, 16,810,715,104 bytes, HF `x-linked-etag` `5f54ded85a78f11ad7a1c02d17564a268238ac8afe9b3d94fb0b614e473006a1`; destino aislado `/media/cristian/Disco local/Modelos-eval/Q135-jetbrains-blend/`, fuera de rutas productivas. Licencia Apache-2.0.
- **Control exacto:** Qwen3.8-27B Q4_K_M ya local, 18,973,870,528 bytes, SHA-256 `c600de0300ae8a0eb3a6c0b8b5561b8b96f16bd2c863c2a66c42de29d391a747`.
- **Runtime/harness:** llama.cpp server b11554, commit `966baae76`, ejecutable SHA-256 `fe8a7d6073d3e3a276193fcaec162cbf280d2572ad2016c9100fd924be19c6ed`; plantilla `assets/chat-templates/qwen38-tools-fixed.jinja`, SHA-256 `03c3e852d2c349ce306ed9ecd870c83487bf123918843387b179ead1fcce93af`; Tool-Eval Bench 2.8.0, commit `0a1ba68c7709f429298bc92417a9e003f61de4e3`, Hard Mode TC-70–TC-97 (28 escenarios), seeds 42/43/44, variant-seed 20261010, temperature 0.6, top-p 0.95, top-k 20, min-p 0, repeat penalty 1, reasoning medium, timeout 120 s, max turns 8, parallel 1, contexto 32,768.
- **Hardware/configuración:** las dos RTX 3090 físicas, `CUDA_VISIBLE_DEVICES=0,1`, `--split-mode layer --tensor-split 1,1`; comprobar en el log que ambas reciben capas/pesos. Un solo server y un solo seed activo por vez. MTP/spec desactivado en ambos modelos para aislar el blend; KV K/V q4_0 en ambos.
- **Orden emparejado y contrabalanceado:** seed 42 control→blend; seed 43 blend→control; seed 44 control→blend. Parar el server propio entre cada celda; no dejar servicios residentes.
- **Métricas:** score por semilla, pass/partial/fail, TC-74/84/92 y cualquier fallo crítico, tokens de salida, duración por tarea completada correctamente y tiempo E2E del harness. Informar cada brazo y delta; sin comparar TPS aislado de perfiles históricos.
- **Gate de continuación (screen, no adopción):** las seis corridas deben cerrar válidamente; la media del blend no puede quedar más de 2 puntos bajo el control; no puede añadir una falla en un escenario crítico que el control haya pasado; y debe mejorar ≥15% el tiempo mediano de tareas correctas **o** reducir ≥20% los tokens de salida en esas mismas tareas. Si pasa, sólo habilita un holdout/discriminación mayor; no promueve a producción. Una falla de carga/runtime detiene la campaña sin build ni retry automático.
- **Operación:** antes de descargar y antes de cada carga, confirmar espacio ≥25 GiB en el volumen destino, ausencia de inference servers externos y puerto libre; inspeccionar procesos GPU. No parar GUI. Sin systemd/cgroup MemoryHigh/MemoryMax/MemorySwapMax ni límites de RAM/swap. Monitorizar MemAvailable/PSI/swap/OOM de forma observacional; abortar ante OOM, error CUDA, caída del server o temperatura ≥85 °C. ASTRA, SOL y Flash-Next de producción quedan intactos; no tocar PeritoSoft.
- **Revisiones Q135 sin corrida:** Q60 Promethevs 0.2 está publicado pero exige Windows, 64 GB RAM, GPU NVIDIA 12 GB, ~1.1 TB libre en NVMe, descarga 475 GiB y ~4 h de store build; host actual Linux y sólo 59+26 GB libres en los volúmenes de modelos: bloqueado por condición concreta, no descargar. Q61 Gyro-Coder-L es para tarjeta 32 GB, ocupa 27.54 GiB de VRAM y 78.2 GiB en disco; card dice que Strata está pendiente y stock llama.cpp no carga ese formato; espacio insuficiente con tabla N-gram. Q62 Basalt/NVFP4 requiere Blackwell sm_120/CUDA 13; RTX 3090 es sm_86: sin prueba aplicable en este equipo. Q63 Huihui v2 87.25 GB más 26.82 GB de PLE no entra en 59 GB de Disco local ni 26 GB de HDD extra; el benchmark publicado usa RTX 5060 Ti/Strata 0.1.47 y no se debe extrapolar; el QFN Unsloth local Q26 es otro artefacto, no duplicado. Q64 Strata soporta Qwen3.6-35B-A3B, pero la ruta `qwen35` documentada usa una GPU y el issue #3294 sigue abierto para layer-split; no correr en una sola 3090 como sustituto del dual-GPU solicitado.

## Enmienda preregistrada 01 — intento 02 con runner corregido

- El intento `attempt-01` comenzó el 2026-10-25T15:17:12Z y se detuvo antes de cualquier llamada al benchmark: por orden del código, `llama-server` sí llegó a iniciar el Qwen3.8 base y su log confirma `model loaded` y `listening` en 18104; el JSON de invocación falló inmediatamente después al serializar un `PosixPath`. El proceso propio (PID 1087440) se terminó con SIGTERM y se verificó cero listener en 18104 y cero llama-server; no se enviaron prompts ni se ejecutó ningún escenario Tool-Eval. La tabla nvidia-smi mostró el PID con asignaciones de ~9,8 y ~10,2 GiB, consistente con el split dual, aunque el log no dejó un desglose de capas por dispositivo. Receipts `receipts/run-failure.json`, `receipts/attempt05-runner-serialization-failure-and-cleanup.json` y `logs/seed-42-control-llama-server.log`.
- Causa técnica: el runner había arrancado el proceso antes de escribir `server-invocation.json`, y la excepción ocurrió antes de entrar al `try/finally`; por eso el servidor quedó vivo. La enmienda cambia el orden de registro/cleanup y convierte las rutas `Path` al serializar. Cada intento ahora escribe en un subdirectorio único `attempts/attempt-NN/`; no pisa la evidencia de `attempt-01` y no reanuda resultados a medias. En una excepción, el propio runner termina exclusivamente el grupo de procesos creado por esa celda.
- Alcance científico sin cambios: mismos modelos, hashes, dos RTX 3090, split, plantilla, 28 escenarios, semillas/orden, métrica y gates. `attempt-02` puede continuar porque el primer error fue del arnés antes de una evaluación, no fallo de carga/runtime del candidato; no se construye ni descarga nada de nuevo. El servidor ya está apagado y el gate externo se repite inmediatamente antes de iniciar.
