# Perfiles de contexto ASTRA Flash-Next

El perfil ASTRA existente a 1M queda como referencia intacta. En Lanzamiento,
el usuario puede crear un perfil alternativo de 131.072 tokens para el uso normal
y, desde ese perfil, volver al 1M bajo demanda. La selección se guarda como el
último perfil elegido; no se modifica el JSON de Strata que usa el perfil fuente.

La variante ASTRA es una copia editable con un JSON propio bajo
`AppLocalData/LlamaCode/astra/context-variants/`. La creación valida el archivo de
origen y cambia únicamente el argumento `--max-context`; el backend OpenAI local,
el contexto declarado, el preset del runtime y el perfil quedan alineados. Si el
JSON no contiene exactamente un `--max-context` válido, la operación se cancela
sin dejar una variante parcial.

Las opciones de contexto son explícitas: 131K reduce el coste normal frente a la
prueba de 1M, mientras 1M sigue disponible para recuperación de material extenso.
No se fuerza un cambio de perfil ni se modifica SOL. Las variantes ya creadas se
reutilizan para evitar duplicados.
