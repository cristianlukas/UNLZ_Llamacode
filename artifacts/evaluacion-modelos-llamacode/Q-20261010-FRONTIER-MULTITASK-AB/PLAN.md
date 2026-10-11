# Comparación Frontier Multi-Task — SOL vs ASTRA vs Flash-Next Q4

## Objetivo

Medir si SOL, ASTRA IQ3_S calibrado o Qwen3.8-Flash-Next UD-Q4_K_XL resuelven mejor tareas difíciles de uso de herramientas, restricciones, recuperación de errores, estado y seguridad. Es una comparación de los endpoints/model-runtime profiles locales; no es una evaluación del agente completo de LlamaCode.

## Suite y por qué se eligió

- `tool-eval-bench` oficial, release **v2.8.0**, commit `0a1ba68c7709f429298bc92417a9e003f61de4e3`.
- Usar las **28 tareas Hard Mode (TC-70…TC-97)**, categoría P, sin el conjunto estándar fácil.
- Cobertura que interesa aquí: herramientas casi duplicadas, llamadas encadenadas, corrección de ambigüedades, recuperación de errores, restricciones múltiples, estado entre turnos, actualización condicional, prompt injection en resultado de herramienta, memoria contradictoria, paginación, transacciones, concurrencia optimista, autorización, aislamiento por tenant y manipulación de documentos.
- Los escenarios usan herramientas simuladas y evaluación determinista por escenario; no ejecutan acciones en servicios reales. La suite puntúa pass/partial/fail y conserva traza de conversación.
- Inspiración complementaria: Terminal-Bench favorece tareas difíciles en entornos aislados con pruebas de verificación; aquí tomamos la dificultad, el estado controlado y la verificación reproducible, sin afirmar que esto sea Terminal-Bench.

## Condiciones fijadas

- 28 escenarios Hard Mode completos; secuenciales (`parallel=1`), 8 turnos máximos y timeout 120 s por request.
- Tres seeds de inferencia pareadas: `42`, `43`, `44`; mismo `variant_seed=20261010` para todos los perfiles y seeds.
- Sampling común por request: temperature 0.6, top-p 0.95, top-k 20, min-p 0.0, repetition penalty 1.0 y presence penalty 0.0; razonamiento medium si lo acepta el servidor.
- Mismo runner v2.8.0, system prompt incorporado, lista y orden de escenarios, fixtures y límites. GPU compartida en exclusiva; perfiles cargados y probados de a uno en ambas RTX 3090.
- No reintentar fallos de modelo en silencio. Las respuestas no puntuables por falta de capacidad/infraestructura se reportan aparte mediante `completion_rate` y trazas.

## Perfiles a comparar

1. **SOL:** Qwen3.8-27B AutoRound INT4, vLLM 0.27.1, TP2/P2P, MTP4, KV FP8, endpoint local `127.0.0.1:8113`. Compose con la cuarentena de VRAM incluida en su configuración; acceso de esta prueba limitado a loopback.
2. **ASTRA:** Qwen3.8-Flash-Next GSQ-RCO IQ3_S calibrado, Strata 0.1.41 (mismo build de Strata que se usa para Q4), dos RTX 3090, MTP4, KV int8, contexto 131072, `spec-min-p=0.70`, `pcie-frac=0.00`, endpoint `127.0.0.1:8350`. El pack IQ3_S disponible está en `Models/FlashNext-IQ3XXS-ISTA-Strata-eval-20261009/strata-data/packs/iq3_s`; los shards y MTP son los IQ3_S ASTRA ya verificados en la campaña anterior.
3. **Flash-Next Q4:** Unsloth UD-Q4_K_XL, Strata 0.1.41, dos RTX 3090, MTP4, KV int8, contexto 131072, `spec-min-p=0.70`, `--resident-experts`, split 18/30, endpoint `127.0.0.1:8350`; se reutilizan los hashes y config del screening Q4 completado.

**Identidad del alias:** el `ASTRA` actualmente marcado deprecated en `profiles/launches.json` apunta al mismo model-profile UD-Q4_K_XL que el candidato Q4. Para que ASTRA/Q4 compare dos pesos distintos y se mantenga continuidad con los resultados previos, el brazo ASTRA de esta prueba es el ASTRA IQ3_S calibrado que se usó en las comparaciones anteriores. El resultado no debe etiquetarse como comparación del alias deprecated actual.

## Lectura de resultados

- Tabla principal: score total y por seed; reportar también escenarios completos, parciales, fallidos, seguridad y errores de endpoint.
- Comparación por escenario pareada entre los tres perfiles y estabilidad de cada perfil entre los tres seeds.
- Tiempo total/latencia sólo como métrica secundaria: los runtimes y cuantizaciones son distintos y el objetivo principal es calidad de tool-use.
- Una diferencia en esta suite no demuestra mejor coding, Computer Usage GUI, voz, visión o contexto largo. No cambiar perfiles ni HarnessSpec a partir de un screening aislado.

## Referencias metodológicas

- Terminal-Bench 2.0: cada task tiene entorno aislado y tests de verificación; ver `https://github.com/harbor-framework/terminal-bench`.
- tool-eval-bench v2.8.0: 28 escenarios Hard Mode, herramientas mockeadas, evaluador determinista por caso y trazas; fuente `https://github.com/SeraphimSerapis/tool-eval-bench`.
