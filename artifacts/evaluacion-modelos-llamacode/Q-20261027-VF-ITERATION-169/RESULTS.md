# Q169 — Revalidar el gate IQ4_XS y buscar pruebas ejecutables

Fecha: 2026-10-27. Se reutilizó el lock paraguas Q146 (2242863e-c78e-4fa9-9649-c1d1541f3919). Fuente: VF-20261019-01, material #14, r/LocalLLM Ycr6z6binI.

## Resultado

No se inició inferencia ni benchmark. El ejecutable Strata disponible devolvió strata 0.1.41; el ajuste STRATA_ROUTE_TAIL_SKIP descrito por la fuente requiere Strata 0.1.42 o posterior. Una búsqueda de los archivos GGUF/safetensors *IQ4*XS* en /media/cristian/HDD extra/Models/LlamaCodeEval y /home/cristian/.cache no encontró pesos exactos. Esta búsqueda sólo cubrió esas rutas. El GGUF IQ4_XS usado en la evaluación histórica ya no está disponible allí; no se sustituyó por ASTRA IQ2_XS, porque eso no probaría la afirmación de la fuente.

El recheck Linux no encontró procesos de PeritoSoft ni servidores llama/Strata/vLLM/Ollama/SGLang, y no encontró listeners de inferencia. No se envió ninguna señal. OpenRGB, CUPS, DNS y artcraft-launch no son servidores de inferencia identificados y quedaron intactos. La enumeración de Windows nativo sigue fuera de este executor (powershell.exe no disponible, como quedó registrado en Q168).

## Decisión y reanudación

La fuente #14 sigue sin una prueba nueva habilitada. El HE20 histórico 20/20 y los dos timeouts de BCB8, más ADV/TaskFlow incompletos, siguen siendo el resultado válido de la corrida anterior; no se presentan como una repetición de hoy. No se cambia el inventario ni se agrega una fila de Resultados sin una medición nueva.

Reabrir este A/B sólo si se decide volver a conservar/restaurar el GGUF exacto UD-IQ4_XS y actualizar el runtime a Strata >=0.1.42. Antes de usar GPU, arreglar el fixture corto de coding y preregistrar un A/B intercalado STRATA_ROUTE_TAIL_SKIP=7 vs 0, con misma cuantización, endpoint, prompts y sampling; medir aceptación funcional, seguridad, E2E y fallos. Hasta entonces, mantener la fila del Sheet como bloqueada y no descargar el modelo.

Q168 ya documenta que los demás ensayos de inferencia pendientes en este executor están condicionados por Windows nativo, principal/policy autenticados, workflow+holdout de Harness², fuente primaria de transcripción, defecto parser/runtime reproducible de HyperQwen o traza real de presión crítica para Q119. No se encontró un test adicional que pueda ejecutarse ahora sin saltarse esos gates.

Evidencia: receipts/source-14-revalidation.json, receipts/google-sheet-readback.json, receipts/prechange-inbox-source-14.json; lectura/escritura de Evaluaciones LlamaCode!C67:J67.
