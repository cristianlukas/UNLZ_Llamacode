# Q-20261023-VF-ITERATION-52 — revalidación de cuatro fuentes bloqueadas

## Pregunta
¿Cambió alguna condición externa de las entradas #26 (cartuchos CUT3/Qwen2.5-72B), #28 (anécdota Qwen vs Opus), #31 (DeepSeek V4.1 ROCm) o #32 (Instagram) de VF-20261019-01, habilitando una prueba local que pueda cambiar una decisión?

## Alcance y protección
Revisión CPU/red de fuentes primarias y recibos existentes. No descargar, compilar, lanzar servidores, inferir ni usar GPU. Mantener intactos Qwen Flash-Next ASTRA, SOL y PeritoSoft. La confirmación comercial Swift y el acceso a un ejecutor Windows siguen fuera de esta pregunta.

## Criterio de habilitación
Sólo preregistrar una prueba si el material nuevo identifica un target compatible y una comparación local que pueda cambiar la decisión. Un log del publicador, una anécdota subjetiva o un resultado de otra arquitectura no son por sí mismos una prueba local.

## Inspecciones
- Abrir de nuevo las cuatro URLs originales.
- Para #26, verificar el post contra repositorio, script, log y licencia que enlaza.
- Para #28, revisar si aparecieron snapshot/diff/tests o una rúbrica reproducible.
- Para #31, comprobar soporte actual, requisitos de hardware y almacenamiento en el repo enlazado.
- Para #32, comprobar si el Reel/caption/transcripción se volvió accesible.
- Auditar `inbox.json`, el estado local de inference servers y las celdas de hoja destinadas al siguiente registro.

## Resultado esperado
Mantener cada entrada en su categoría correcta (bloqueada con condición concreta) si no cambió su gate; registrar fuente, motivo, siguiente paso y no ejecución.
