# Q146 · Resultados históricos añadidos a Google Sheets

Se añadieron **56 filas** en `Resultados!A291:AF346`, tras auditar las 18 pestañas del workbook y cotejar los IDs de Resultados con la evidencia local. Antes de la migración había 289 IDs únicos; después hay 345.

La lectura de vuelta exacta verificó las 1.792 celdas del rango, cero diferencias, cero fórmulas/chips/validaciones y el formato WRAP/TOP/Arial 10. Los paneles congelados (fila 1 y columnas A:D) se conservaron.

## Resultados incorporados
- **Mica v0.1 4B:** replay local Tetris 797/797 decisiones coincidentes; perfil auxiliar de decisión, sin presentarlo como modelo de coding.
- **MiMo-V2.6 Distill Qwen 9B y control Qwen3.5-9B:** throughput y HumanEval/20 lado a lado; BCB del MiMo marcado inválido por contaminación del entorno.
- **Opti-27B:** pruebas de texto 16K/262K, prefill largo, cuatro sesiones, visión y tool-call; fallo con reasoning on claramente registrado.
- **Laya 421M:** latencia/router/guardrail como componente auxiliar, no generador.
- **LFM2.5-VL-3B + DSpark:** control, n=8 y n=9; aceleración de decode separada del fallo de precisión espacial de Computer Use.
- **Qwen3.8-27B:** cuatro resultados históricos de throughput multimodal y nueve finalistas HumanEval/20, con throughput HE0 y tiempo total HE20.
- **Flash-Next IQ1_S:** sweep sin MTP, MTP corto, prompt largo, tool smoke, BCB de un ítem y head Q4 incompatible; el ítem parcial no se cuenta como BCB completo.
- **NInfer Qwen3.6-35B-A3B:** MTP/control, sweep de contexto textual, contexto visual, reutilización de prefijo y límite visual de 262K.
- **ExLlamaV3 Flash-Next EXL3:** texto y visión a 262K, single-GPU, reserva 512K y fallo 1M.
- **BeeLlama Qwen3.8 KVarN5/KVarN4:** control/candidato a 8K y 131K.
- **Ling 3.0 Tiny:** perfil APEX vs Qwen3.5-2B de mismo prompt, perfil auxiliar 131K/tool/context y ocho combinaciones CPU Q4/Q6, 4K/8K, thinking off/on.

## Interpretación
No son una única cohorte. Los registros separan suites de coding, pruebas de humo, velocidad multimodal, routing y memoria/contexto. Ninguna fila convierte por sí sola un perfil en reemplazo de SOL/ASTRA. Se mantuvieron resultados negativos y parciales porque evitan repetir configuraciones incompatibles o atribuir calidad donde no se midió.

## Exclusiones
- Duplicados por modelo/quant/suite/fingerprint ya presentes en filas previas del sheet.
- Claims de terceros sin ejecución local.
- Runs sin respuesta o evidencia mínima para una métrica.
- Scores derivados; no se sintetizó una métrica de calidad/velocidad global.
