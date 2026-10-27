# Q164 · PeritoSoft/inference process gate and test resumption

- **Fecha:** 2026-10-27T04:37:32Z.
- **Lock:** se reutilizó el lock persistente Q146 `2242863e-c78e-4fa9-9649-c1d1541f3919`.
- **Solicitud:** cerrar PeritoSoft y sus llama-server antes de continuar.
- **Resultado de proceso:** no se encontró proceso PeritoSoft ni llama-server/llama.cpp/NInfer/Strata escuchando como servicio, ni contenedor Docker relacionado. Por eso no se envió ninguna señal y no se cerró ningún proceso.
- **GPU/puertos:** `nvidia-smi` mostró `artcraft-launcher` (207 MiB), sin identificarlo como inferencia; no se terminó. Los listeners visibles fueron OpenRGB, CUPS, Artcraft y DNS local; no había listener de LlamaCode/PeritoSoft en los puertos de servicio revisados. El usuario había indicado que la interfaz gráfica no impide probar.
- **Continuación de pruebas:** no ejecuté un benchmark sustituto. Los pendientes locales siguen sin cumplir sus prerequisitos: C39-02 NInfer Flash-Next y Job Objects requieren Windows nativo; tenant safety necesita principal autenticado y policy confiable; Harness² necesita workflow y holdout fijo; validación de pedido necesita la transcripción primaria; HyperQwen requiere un defecto parser/runtime reproducible; Q119 necesita una traza real de presión crítica. No se induce presión artificial.
- **Estado de modelos:** sin resultados nuevos, scores ni cambios de adopción. ASTRA Flash-Next RCO IQ2_XS, SOL y modelos/datos de PeritoSoft permanecen intactos.
- **Sheet:** no se añadió fila de Evaluaciones porque no se realizó un test ni cambió un resultado/acción.
