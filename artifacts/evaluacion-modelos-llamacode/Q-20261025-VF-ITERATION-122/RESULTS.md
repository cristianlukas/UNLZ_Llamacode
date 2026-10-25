# Q122 · regresiones Linux para tandas de herramientas · 2026-10-25

## Resultado

El gate completo `env -u LLAMACODE_Q77_SERVER_URL -u LLAMACODE_Q102_SERVER_URL LC_JOBS=4 ./scripts/tests-linux.sh Release` terminó correctamente: **build Release PASS y CTest 95/95 PASS, 0 fallas**. Se compiló y probó desde la caché nativa Linux que usa el script para este checkout NTFS.

Las regresiones relacionadas con la tanda de herramientas pasaron dentro de `test_agent_wire`:

- `toolBatchRequiresReplan_onlyTaskBatchesFanOut`: PASS.
- `nativeToolBatchReplansAfterFirstResult`: PASS.
- `nativeMixedTaskBatchDoesNotDispatchLaterTaskEarly`: PASS.
- El ejecutable `test_agent_wire` terminó con 78 PASS, 0 FAIL y un SKIP opt-in: `qwenQ77NativeDispatcherProbe`, porque no se definió endpoint Qwen.
- `test_agent_tools` terminó con 55 PASS, 0 FAIL y 6 SKIP en 112,257 s. Los SKIP fueron la evaluación opt-in Q44 sin su fixture/endpoint y pruebas UIA/Windows no disponibles en Linux.

Se comprobó que el proceso de inferencia seguía ausente tras el gate. La prueba usó CPU, build y sockets loopback de fixtures; no se inició modelo, inference server ni GPU, no se hicieron conexiones externas ni se asignó memoria artificial. Los hashes de los tres archivos C++/test bajo validación siguieron idénticos al prerregistro; sus cambios preexistentes permanecen sin modificar y sin commit propio de Q122.

## Decisión para P2.1

Q122 valida el orden de ejecución/replanificación en el estado actual de trabajo. **No valida identidad confiable ni autorización por tenant**, así que P2.1 continúa abierto para pruebas con efectos entre tenants. Antes de habilitar esa prueba debe existir un principal propagado por un host confiable y una policy real aplicada al recurso. Los resultados de calidad/seguridad de Qwen3.8-27B y demás modelos no cambian; no se promovió ningún perfil.

La posible repetición Q95 se descartó porque el gate Bubblewrap ya fue corregido por Q96 y la comparación Swift-vs-ASTRA se ejecutó después en Q97. Evitar repetirla no elimina el score fallido de Q97.

## Evidencia

- `PLAN.md` y `receipts/preregistration.json`.
- `receipts/sheet-preregistration-readback.json` y `receipts/google-sheet-sync-final.json`.
- `receipts/q122-test-run.json` y `receipts/postflight.json`.
- `runs/tests-linux-release.log` y `/home/cristian/.cache/llamacode/build_tests_linux/Testing/Temporary/LastTest.log`.
- Código C++ existente verificado por SHA-256 contra el prerregistro; no editado en Q122.
