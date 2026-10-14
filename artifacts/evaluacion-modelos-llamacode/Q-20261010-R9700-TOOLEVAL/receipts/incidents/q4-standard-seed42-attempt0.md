# Incidente: Q4 estándar seed 42, intento inicial

El primer proceso interactivo del runner desapareció tras 14 de 69 escenarios y no dejó JSON final. El endpoint continuó respondiendo; no se observó OOM ni error CUDA en el log del servidor. No se conserva recibo crudo completo de ese intento y su subtotal no se cuenta como score. Se repitió la misma huella con captura de salida: 69/69 y 88/100 en `../raw/q4-standard-seed42-retry1.json`.
