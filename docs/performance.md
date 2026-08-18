# Rendimiento de la interfaz

## Carga diferida de páginas

`qml/Main.qml` no construye todas las páginas al iniciar. Cada sección se
define como un `Component` y se instancia mediante un `Loader` cuando el
usuario la visita por primera vez. Una vez creada, la página permanece viva
para conservar el estado temporal de sus formularios y evitar reconstrucciones
innecesarias.

La página de inicio es la única que se carga durante el arranque. Esto reduce
el trabajo inicial del hilo GUI y permite que el menú de la bandeja y la
ventana respondan mientras el resto de la aplicación queda disponible bajo
demanda.

## Diagnóstico del event loop

El build de escritorio registra una advertencia cuando el hilo GUI deja de
procesar eventos durante 250 ms o más:

```text
GUI event-loop pause ms=...
```

Estas pausas son evidencia de trabajo síncrono en el hilo principal. Deben
correlacionarse con la acción que el usuario estaba realizando antes de mover
operaciones de disco o CPU a tareas asíncronas.

## Validación

Después de cambios en QML o C++ de la interfaz:

```bat
tests.bat Debug
build.bat Debug NOPAUSE
```

Además de la suite automática, comprobar manualmente el click derecho del tray,
la restauración de la ventana, el cambio entre páginas y las acciones de
agregar binarios/modelos desde el asistente inicial.
