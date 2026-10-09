# Congelación al abrir “Usar un servidor LAN”

Fecha: 2026-10-08. Evidencia de la sesión real en
`~/.local/share/LlamaCode/LlamaCode/llamacode-expanded.jsonl`, PID 1576434.
No se cerró ni manipuló ese proceso y no se inició ningún modelo ni se usó GPU.

## Causa

`discoverLanServers()` envía `LLAMACODE_DISCOVER_V1` por broadcast y por cada
interfaz de red activa. La respuesta UDP del `LlmGateway` se atiende en el hilo
GUI y llamaba `m_hooks.models()`. El hook llegaba a
`gatewayModelCatalog()` → `launchMenu()`, que recalculaba disponibilidad para
271 perfiles antes de responder. Cinco respuestas consecutivas tardaron
6.470–6.522 s cada una y bloquearon la interfaz; el monitor registró pausas de
32.558 s y 13.568 s en esa sesión.

## Cambio

`gatewayModelCatalog()` ahora usa `launchMenuQuick()` y sólo publica perfiles
cuyo readiness ya está confirmado en la caché de la comprobación incremental.
No vuelve a inspeccionar rutas/modelos durante cada paquete UDP ni cada
`GET /v1/models`. Mientras el escaneo inicial está en curso, responde con el
subconjunto ya confirmado; un nuevo descubrimiento obtiene el catálogo ampliado
cuando termina. También corregí los `Loader` QML: el estado de página visitada
ya no reasigna la propiedad `active` que depende de su propio binding.

## Verificación

- Regresión `controller_launchMenuQuickDefersReadinessWork`: el catálogo LAN
  devuelve en menos de 500 ms antes y después del escaneo; antes se espera un
  resultado vacío, después se comprueba que contiene perfiles listos.
- `controller_astraStrataIsListedAndRequiresLocalSetup` ahora espera el
  readiness incremental antes de verificar que ASTRA aparece en el catálogo.
- `qml_lazy_page_loader` verifica carga bajo demanda, conservación de página y
  el estado separado de `active`.
- Build local Debug: `/home/cristian/.cache/llamacode/build_linux/LlamaCode`,
  SHA-256 `9e8fbffd5a107aadd6ae78bb9aebf071bbfd7b2915b73b9493c04d83e9a7f612`.
- `./scripts/tests-linux.sh Release`: **79/79 aprobadas**, incluidas las
  regresiones de catálogo LAN, ASTRA readiness y carga perezosa QML.

El proceso que ya estaba abierto conserva el código cargado en memoria; la
compilación actualiza el binario que usará la próxima apertura de LlamaCode.
