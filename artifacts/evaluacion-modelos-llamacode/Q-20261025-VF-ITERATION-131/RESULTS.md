# Q131 — resultado del screen Q4 a 262K y revisión del guard

## Veredicto

**PASS del screen preregistrado.** Qwen3.8 Flash-Next UD-Q4_K_XL con Strata 0.1.41 procesó una solicitud de 258.029 tokens de prompt en contexto 262.144 y recuperó exactamente las 10 claves sintéticas distribuidas entre 5% y 95%. HTTP 200, JSON exacto, `usage.prompt_tokens` dentro de rango, una solicitud y cero retries. No se cambia ningún perfil productivo ni el default de contexto; el resultado se limita a este holdout.

## Rendimiento de esta solicitud

- Prefill: **1.877,7 tok/s**, 137,420 s para 258.029 tokens.
- Decode: **50,3 tok/s**, 6,288 s para 334 tokens.
- Tiempo del request: **143,84 s**.
- Hardware/runtime: **2×RTX 3090**, host de 128 GiB, Strata 0.1.41 / CUDA 12.8, split 18/30, Q4, contexto 262K.
- Pico de VRAM observado: GPU0 22.540 MiB, GPU1 22.764 MiB; ambas llegaron a 100% de utilización durante la corrida.

Son medidas de una única petición larga; no son una comparación estadística con ASTRA/SOL ni con otro motor.

## Detector de presión de memoria

La revisión responde la duda del usuario con los trazos de éxito, los límites sintéticos y una carga real nueva:

- Replay del guard Q131 sobre ASTRA DEFAULT 1M: **707/707 muestras sin falso stop**, incluyendo RSS 51,306 GiB, MemAvailable mínima 58,698 GiB y PSI moderada.
- Replay sobre SOL Q127 dual-3090: **157/157 muestras sin falso stop**.
- Casos CPU sintéticos en memoria: presión PSI severa OR alternada corta en muestra 15; MemAvailable baja corta en muestra 15; OOM corta inmediatamente.
- En Q131 en vivo, el árbol del proceso alcanzó **93,13 GiB RSS** y systemd observó un pico cgroup de **100.530.450.432 bytes (93,61 GiB)**. El host conservó **60,80 GiB** como mínimo disponible. PSI global avg10 máxima fue **8,05% some / 7,54% full**, OOM pasó de 0 a 0 y la guarda no abortó. SwapFree bajó de 4,37 a 3,79 GiB; se conservó sólo como telemetría y no como criterio de corte.
- Tras cleanup quedaron **109,69 GiB disponibles**, puerto 8350 libre, unidad Q131 recogida y ningún proceso/model server Q131. ArtCraft siguió abierto con 207 MiB; no se tocó la GUI.

**Conclusión:** la guarda del worker de evaluación distingue uso alto de presión peligrosa en los escenarios medidos. El resultado confirma que no debe detenerse por RSS/VRAM altos o swap usado si todavía hay headroom y no hay PSI/OOM de corte. La prueba no acredita todas las condiciones del sistema operativo ni identifica la causa de los cierres de Codex.

Hay un hueco conocido distinto: la semántica histórica de Q97/Q100 no acumula la condición OR severa si `some` y `full` alternan entre métricas; Q116 lo detectó. AMD05 y la racha OR compuesta pasan pruebas, pero AMD05 sigue candidate-only y no se integró a producción. Este Q131 runner sí usó la transición OR preregistrada.

## Registro, seguridad y límites

- El replay CPU y fixture de diez claves pasaron antes del preflight. Los pesos Q4 coinciden con hashes previamente verificados, tamaños, mtimes y marcadores de completion; auxiliares, runtime, tokenizer, config y scripts tienen fingerprints en `receipts/`.
- El primer snapshot por heredoc se detectó a sí mismo como proceso; no inició ni detuvo servidores. Se documentó y sustituyó por un helper limpio con hash. El preflight limpio y el preflight inmediatamente anterior al modelo pasaron: dos 3090 visibles, 109 GiB disponibles, PSI/OOM cero y ningún inference server externo.
- Una unidad systemd inocua confirmó timeout de 70 minutos, `KillMode=control-group`, `OOMPolicy=stop`, red privada y memoria/swap infinitos. El modelo corrió en unidad transient sin límites de memoria.
- ASTRA y SOL productivos quedaron intactos. No se promovió Q4 a default y no se afirma causalidad respecto del crash de Codex.

Google Sheets quedó sincronizado y leído de vuelta en `Evaluaciones LlamaCode!A352:J352`, `Accionables!A19:N19` y `Inventario de modelos!A8:R8`; ASTRA de referencia también se actualizó en `Inventario de modelos!A14:R14`. Ver recibos de sincronización. Los detalles, salida exacta y recursos están en `receipts/q131-run-summary.json`, `context262k-attempt-01.json`, `context262k-attempt-01-controller.json` y `logs/context262k-attempt-01.resource-monitor.jsonl`.
