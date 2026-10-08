# LlamaCode: retest de velocidad de apertura

Fecha: 2026-10-08. Plataforma: Ubuntu, build Linux Debug, Qt 6.8.3, sesión
headless `offscreen`. No se inició ningún modelo ni se usó GPU. Cada smoke usó
directorios XDG temporales para no tocar las preferencias del usuario.

## Diagnóstico

La demora no estaba en el escaneo inicial de modelos ni en la detección de GPU.
Una captura de Qt QML Profiler mostró que el binding inicial
`LaunchPage.qml:491` tardaba aproximadamente 5,86 s. El desglose instrumentado
de `launchMenu()` confirmó 271 entradas; las comprobaciones síncronas de
disponibilidad sumaban 5,76 s. La creación de `Main.qml` y el primer frame eran
los que aparecían bloqueados.

## Mediciones

| Métrica | Antes del cambio | Después |
|---|---:|---:|
| `Main.qml` / primera ventana visible | 6.151–6.415 ms (3 ejecuciones) | 208 ms (smoke final) |
| Arranque de fondo, después de mostrar ventana | 59–119 ms en la medición previa | 155 ms; finalizó a 379 ms desde el inicio |
| Carga de primera página Lanzar | validación síncrona dentro del binding: ~5,86 s | página y primer frame no esperan el catálogo completo |
| Validación de disponibilidad del menú | bloqueaba el GUI durante ~5,76 s | 281 perfiles validados incrementalmente en 7,205 s de tiempo total |

La primera ventana se mostró aproximadamente **29–31 veces antes** que en la
línea base (unos 96,6–96,8% menos latencia). El tiempo completo de validación
del catálogo no desapareció: ahora ocurre después de pintar y se intercala con
el event loop para que la UI pueda responder.

## Cambios y verificación

- Las páginas QML se cargan bajo demanda por URL asíncrona y permanecen activas
  tras su primera apertura.
- Lanzar y Tuner consultan de inmediato metadatos ligeros; la validación de
  readiness se distribuye entre eventos del GUI. Los resultados actualizan la
  lista sin perder el perfil seleccionado.
- Los estados booleanos de navegación ahora son explícitos; desaparecieron los
  avisos `Unable to assign [undefined] to bool` observados en la línea base.
- Smoke final: `First window visible elapsedMs=208`; `Startup complete` a
  `elapsedMs=155` (379 ms desde el inicio); comprobación del menú finalizada con
  `profiles=281` en 7.205 ms. No se registró una pausa del event loop.
- Comando de compilación: `./scripts/build-linux.sh Debug`.
- Gate: `./scripts/tests-linux.sh Release` — **79/79 aprobadas**, 84,93 s de
  tiempo de pruebas; incluye `qml_lazy_page_loader`, `qml_navigation_policy`
  y `test_system_profiles`.
- Build Debug final: `/home/cristian/.cache/llamacode/build_linux/LlamaCode`,
  115.586.416 bytes; SHA-256
  `dfd56c878b0fa9ece4a768d9efadd9d1dadea4acf6efdb629a406c2e4f71f824`.

Los resultados de apertura se midieron con logging ampliado y entorno offscreen;
el tiempo absoluto puede cambiar en una sesión de escritorio, pero el bloqueo
de 5,8 s en el hilo de UI se identificó directamente en QML Profiler. No se
reclama una aceleración equivalente de la inferencia o de la validación total.
