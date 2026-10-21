# Q21 — Revalidación iterativa de pendientes

**Estado:** auditoría completada; no apareció una prueba nueva habilitada. La campaña VF-20261019-01 sigue incompleta.

## S36: recuperación de evidencia primaria

La apertura de `https://www.instagram.com/reel/DeehKGtuth5/` fue throttled. La búsqueda exacta de `DeehKGtuth5` devolvió cero resultados; la búsqueda combinada tampoco dio caption, transcripción ni copia atribuible. No se usó inicio de sesión, no se descargó el video y no se infirió su contenido desde notas previas.

**Decisión:** no diseñar ni correr un fixture específico. Reabrir cuando haya caption, transcripción, captura legible o mirror atribuible que confirme el escenario. Recibo: [resultado S36](receipts/source36-primary-retrieval-result.json).

## Revisión del resto de pruebas pendientes

- **Fuente #1, concurrencia:** el screen de servidor ya dio 48,45 tok/s serial y 48,01 tok/s simultáneo, con mayor latencia simultánea; las 80 generaciones terminaron al cap de 96 tokens. La E2E con dos tareas/subagentes no cambia la decisión actual porque el flujo solicitado es un repositorio por vez. Reabrir si se decide habilitar solapamiento.
- **Fuente #16, capacidad:** el cruce documental de tamaño exacto ya se hizo; falta telemetría de carga/residencia para inferir capacidad, y no hay decisión de aumentar la carga ahora.
- **Fuentes #20/#21/#24, híbrido:** siguen esperando proveedor, ID/versión, referencia autorizada de credencial, techo de gasto y frontera de datos antes de cualquier llamada.
- **Fuente #23:** Q20 cerró el A/B de PLE FP8 con empate de calidad (3/24 cada brazo) y cero pares ganados por FP8; no repetir el mismo diseño.
- **Otros:** S51 requiere resolver elegibilidad de licencia y un A/B no-MTP; UD-IQ4_XS requiere runner/grader corregidos y carga segura nueva; OpenJet requiere GGUF/kernel compatible; Harness² requiere workflow y holdout independiente de calidad. Otras fuentes dependen de hardware, almacenamiento o runtime que no está presente.

**Resultado:** no queda prueba de calidad justificada ejecutable en la configuración actual. Esto es una detención por condiciones externas, no una declaración de que la campaña esté completa. Próximo paso: continuar al cambiar al menos una condición listada.


La fila 169 de `Evaluaciones LlamaCode`, los resúmenes C2/E2 y el filtro A1:I169 quedaron actualizados; valores y formato de las celdas se releyeron. Recibo: [google-sheet-update-result.json](receipts/google-sheet-update-result.json). La altura de fila de 155 px fue aceptada por la API, pero el conector no expone lectura de vuelta de esa dimensión.
