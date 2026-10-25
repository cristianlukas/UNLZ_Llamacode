# Q116 · Semántica de PSI severa alternada · 2026-10-25

## Resultado

**Q116-A1: comportamiento observado en el guard histórico Q97.** Los controles estables `full=60%` y `some=80%` pararon en la muestra 15. En cambio, 15 muestras alternadas (`full=60%, some=0%` / `full=0%, some=80%`) mantuvieron verdadera la condición OR severa en cada muestra, pero no pararon: Q97 lleva contadores independientes por métrica y cada contador vuelve a 0 al cambiar la dimensión. La secuencia `14 + normal + 14` tampoco paró y confirmó el reset.

El intento Q116-A1 número 01 ejecutó los escenarios en memoria, pero no escribió resultado porque una aserción del runner esperaba equivocadamente que ambos contadores terminasen en 1 después de que la muestra 15 fuera `full`. Se conservó como `receipts/attempt01-runner-error.json`; enmienda 01 corrigió sólo esa aserción antes del retry. El replay corregido produjo cuatro observaciones; no se oculta ni se cuenta el primer intento como PASS.

**Q116-A2: helper candidato compuesto 5/5 PASS.** Un helper versionado, separado y no integrado detiene la alternancia en la muestra 15; mantiene las fronteras de full/some, resetea después de una muestra normal y conserva el warning moderado en 30 muestras. El control `full=46,52%` advierte en la muestra 30 y no activa el hard-stop.

## Contexto de las cargas exitosas de memoria

La evidencia que motivó la revisión coincide con que la guarda no debe tratar RSS alto como presión crítica: ASTRA DEFAULT 1M Q14 terminó con RSS de proceso de 51,14 GiB y MemAvailable mínima de 55,64 GiB (Q97/Q98); la calibración Q101 registra 55,728 GiB para el mismo perfil. ASTRA Flash-Next 1M Q35 completó 3/3 con 64,98–65,06 GiB disponibles. SOL Q34 TP=2 terminó usando las dos RTX 3090 sin OOM, pero su recibo no contiene una serie continua de PSI, así que cuenta como éxito de ejecución y no como calibración PSI.

Esos casos no fueron interrumpidos por el detector recalibrado y la implementación no usa RSS ni porcentaje de RAM como umbral de corte. La decisión de Q116 se limita al significado de la racha PSI severa (OR compuesto frente a rachas independientes); no contradice los éxitos de ASTRA/SOL, no explica un cierre de Codex y no justifica reducir memoria, contexto o swap.

## Decisión

La política documentada formula el hard-stop como `full>=60% OR some>=80%` durante 15 muestras. El helper Q97/Q100 vigente requiere que una misma dimensión supere su límite durante las 15 muestras. Por lo tanto, si la regla intended es el OR compuesto por muestra, Q97 no implementa toda la semántica escrita para una presión severa que alterna dimensiones. El candidato Q116-A2 demuestra una corrección acotada sin tocar los umbrales ni el comportamiento de PSI moderada.

No se modifica retroactivamente Q97/Q100 ni el producto: son evidencia histórica y supervisor de campañas, no un monitor general de la aplicación Codex/GUI/driver. Para una próxima campaña, integrar la racha `severe_any` en un supervisor versionado o explicitar que la persistencia se exige por métrica antes de depender de esta parada. No se atribuye a esto el cierre de Codex.

ASTRA DEFAULT 1M, SOL, Flash-Next, PeritoSoft, RAM, swap y perfiles permanecen intactos. Q116 fue CPU-only con dos RTX 3090 representadas como fixtures; no hubo servidor, modelo, GPU, build, red ni asignación artificial de memoria.

## Evidencia

- `PLAN.md`; `receipts/preregistration.json`; `receipts/amendment-01-preregistration.json`; `receipts/amendment-02-preregistration.json`.
- `runner/test_q116_mixed_severe_psi.py`; `receipts/q116-mixed-severe-psi.json`; `receipts/attempt01-runner-error.json`.
- `candidate/q116_composite_psi.py`; `runner/test_q116_composite_psi_candidate.py`; `receipts/q116-composite-candidate.json`.
- `receipts/q116-preflight.json`; `receipts/q116-preflight-retry.json`; `receipts/q116-preflight-candidate.json`.
