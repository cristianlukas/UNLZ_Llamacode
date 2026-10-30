# Orden de perfiles por Calidad Q172

Los selectores de perfiles ordenan primero los que tienen un resultado Q172
verificado, de mayor a menor puntuación (0–100). Los perfiles sin puntuación
quedan al final; entre perfiles con la misma puntuación o sin puntuación se
conserva el orden operativo anterior (`menuOrder`, BEST, favoritos, último uso
y número incremental). Los selectores muestran el valor junto al nombre.

La puntuación pertenece al perfil concreto. En **Perfiles**, se puede editar
para un perfil de usuario; dejar el campo vacío significa N/D. Los perfiles de
sistema son de solo lectura. Si cambia la configuración de un perfil de usuario
(modelo, backend, runtime, argumentos u otra configuración evaluada), se borra
la puntuación para evitar ordenar con un resultado obsoleto.

Las puntuaciones de sistema se cargan desde `assets/system_profiles.json` y sólo
se precargan donde el artefacto y la receta coinciden con una fila Q172 de la
hoja «Modelos locales por peso»: ASTRA (89), SOL/Strata (73), Qwen3.5-9B MTP
(69) y Gemma 4 E4B QAT (52). No se heredan resultados de cuantizaciones,
artefactos o runtimes relacionados; los demás perfiles aparecen como N/D hasta
que exista un resultado exacto.
