# Smoke del log ampliado

Arranque aislado del ejecutable seleccionado por `/home/cristian/.local/bin/llamacode`, con `QT_QPA_PLATFORM=offscreen`, almacenamiento de prueba, sin preferencia persistente de log y el argumento `--expanded-log`.

La evidencia JSONL comienza en `process_start` (antes de `QApplication`) y marca `expandedLoggingSource=command_line`; registra las fases `QQuickStyle`, `QApplication` y `Main.qml`, muestras de CPU/RSS y la pausa del event loop. En esta corrida offscreen, `Main.qml` tardó 6076 ms y el primer pulso detectó una pausa de 6091 ms. La consola conserva tres avisos de QML en `NavBar.qml:79` (`Unable to assign [undefined] to bool`). No interpretar esos tiempos como benchmark de una sesión de escritorio normal; la finalidad es verificar la instrumentación y el modo de lanzamiento de emergencia.
