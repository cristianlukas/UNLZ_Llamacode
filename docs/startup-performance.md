# Rendimiento de arranque

LlamaCode crea la página inicial y carga las demás páginas QML cuando se
seleccionan. Una página permanece activa después de su primera apertura. Así el
arranque no compite con la construcción en segundo plano de secciones que el
usuario quizá no vaya a visitar.

## Fases

1. Se crea y muestra la ventana.
2. Se actualizan registros livianos de binarios y roots.
3. La detección de GPU (`nvidia-smi`) corre en un worker.
4. El catálogo se diagnostica y los roots se escanean después del primer frame.
5. Benchmark, Research y recomendaciones se preparan en la fase tardía.

La fase final registra tiempos por operación en `llamacode.log`: actualización
de registros, diagnóstico del catálogo, envío de escaneos, lectura/importación
de benchmarks y actualización de Research. Los escaneos de roots usan workers;
el registro separa el tiempo de envío del trabajo asíncrono.

Las páginas se crean bajo demanda y quedan en memoria después de abrirse por
primera vez. En particular, Ranking no se construye automáticamente al iniciar:
su tabla y sus especificaciones sólo se calculan cuando se visita esa sección.

La UI expone `App.startupBusy`, `App.startupStatus` y
`App.startupTimings`. El log de la aplicación registra también los tiempos
hasta `QApplication ready`, carga de `Main.qml`, primera ventana visible y
entrada al event loop. Esto permite comparar `LlamaCode` y
`LlamaCode-debug` sin inferir el origen de una demora.

El monitor del event loop se puede activar después de iniciar la app. Al
reactivarse, reinicia su marca temporal para no reportar como bloqueo el tiempo
anterior a que el monitor estuviera corriendo.

## Catálogo incremental

El escáner conserva la metadata previamente catalogada cuando coinciden ruta,
tamaño y fecha de modificación. Sólo los archivos nuevos o modificados vuelven
a leer el header GGUF y a calcular composición, quant real y arquitectura.

Los roots de inicio ya no se escanean durante la construcción de
`AppController`; se programan desde la fase de startup posterior al primer
pintado. Los roots manuales mantienen su comportamiento y sólo se escanean al
pedir un rescan.
