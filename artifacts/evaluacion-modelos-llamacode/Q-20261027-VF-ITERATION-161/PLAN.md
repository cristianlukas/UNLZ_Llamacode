# Q161 — Gyro-Coder-L v1.1 con presupuesto explícito de razonamiento

**Estado:** preregistrado; screen BCB-Hard-8 pendiente.

## Pregunta

¿El perfil Gyro-Coder-L TQ3_0 v1.1 entrega código utilizable en el screen de 8 tareas cuando el request incluye `reasoning_budget_tokens=2048`? Q152 corrió el mismo modelo/fixture/seed, pero `arm=swift` omitió ese campo: su metadata decía 2048 aunque la solicitud no lo mandaba. Seis casos consumieron los 6144 tokens en `reasoning_content` y no devolvieron contenido final. Q161 cambia únicamente ese campo del request.

## Prerregistro

- Candidato: `agentionai/Qwen3.8-Flash-Next-Gyro-Coder-GGUF`, revision `87d31357f4cfeb8555cf32fc63a707c5fa10ae7a`, GGUF `Qwen3.8-Flash-Next-Gyro-Coder-L-TQ3_0-v1.1.gguf`, SHA-256 `377d5aa5b473a89b4d0d0c9fbd54fd8fcc46da19c16fc881860577189c1403df`, 83,975,624,672 bytes.
- Runtime: Agention llama.cpp GitLab commit `9aa51ce4fdd3435a91531ffe16a17414ccc6dc6f`, binario Release CUDA SM86 fijado en Q160; dual RTX 3090, capas en GPU, split `1,1`, `--fit on`, Flash Attention y reasoning habilitado.
- Harness: fixture `artifacts/bigcodebench-hard-ubuntu-8.json`, misma revisión/hash y grader aislado/seccomp de Q89/Q152; seed 4242; serial; contexto 8192; máximo 6144 tokens; sampling `temperature=0.6`, `top_p=0.95`, `top_k=20`, `min_p=0`, repetition penalty 1.0, penalties 0; template thinking habilitado.
- Única diferencia contra Q152: el request HTTP contiene explícitamente `reasoning_budget_tokens: 2048`. Un supervisor Q161 separado usa loopback puerto 18383 y limpia solo los grupos de procesos que inicia.
- Validez de ejecución: 8/8 respuestas transportadas, 0 errores del sandbox, 0 `no_final_content`, ambas 3090 propiedad del proceso de prueba y limpieza confirmada. Si algún gate de ejecución falla, no se interpreta como calidad.
- Screen útil: al menos 4/8 casos aprobados para justificar un experimento matched-control posterior. Por debajo de 4/8, no-go de este perfil y no se atribuye inferioridad general a la familia/modelo. El control ASTRA Q97 (2/8) es histórico y usa otro runtime; esta corrida no permite afirmar superioridad frente a ASTRA/SOL.
- No promover ni conectar el candidato a PeritoSoft. Sin límites artificiales de RAM/swap; se detiene solo por fallo del servidor/runner, OOM confirmado, PSI severa sostenida, cleanup inseguro o interrupción del usuario.

## Evidencia y decisión

Q152 observó 0/8; seis respuestas no llegaron a contenido final con el límite de salida. Q161 prueba si el presupuesto acotado corrige esa condición. Solo un screen ≥4/8 permite preregistrar una comparación pareada de tres semillas y seguridad; no habilita adopción por sí solo.


## Final result

Completed 2026-10-27T04:06:03Z: 1/8 passed, below the preregistered ≥4/8 gate. The budget field fixed truncated final responses but did not produce adequate functional quality. No matched-control follow-up or three-seed campaign is justified. Candidate retirement is separately preregistered; ASTRA/SOL and the shared runtime remain untouched.
