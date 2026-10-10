# Alcance de los hashes SHA-256

Esta carpeta reúne la evaluación inicial del post r/Qwen_AI de IQ3_XXS en una
laptop y la solicitud posterior del post r/LocalLLM de Q4/4×P100/262K. Ambos
materiales quedaron bajo el mismo ID de campaña activa; el segundo no convierte
los resultados IQ3_XXS en una réplica del caso P100.

`SHA256SUMS.txt` usa el formato estándar de `sha256sum` y lista los archivos de
evidencia de esta carpeta. Se excluye a sí mismo, `manifest.json` y los archivos
`.pyc` bajo `__pycache__`, que son bytecode regenerable e ignorado por Git.
`manifest.json` enumera y verifica los demás archivos, incluido `SHA256SUMS.txt`,
pero se excluye a sí mismo y a esos mismos `.pyc`.

El paquete conserva recibos crudos, definiciones de suites, workspaces y event
logs generados por los agentes, ambos textos fuente, los planes por cada post y
el registro del bloqueo de recursos. No incluye pesos de modelos ni perfiles o
settings productivos.
