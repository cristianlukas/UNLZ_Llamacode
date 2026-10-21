# Q21 — Auditoría iterativa posterior a Q20

**Objetivo:** seguir el lote VF-20261019-01 de forma secuencial y encontrar si cambió alguna condición externa que habilite una prueba justificada.

## Prerregistro S36

**Pregunta:** ¿hay ahora una página pública primaria o un mirror atribuible que permita verificar el contenido del Reel `DeehKGtuth5` y la alegación sobre pedidos/unidades?

**Método:** abrir la URL recibida y consultar búsqueda pública por shortcode exacto y frase relacionada. Aceptar sólo caption/transcripción o copia atribuible. No iniciar sesión, descargar medios, inferir desde notas previas ni usar modelo/GPU.

**Pasa si:** una fuente atribuible confirma el requisito relevante. **Falla si:** throttling/login, ausencia de contenido o resultados que sólo repiten la nota no verificada.

**Decisión:** si pasa, revisar fixture existente y decidir si amerita caso nuevo; si falla, registrar el bloqueo y auditar el resto de condiciones pendientes. No editar producción ni borrar/mover modelos.
