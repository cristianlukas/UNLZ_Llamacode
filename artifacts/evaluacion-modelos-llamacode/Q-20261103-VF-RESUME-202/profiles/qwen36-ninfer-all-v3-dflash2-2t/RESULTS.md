# Q217 — Qwen3.6-35B-A3B NInfer-all v3 DFlash2 K=2

**Resultado:** medición Q173 válida; **gate de velocidad fallido**. No se justifica ladder completo ni Q172 para este perfil tras el criterio preregistrado.

| Métrica | Q217 DFlash2 K=2 | Q190 MTP3 control 8K | Cambio |
|---|---:|---:|---:|
| Prefill | 6466.06 tok/s | 6520.04 tok/s | -0.83% |
| Decode | 238.62 tok/s | 285.76 tok/s | -16.50% |

Repeticiones válidas 3/3 (8192 prompt tokens y 128 tokens generados):

| Repetición | Prefill tok/s | Decode tok/s | TTFT s |
|---:|---:|---:|---:|
| 1 | 6401.72 | 279.12 | 1.2797 |
| 2 | 6535.89 | 215.35 | 1.2534 |
| 3 | 6460.58 | 221.38 | 1.2680 |

El umbral de continuación era prefill ≥6194.04 y decode ≥314.34 tok/s (+10% frente a Q190 a 8K). Prefill pasa; decode no: queda **16.50% por debajo del control** y 75.72 tok/s bajo el umbral. Por preregistro, se cierra sin ladder adicional ni Q172. Esto no concluye calidad general; sólo descarta esta configuración como optimización de velocidad.

**Infraestructura/limpieza:** preflight PASS; ambas RTX 3090 usadas por el mismo PID (13.3/10.7 GiB); ASUS 1636/1636 frames reservados; P2P bidireccional OK; gpu_unlock activo en ambas; MemAvailable mínimo observado 114.2 GiB; sin swap/OOM registrado. Inicio frío 46.533 s. Servicio terminó exit 0, servidor detenido, puerto 18642 libre, ningún inference server ajeno presente.

Q172/calidad: N/D (no ejecutado por gate de velocidad preregistrado). Init caliente: N/D.

Evidencia cruda: `runs/q173-context-8192.json` SHA-256 `07c4280803a4b1d3381c8b9f14c2fab93632802bbe4f948e49ea662ee010ffc1`. Recibo final: `receipts/q217-result.json` SHA-256 `4f0b48d3a04c42af6da47c93f694d30701fe491791644d154f807a3537e8f5ec`. Preregistro: `receipts/preregistration.json` SHA-256 `2c11f532b74b8f261ecb82c33200676a2be75b1f2b4ffbd558c8b6fc428a411c`.
