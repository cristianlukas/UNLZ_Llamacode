# Rendimiento de arranque

LlamaCode crea la página inicial y carga las demás páginas QML cuando se
seleccionan. Una página permanece activa después de su primera apertura. Así el
arranque no compite con la construcción en segundo plano de secciones que el
usuario quizá no vaya a visitar.

Los tipos de páginas se resuelven mediante `Loader` con URL y carga asíncrona;
las páginas siguen retenidas una vez cargadas. En particular, Lanzar muestra
primero su lista liviana de perfiles. La comprobación de disponibilidad de cada
perfil se hace después, en pasos individuales del event loop. Los elementos sin
resultado todavía no se marcan como ausentes; al terminar, la lista se
reconstruye con los estados reales y conserva la selección del usuario. Esto
evita que un catálogo grande bloquee la primera pintura o la interacción.

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
La finalización de la comprobación incremental del menú informa
`Launch menu readiness complete` con duración y cantidad de perfiles.
El catálogo que usa Gateway para responder `/v1/models` y las consultas UDP de
descubrimiento consume esos estados ya calculados. Esos callbacks corren en el
hilo de la interfaz, por lo que no deben revalidar el catálogo completo al
responder cada paquete de red.

La respuesta UDP usa el mismo camino de catálogo rápido: el descubrimiento se
envía por cada interfaz activa y el servidor puede recibir varias consultas en
una sola búsqueda. La operación debe ser barata y sólo anunciar perfiles cuya
disponibilidad ya se verificó; mientras el escaneo sigue activo, devuelve el
subconjunto confirmado hasta el siguiente descubrimiento.

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
