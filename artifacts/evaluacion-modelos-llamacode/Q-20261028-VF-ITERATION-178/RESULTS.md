# Q178 — Flash-Next IQ2_XS/NInfer: histórico y medición dual

**Estado:** A05 completó la ladder con ambas RTX 3090. Se conserva la medición histórica Q171/Q173 (NInfer preview v0.16.1, GPU1) como fila independiente. A02 mostró que el preview original no acepta dos GPU; A04 falló antes de readiness con expertos desde disco. A05 usó NInfer-all v3 con expertos residentes en GPU y KV sparse en host: cambia runtime, formato y estrategia de memoria, por lo que no es un A/B que aísle únicamente el número de GPU.

## Tabla comparativa actualizada

Los rates son prefill/decode observados por llama-benchy con 128 tokens exactos de salida. A 8K se reporta mediana de tres corridas; niveles superiores tienen una corrida cada uno. Contexto 256K usa 261.888 tokens reales solicitados (máximo nativo 262.144). 512K fue descartado por instrucción del usuario; 1M no forma parte del perfil NInfer. Los resultados heredados conservan sus fuentes y no se recalcularon.

| Perfil | GPU usada | Contexto; prefill / decode (tok/s) | Calidad y límites | Init proceso inicial / relanzamiento inmediato |
|---|---|---|---|---|
| DeepSeek V4.1 Flash-1017 DSX T16 · Xolotl | 2× RTX 3090 | 8K/32K/64K/128K/256K · P 382/601/584/459/325 · D 30,27/29,14/28,31/26,89/25,34 | Q172 89/100; falló TC-92 | 224,155 / 284,167 s |
| SOL · Flash-Next RCO IQ2_XS · Strata, YaRN×4 | 2× RTX 3090 | 131K/262K/524K/1M · P 3265,5/3163,8/2860,8/2232,9 · D 139,1/133,2/113,1/85,6 | Q172 73/100; falló TC-74/82/92. Q35: recuperación sintética a 1M, 8/8 en tres semillas | 52,115 / 18,088 s |
| **Flash-Next IQ2_XS · NInfer preview, Q171/Q173 (histórico)** | **1× RTX 3090, GPU1** | **Q173 8K/32K/64K/128K/256K · P 1789,4/2062,3/2078,0/2041,6/1983,5 · D 27,72/29,94/28,63/31,87/28,35. Q171 8K: 218,75/31,99** | **Q173 Q172 77/100; falló TC-75/82/84/92. Q171 25/25 comprobaciones sintéticas exactas; no es calidad general** | **≈330 s en Q173; no cold/hot separado** |
| **Flash-Next IQ2_XS · NInfer-all v3, device experts, KV residente 32K (Q178 A05)** | **2× RTX 3090, GPU0+GPU1; pipeline de una etapa por GPU, no TP** | **8K/32K/64K/128K/256K · P 2166,9/2261,1/2209,4/2052,7/1743,6 · D 94,60/92,04/90,48/83,05/76,39** | **Q178 no ejecutó Q172. El 77/100/TC-75/82/84/92 es sólo el resultado histórico Q173 y no se atribuye a este runtime** | **287,783 / 287,917 s; segundo es relanzamiento inmediato, page cache no controlada** |
| TERRA · Qwen3.8-27B AutoRound W4A8, MTP-off | 2× RTX 3090, TP2 | 8K/32K/64K/128K/256K · P 2439/2134/1814/1383/949 · D 55,16/53,83/51,39/47,55/39,62 | Q172 62/100; falló TC-74/84 | 134,516 s / N/D; assert CUDA antes de readiness |
| TERRA · MTP4 | Sin medición válida | N/D | Bloqueado por assert CUDA; no hay Q172 válido para MTP4 | N/D / N/D |
| Ternary Bonsai 2 · PrismML | 2× RTX 3090, split 1:1 | 8K/32K/64K/128K/256K · P 1227/1071/875/608/384 · D 75,84/65,82/55,09/42,52/28,37 | Q172 75/100; falló TC-74/84/92. TTFT 256K: 11m27s | 2,584 / 2,116 s |
| Ternary Bonsai 2 · NInfer-all | 2× RTX 3090, etapas de pipeline | 8K/32K/64K/128K/261.888 · P 2067/1841/1580/1224/857 · D 170,9/167,4/139,4/146,6/162,9 | Q172 del mismo peso en PrismML: 75/100; no es score propio de este motor | ≈4,52 / 6,016 s |
| Gemma 4 12B QAT Q4_0 | 2× RTX 3090, split 1:1 | 8K/32K/64K/128K/256K · P 3825/3517/2890/2105/1376 · D 77,63/74,42/69,80/63,64/54,53 | Q172 66/100; falló TC-85/87/91 | 2,617 / 2,072 s |

## Lectura correcta del resultado NInfer dual

Q173 conserva sus valores originales de una RTX 3090, GPU1, sin fusionarse ni reemplazarse. A02 probó el mismo NInfer preview v0.16.1 con `--devices 0,1`, pero el binario rechazó Flash-Next antes de cargar pesos (`runs on one GPU`). Q178 A05 calificó un camino distinto: los mismos pesos IQ2_XS/RCO convertidos a NInfer v3, runtime NInfer-all Q174, `--devices 0,1`, expertos en GPU y KV int8 residente hasta 32K con el resto sparse en RAM. El PID de inferencia se observó en ambas tarjetas durante la ladder.

En A05, el primer inicio de proceso y el relanzamiento tardaron 287,783 y 287,917 s. Los hashes previos ya habían leído los artefactos; la page cache no fue purgada ni instrumentada. El segundo intento volvió a leer los 36 GiB a una velocidad cercana a 130 MiB/s, así que los encabezados no deben presentarse como una comparación controlada de disco frío contra caliente. La medición de velocidad se hizo después del segundo readiness.

El perfil dual bajó de 2166,9/94,60 a 1743,6/76,39 tok/s de prefill/decode al pasar de 8K a 256K. No se midieron 512K ni 1M. El score Q172 77/100 y sus fallos críticos corresponden a Q173 preview/GPU1; calidad y gates del runtime dual nuevo siguen pendientes, no aprobados por herencia. La alternativa Strata YaRN×4 a 1M continúa separada.

La ejecución terminó sin error: 8K n=3 y 32K–256K n=1, salida exacta de 128 tokens; MemAvailable 112.296.708 KiB; PSI sin presión; cero OOM/Xid; PID propio detenido con exit 0, puerto 18478 libre y cero inference servers residuales.

## Evidencia

- Resultado de ladder, init, hardware y cleanup: `runs/ninfer-device-dual-context-ladder.json`.
- Corridas/eventos: `runs/ninfer-device-dual-8k.json`, `runs/ninfer-device-dual-8k-events.jsonl`, `runs/ninfer-device-dual-contexts.json`, `runs/ninfer-device-dual-contexts-events.jsonl`.
- Configuración preregistrada: `receipts/prereg-amendment-05-device-residency.json`; runner `scripts/run_ninfer_all_device_dual_ladder.py`.
- Histórico Q171/Q173: `../Q-20261028-VF-ITERATION-173/RESULTS.md`; mediciones de inicio previas: `../Q-20261028-VF-ITERATION-176/RESULTS.md`.
