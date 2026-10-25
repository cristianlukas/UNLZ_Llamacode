# Q134 — revisión de cinco items agregados a IA local

**Estado:** completada; alcance CPU/offline.

## Alcance

Evaluar, en secuencia, las filas 54–58 de `IA local` de Google Sheets y deduplicarlas contra el inbox local (58 entradas). El trabajo comprende contrastar fuentes primarias y resultados del repositorio y una auditoría offline de las trazas Q41 para clasificar lo que realmente registraron sobre tool calls.

## Hipótesis

Las nuevas publicaciones no desbloquean por sí solas una comparación válida de adopción en el equipo 2×RTX 3090 + 128 GiB. Basalt exige Blackwell; el stack de voz propuesto se solapa con Charla; Qwen3.8-27B/NInfer ya tiene medidas de calidad y velocidad; la anécdota de IQ3_S cambia modelo, quant y motor; y la historia de REA/Ghidra no ofrece un fixture ni un oráculo de resultado.

## Método preregistrado

1. Revisar páginas primarias y filas exactas del Sheet.
2. Cruzar NInfer con Q32/Q34/Q129, voz con `README.md` y `docs/voice-streaming.md`, y QFN tool calls con Q41.
3. Auditar sólo archivos TaskFlow ya existentes. Clasificar fallos como formato/parser, semántica/orden, repetición, o sin evidencia suficiente. No inferir una causa si el registro no incluye raw output y resultado asociado.
4. Cerrar cada fuente como accionable, sin prueba aplicable, duplicada/prior ejecutada, o bloqueada por condición concreta.
5. Actualizar Sheets, `data/inbox.json`, `data/actionables.json`, informe Q134 y esta cola.

## Criterios e invariantes

- No descargar, compilar, levantar servidores, inferir, usar GPU ni crear presión artificial.
- No afirmar que Q41 reproduce el post IQ3_S/Basalt.
- No tocar pesos, perfiles, configuración productiva, ASTRA/SOL, ni la interfaz de voz.
- Recomendar pruebas futuras sólo si pueden cambiar una decisión y dejar sus prerequisitos explícitos.

Los hashes preregistrados de los insumos están en `receipts/preregistration.json`.
