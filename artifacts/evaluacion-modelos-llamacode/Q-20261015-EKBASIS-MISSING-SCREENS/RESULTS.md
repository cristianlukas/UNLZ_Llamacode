# Resultados — Q-20261015-EKBASIS-MISSING-SCREENS

**Fecha:** 2026-10-15
**Estado:** screening incremental completado; la integración y la reducción de daño siguen sin demostrar.
**Antecedente:** la campaña del 12/10 sólo corrió dos screens textuales. Este seguimiento cubrió imagen, recuperación hasta el contexto local de 4K y latencia serial.

## Decisión

No integrar Ekbasis como sidecar ni delegarle permisos. Se mantienen las aprobaciones deterministas. El probe visual dio **9/11** y confundió amarillo/naranja con confianza alta; la recuperación textual dio **9/9** sólo en un fixture sintético de hasta 3.526 tokens efectivos. La latencia de **135,67 ms mediana** es atractiva para un predictor caliente, pero no mide un agente completo ni demuestra menos acciones dañinas. No se cambió ningún perfil, gate, HarnessSpec ni comportamiento productivo.

## Modelo y entorno

- `caiovicentino1/Ekbasis-27B-INT4`, revisión `8e78979bed4d5d47d11ac169ccc9e769f7e4b8d3`; SHA-256 del peso `3ef9d39220a665c741bd734dfa59637607f62993f7f1a52dca2383af6cd085e1`, verificado antes de cargar.
- vLLM 0.30.0, PyTorch 2.13.0+cu130, Transformers 5.19.0; API oficial `serve.py` 1.3, calibración activa, `verify=0`, loopback solamente. GPU1 RTX 3090, bf16, `max_model_len=4096`, una secuencia. Perfil efectivo conservó fingerprint `c4eb3a5b0c3fb2898aa5c70516b857394b4f4cee0ed15e0d2890417958efc01d`.
- La primera activación del adaptador tuvo un URL mal formado y recibió 404 durante warmup, antes de enviar casos puntuados. Se corrigió a la URL base; los casos siguientes terminaron por HTTP 200. El runner pasó `py_compile`; la campaña terminó con código 0.

## Visión

Se mandó el fixture sintético de conteo `vision-holdout-v1` como PNG data URI a la interfaz de decisión con imagen. El verificador externo comparó 4 formas y 7 colores.

| Grupo | Exactitud | Observación |
|---|---:|---|
| Formas | 4/4 | Círculos, triángulos, rectángulos y estrella correctos. |
| Colores | 5/7 | Confundió amarillo (respondió 0) y naranja (respondió 2); cada uno aparecía una vez. |
| Total | 9/11 | Sin exact match. Confianzas en esos dos errores: 0,796 y 0,948. |

Una sola imagen sintética no acredita visión de pantallas reales, variantes de tema/idioma ni ejecución de una acción GUI.

## Recuperación y contexto efectivo

Nueve decisiones con un dato sintético único ubicado aproximadamente al 5%, 50% o 95% de estados de tres tamaños. Resultado **9/9**, una pasada determinista, sin seeds independientes.

| Estado objetivo | Tokens efectivos máximos (incluye prompt) | Resultado |
|---:|---:|---:|
| 1.000 | 1.126 | 3/3 |
| 2.000 | 2.134 | 3/3 |
| 3.400 | 3.526 | 3/3 |

El límite del servidor fue 4.096 tokens. No se probó el contexto anunciado de 16K/262K ni recuperación en sesiones largas de agente.

## Rendimiento del predictor

Doce decisiones cortas, seriales y con el modelo ya caliente: transporte 12/12; latencia cliente mediana **135,67 ms**, p95 **136,90 ms**, mínimo 134,47 ms y máximo 136,97 ms; **7,37 decisiones/s** en esta secuencia. No es TPS de generación, carga concurrente ni comparación A/B. Excluye descarga, carga y warmup del servidor.

## Lo que quedó sin evaluar

- **Coding/agente y Computer Usage E2E:** sin runner local compatible (`node`, Playwright y Chromium no están disponibles) y sin integración de Ekbasis en el agente. El estudio de acciones reales requiere brazos base/sidecar y un estado final comprobable; no se reemplazó con un mock ni se ejecutó nada en apps del usuario.
- **Ingi-Charla/audio:** la API oficial revisada expone decisiones de texto e imágenes, no ASR/TTS ni entrada acústica; no hay una prueba acústica pertinente para este modelo.
- **Contexto >4K:** fuera de la configuración local de este servidor y no probado.

Para retomar E2E hacen falta un runner compatible, una integración aislada del sidecar y un simulador/fixture con etiquetas independientes, varias tareas y estado final verificable. Para generalizar visión se necesita un holdout de pantallas reales con varias condiciones.

## Limpieza y pruebas de código

El servidor vLLM y el adaptador propios se detuvieron. Puertos 18171/18172 libres; GPU1 volvió a 108 MiB, `MemAvailable` 106 GiB, PSI 0 y swap 4,9 GiB frente a 5,0 GiB antes del test. Sin cambios C++/QML/core, por lo que el gate de pruebas del producto no aplicaba. Sí pasó `python -m py_compile` para el runner y `git diff --check`.

## Recibos

- [Plan preregistrado y cierre](PLAN.md)
- [Resumen combinado](receipts/summary.json)
- [Predicciones visuales crudas](receipts/vision/raw.jsonl), [request exacto](receipts/vision/request.json), [fixture](receipts/vision/vision-holdout.png)
- [Requests/responses de recuperación](receipts/context/raw.jsonl) y [resumen](receipts/context/summary.json)
- [Requests/responses de latencia](receipts/performance/raw.jsonl) y [resumen](receipts/performance/summary.json)
- [Fingerprint de runtime/suites](receipts/runtime/effective-profile-manifest.json), [preflight](receipts/runtime/preflight.txt), [postflight](receipts/runtime/postflight.txt), [log del runner](receipts/runtime/run.log)

Fingerprint de corrida: `0fca6cc7af7fdc85d02616f954e3d83a55b7dab723d460f7b6269ac326fb245f`. Repetir sólo para variabilidad o con un holdout E2E independiente; no duplicar estos prompts para declarar una mejora.
