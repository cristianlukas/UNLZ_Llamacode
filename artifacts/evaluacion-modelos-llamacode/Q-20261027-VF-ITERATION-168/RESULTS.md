# Q168 · Stop autorizado de PeritoSoft y reanudación de pruebas

**Estado:** no se encontró proceso PeritoSoft/LlamaServer que cerrar; ninguna prueba de modelo quedó habilitada en este executor Linux.

- Se reutilizó el lock Q146, token `2242863e-c78e-4fa9-9649-c1d1541f3919`.
- El escaneo de procesos no devolvió PeritoSoft, llama-server/llama.cpp, Strata, vLLM, Ollama ni SGLang. No había listeners en los puertos evaluados ni contenedores Docker activos. No se envió ninguna señal.
- `powershell.exe` no está disponible aquí, por lo que no se pudo enumerar ni cerrar una instancia Windows nativa de PeritoSoft.
- No hubo build, descarga, GPU ni inferencia. Q167 prohíbe más semillas para el perfil HyperQwen exacto y el PLE FP8 quedó cerrado en Q20/Q22. Los demás gates requieren Windows nativo, principal/policy confiables, un flujo+holdout de Harness², transcripción primaria, cambio reproducible de parser/runtime o evidencia real de presión crítica.
- ASTRA Flash-Next, SOL y los datos/configuración de PeritoSoft permanecen intactos.

**Reanudación:** volver a ejecutar una prueba cuando cambie una de esas condiciones. El detalle verificable está en `receipts/peritosoft-process-scan-and-test-gates.json`.
