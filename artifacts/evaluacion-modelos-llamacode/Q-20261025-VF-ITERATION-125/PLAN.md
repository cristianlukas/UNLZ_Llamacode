# Q125 · auditoría del detector y conciliación de cola/Sheets

## Objetivo
Resolver la duda del usuario sobre el detector de presión de memoria usando la evidencia ya obtenida de ASTRA DEFAULT 1M y SOL en el host dual RTX 3090 + 128 GiB, y corregir discrepancias documentales de la cola/Google Sheet. Mantener ASTRA, SOL, Flash-Next y PeritoSoft intactos.

## Preregistro / alcance
- Auditoría documental y de código existente: Q116/Q117/Q118/Q120/Q121. Verificar qué guard se ejecutó en cada caso y separar RSS alto, PSI, MemAvailable, swap/OOM, guard histórico Q97/Q100 y candidato AMD05. No reejecutar el replay ni pruebas CPU ya cubiertas; no hay condición ambiental nueva.
- Sin build, inferencia, descarga, GPU compute, estrés artificial ni servidor. No matar procesos. No tocar umbrales productivos ni perfil/contexto/RAM/swap.
- Google Sheets: reconciliar las filas Accionables 5, 6, 8, 9, 10, 11, 12, 13, 14, 15 y 16 (A:N) contra resultados locales/recibos; preservar IDs/prioridades B:C y formato WRAP, clasificando A según estado real. Leer de vuelta exactamente las mismas celdas y verificar sentinels vecinos.
- Fuente VF-20261019-01: corregir sólo el texto obsoleto de `inbox.json` #56 (S56 no tuvo respuesta tras cuatro fallos/arranque en D-state; no más retries sin cambio runtime/storage y preregistro nuevo), #57 (S57 confirmó contexto efectivo ASTRA IQ2_XS 1M en smoke corto, no retrieval/calidad 1M) y #58 (migración sí verificada; el recuento 149 es snapshot histórico, no total actual). Tomar backup previo y mantener 58 entradas.

## Hipótesis y criterios
1. Uso alto no equivale a presión crítica: un guard correcto debe dejar terminar ASTRA 1M con ~51.306 GiB RSS cuando MemAvailable se mantiene sobre ~58.698 GiB, aunque haya PSI moderada/severa aislada.
2. La ruta histórica Q97/Q100 y el candidate-only AMD05 no son el mismo detector. Q116 documenta gap de racha PSI alternante en Q97; AMD05 agrega una racha OR compuesta de PSI global severa + MemAvailable <48 GiB por 15 muestras, con fallos OOM/telemetría y piso <32 GiB.
3. Veredicto conservador: AMD05 sí pasó la carga real ASTRA 1M/replay, pero la conjunción severa+low-headroom no se observó en la carga real; el stop sólo está validado con fixtures CPU. No integrar a producción y no atribuir cierres de Codex. SOL Q34 acabó sin OOM, sin serie PSI continua.
4. Reconciliación completa sólo si la lectura de vuelta del Sheet coincide exactamente con los valores escritos, conserva A:C y WRAP; JSON corregido sigue válido y 58/58 entradas.

## Evidencia a contrastar
Q116 RESULTS + pruebas de alternancia; Q117 RESULTS + suite 21/21 y traza ASTRA real; Q118 replay 12/12 de 707 muestras; Q120 auditoría; Q121 wrapper 8/8. Entradas fuente #55–#58 y actionables locales.

## Bloqueos y siguiente paso
No hay otra prueba model-backed local elegible después de Q124: HyperQwen requiere defecto parser/runtime material (Q104 no lo halló); Flash-Next NInfer/Job Objects requieren Windows nativo; tenant auth espera principal/policy real. La próxima ejecución AMD05 sólo se habilita al abrirse una evaluación local nueva y debe fijar hashes via Q121 antes de iniciar el worker.
