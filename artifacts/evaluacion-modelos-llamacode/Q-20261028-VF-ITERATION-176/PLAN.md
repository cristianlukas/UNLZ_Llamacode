# Q176 — Inicialización fría/caliente y asignación dual

## Objetivo
Completar las columnas nuevas de inicialización fría/caliente de `Resultados` con mediciones reales, y resolver si el perfil Flash-Next/NInfer puede medirse de forma dual en las dos RTX 3090.

## Orden / dependencia
Esperar a que Q174 termine y limpie sus procesos, puerto y GPU. Ejecutar un solo perfil a la vez. No usar Q176 mientras la descarga/inferencia Q174 esté activa.

## Definiciones medidas
- **Init fría (proceso):** segundos desde lanzar el servidor nuevo hasta readiness API estable, sin proceso del motor/modelo ni pesos residentes en VRAM al inicio. No se fuerza vaciado global de page cache; anotar estado observable de caché del sistema y RAM.
- **Init caliente (page cache):** cerrar limpiamente el servidor tras el primer arranque, relanzar proceso limpio con los mismos pesos/configuración inmediatamente después, dejando el page cache del sistema caliente; medir hasta readiness. No confundir con TTFT ni con servicio ya residente.
- Guardar readiness, primera solicitud/TTFT por separado. Si un motor no expone endpoint de readiness o impide un segundo arranque comparable, dejar N/D con causa concreta.

## Perfiles y GPUs
Usar artefacto/runtime/config exactos de la tabla actual de Resultados: DeepSeek DSX T16, Qwen Flash-Next Strata, Qwen Flash-Next NInfer, TERRA MTP-off, Bonsai PrismML, Gemma Q4_0 y Bonsai NInfer-all si Q174 pasa. Usar GPU0+GPU1 y la misma topología por perfil donde el runtime la soporte. No sustituir el registro histórico de Flash-Next/NInfer GPU1-only; si no hay ruta dual validada, registrar bloqueo y mantener N/D para esa ejecución.

## Contexto y exclusiones
Medir readiness con la configuración/contexto fijada para el perfil y anotar el máximo configurado; no enviar prompts largos durante el cronómetro. 512K queda excluido. Qwen Flash-Next Strata puede documentar su perfil YaRN×4/1M por separado de KVarN y de los niveles omitidos de Q173.

## Validez / seguridad
Hashes/runtime/config deben coincidir con la fila seleccionada. Una sola inferencia server activa. Preflight de listeners y compute servers; verificar ambas GPUs asignadas. Capturar log monotónico de start/readiness, GPU/RAM, puerto, y cleanup. Detener ante error de driver, OOM, Xid, servicio externo a localhost, uso externo de GPU o falta de GPU dual. No modificar producción ni PeritoSoft.

## Estado
Q176 completado con cobertura condicionada. Se midió readiness cold/hot para DeepSeek DSX, Flash-Next Strata YaRN×4/1M, TERRA MTP-off, PrismML, Gemma y Bonsai NInfer-all, todos usando ambas RTX 3090 en las topologías indicadas en `RESULTS.md`. Flash-Next/NInfer queda sin init dual: el preview Linux sólo fue calificado en GPU1 y no existe evidencia de soporte dual para dos tarjetas físicas; se conserva el histórico como GPU1-only y las celdas Q176 quedan N/D con la causa registrada. TERRA cold fue medido; hot falló antes de readiness con un CUDA device-side assert, sin OOM de host observado. No reintentar esos gates sin cambio material preregistrado. El Sheet `Resultados` se actualizó y se leyó de vuelta; ver `receipts/google-sheet-q176-init-sync.json`.
