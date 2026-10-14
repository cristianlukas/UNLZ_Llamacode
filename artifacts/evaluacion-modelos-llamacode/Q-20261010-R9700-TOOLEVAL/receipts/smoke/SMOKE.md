# Smoke inicial SOL

- Fecha UTC: 2026-10-12T20:38:55+00:00
- Runner: tool-eval-bench 2.7.0, commit c483eef867d75d9dd04c7d370fe553f96a49d672
- Perfil: SOL Qwen3.8-27B AutoRound INT4; vLLM 0.27.1; TP2 en dos RTX 3090; MTP4; contexto 262144; KV FP8.
- Huella efectiva: see `preflight.json`; semilla 42; T=1, top-p=.95, top-k=20, min-p=0, rep=1, presence=0, max_tokens=16384, thinking=true, reasoning_effort=medium; serial; 8 turns; timeout 600 s.
- Corrida cruda: `sol-seed42.json`; log: `../logs/sol-smoke.log`; informe: `sol-reports/2026/10/2026-10-12T20-36-31.198166Z_0d4a1b12--sol-smoke-v2.7.0-seed42.md`.
- Resultado de smoke (no se suma a la suite): 5/6 puntos, score 83/100. TC-01 parcial (1/2, 88.41 s): eligió `get_weather` correctamente, pero no resumió el resultado en la respuesta final; fallo funcional de calidad con HTTP normal. TC-47 pasó (2/2, 12.39 s), TC-70 pasó (2/2, 1.92 s). Sin errores de infraestructura ni warnings de safety gate. El runner aceptó y reportó todos los parámetros, incluido reasoning effort medium.
- Decisión: el parcial de TC-01 es evidencia de calidad y no rompe transporte ni continuidad; no se descarta ni se fuerza como aprobado. Prosigo con la suite completa de SOL para cuantificar la transferencia, conservando el fallo del smoke aparte.
