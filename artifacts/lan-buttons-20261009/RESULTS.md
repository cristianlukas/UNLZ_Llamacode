# Botones de inicio LAN sin respuesta aparente

Fecha: 2026-10-09.

## Diagnóstico

Los dos botones dependían de asignar `gatewayLanEnabled` y `gatewayEnabled`.
Los setters de estas propiedades hacen early-return cuando el valor ya coincide
con la configuración. Si un intento previo no logró enlazar el puerto, volver a
hacer clic no invocaba de nuevo `startGateway()`. Además, la página no escuchaba
`serverError` para este flujo y el modo “sin perfil” no cambiaba el estado
visible del servidor de modelo; podía parecer que el clic no había hecho nada.

## Cambio

- `AppController::startLanGateway()` activa el bind LAN y reintenta el listener
  cuando no está ejecutándose, aunque los flags ya estuvieran activos.
- Ambos botones muestran progreso, confirmación, dirección LAN o error concreto
  en la cabecera y junto a las acciones.
- “Con este perfil” detiene el flujo si no pudo iniciar el gateway, reporta
  fallos de `serverError`/estado y confirma cuando el perfil queda listo.
- “Sin cargar perfil” confirma que el gateway está escuchando y recuerda que el
  cliente puede elegir un perfil.

## Verificación

- Regresión `controller_startLanGatewayRetriesWhenSettingsAlreadyEnabled`:
  ocupar el puerto hace fallar el primer bind; liberar el puerto y volver a
  llamar al inicio LAN con los mismos flags debe enlazar correctamente.
- `./scripts/build-linux.sh Debug`: OK; binario
  `/home/cristian/.cache/llamacode/build_linux/LlamaCode`, SHA-256
  `615e696286be08aac74aeb6b5a77aade599661e8a154dd8897bc1d0b45d8f206`.
- `./scripts/tests-linux.sh Release`: **79/79 aprobadas**.
- El lanzador `/home/cristian/.local/bin/llamacode` prioriza ese binario Debug,
  por lo que la próxima apertura usa el cambio.

La verificación cubre el controlador, el build y la suite; no automatiza un clic
en la sesión de escritorio del usuario.
