# Q126 · borde de presión PSI alternada en AMD05

## Pregunta

¿El guard candidato AMD05 acumula correctamente el OR de presión PSI global cuando la señal alterna entre `full >= 60%` y `some >= 80%`, y exige a la vez menos de 48 GiB de memoria disponible por 15 muestras consecutivas? ¿Evita detenerse en el borde de 48 GiB y reinicia la racha cuando una muestra deja de ser severa?

## Prerregistro

- **Alcance:** regresión determinista CPU-only del guard importado por `run_context_holdout_attempt05.py`. No modifica el guard, no crea presión real, no reserva RAM, no inicia modelo/servidor/CUDA/GPU y no compila.
- **Fuentes fijadas:** `scripts/q117_pressure_guard_attempt05.py` SHA-256 `b4d42302e7d405abd5c59df5aa86bb7de6ef3bb91aef487b49acbebd1d24270e`; `guard_sources/q108_guard_core.py` SHA-256 `832c6661692fa9c6e45d209be5c4201a1ad796bfe66bec92cf947151e6988b4b`.
- **Caso A:** 15 muestras alternadas `full=60%` / `some=80%`, cada una con `MemAvailable=47,99 GiB`; esperar sin corte hasta la 14 y corte en la 15.
- **Caso B:** 30 muestras con la misma alternancia y `MemAvailable=48,00 GiB`; esperar cero cortes por presión PSI.
- **Caso C:** 14 muestras severas alternadas a 47,99 GiB, una muestra normal que reinicia la racha, 14 severas alternadas y una severa más; esperar corte sólo en la muestra global 30.
- **Criterio:** PASS sólo si cada índice y motivo de corte coinciden con lo anterior y las fuentes fijadas conservan sus hashes. Si falla, detener el análisis y no usar ningún runner de modelo hasta resolver la discrepancia.
- **Límite:** resultado sintético del guard; no demuestra que se haya observado esta combinación de presión real en el host ni integra AMD05 a los runners históricos Q97/Q100 o al producto.

## Resultado

**PASS, 4/4.** Alternancia severa a 47,99 GiB detuvo en muestra 15 (y no antes); la misma señal a 48,00 GiB no detuvo en 30 muestras; una muestra normal reinició la racha y el stop llegó en la muestra global 30. Hashes fuente sin cambios. Detalle en `receipts/cpu-boundary-regression.json`.

La prueba valida el candidato AMD05 únicamente. No cambia el guard histórico Q97/Q100 ni lo integra al producto; tampoco representa un evento real de presión en el host.
