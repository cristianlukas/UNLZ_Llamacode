# Q107 — Diagnóstico del fallo `update_binary_sh`

**Estado:** cerrada PASS; la falla inicial se atribuyó al entorno de prueba. **Lock:** `307e2ed3-6036-4a52-852b-d4f481e21ee0`.

## Pregunta

¿Las dos aserciones fallidas de `update_binary_sh` en la corrida Q106 se reproducen al ejecutar el test aislado desde el mirror de CMake y desde CTest? Localizar si la causa es determinista del script, diferencia de entorno/mirror o flakiness del harness, sin cambiar código antes de identificarla.

## Experimentos preregistrados

1. Ejecutar una vez el script de prueba aislado desde `/home/cristian/.cache/llamacode/source/tests/test_update_binary_sh.sh`, guardar stdout/stderr y exit status.
2. Ejecutar una vez `ctest --test-dir /home/cristian/.cache/llamacode/build_tests_linux -R '^update_binary_sh$' --output-on-failure`, guardar salida/exit status.
3. Comparar los dos resultados con `/home/cristian/.cache/llamacode/build_tests_linux/Testing/Temporary/LastTest.log` de Q106 y revisar los archivos de prueba relevantes. Si no se reproduce, clasificar como fallo no reproducido y no editar. Si se reproduce, proponer enmienda limitada con una regresión concreta; sincronizarla y leerla de vuelta antes de cualquier edición/fix adicional.

## Límites y recursos

CPU/shell y temporales del propio test; sin build, inferencia, modelo, servidor, red, GPU ni cambio de límites de RAM/swap. Host de referencia: 2× RTX 3090 + 128 GB RAM. No matar procesos de escritorio ni de terceros.

## Criterios

- Determinar reproducibilidad en 2 entornos y preservar ambos logs.
- No afirmar que el fallo causa cierres de Codex: esta prueba sólo cubre el updater.
- No tocar el backend de tools ni los perfiles/modelos ASTRA/SOL/Qwen.


## Amendment 01 — reproducible failure

Direct script and isolated CTest both exited nonzero and reproduced the same two assertions (menu unchanged; warning/autostart untouched). Before any fix, run one minimal synthetic reproduction of the wrapper scenario from the test with a temporary package, wrapper, menu and autostart. Capture updater stdout and the exact menu/autostart contents before and after. This may classify the issue as test fixture/environment mismatch or expose a deterministic updater behavior. Do not edit repo source or test files in this amendment.


## Amendment 02 — runner environment correction

La inspección de la fixture demuestra que el propio comando de prueba inyectó `LLAMACODE_Q77_SERVER_URL=` y `LLAMACODE_Q102_SERVER_URL=`. El entorno de la sesión no tenía variables `LLAMACODE_*`; aun así, `update-binary.sh` detecta la presencia del nombre (sin comprobar valor no vacío) y escribió `launcher.env`, por eso el wrapper dejó de preservarse. No es un fallo del código de producción ni requiere editar el test.

Repetir, en este orden, el script directo, CTest aislado y el gate Linux Release con las dos variables realmente ausentes (no exportadas). `CUDA_VISIBLE_DEVICES` queda vacío. Si el gate completo pasa, enmendar los resultados Q106/Q107 y cerrar; si no, conservar la nueva falla. Sin cambios de código.
