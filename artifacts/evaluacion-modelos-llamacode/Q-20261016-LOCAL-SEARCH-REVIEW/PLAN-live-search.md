# Preregistro complementario — smoke de calidad de búsqueda

Fecha: 2026-10-16. Continuación de `Q-20261016-LOCAL-SEARCH-REVIEW` (mismo ID; lock nuevo).

## Pregunta

El test de API sólo probó compatibilidad. Este smoke intenta observar si un endpoint PlumbSearch **local ya disponible** recupera páginas útiles para consultas técnicas habituales frente a un endpoint SearXNG local ya configurado.

## Condiciones de ejecución y parada

1. Consultar configuración y procesos sin imprimir valores de URL que puedan ser privados; sólo confirmar si los endpoints están configurados y si apuntan a loopback/local.
2. No instalar Docker, compilar/clonar Plumb, abrir un nodo P2P, iniciar crawlers, consultar el nodo público ni contactar motores externos. Si falta uno de los dos servicios locales, no hay comparación válida y se detiene la parte de relevancia con ese motivo concreto.
3. Si ambos servicios locales están activos, usar ocho consultas sintéticas y públicas, una solicitud por consulta y servicio, en serie, sin reintentos. Guardar consultas, URLs/resultados, códigos HTTP y latencias; no poner secretos en recibos.
4. Holdout predefinido: hallar documentación primaria para (a) Qt `QTcpServer::newConnection`, (b) Qt `QUrlQuery::queryItemValue`, (c) Qt `QTcpSocket::readyRead`, (d) CMake Ninja generator, (e) Python `pathlib.Path.write_text`, (f) C++ `std::filesystem::recursive_directory_iterator`, (g) QML `Loader.active`, (h) Python `urllib.parse.urlencode`. Un resultado es relevante si incluye la documentación primaria esperada; además se anotará relevancia del dominio oficial en top 3.
5. Clasificación 0/1 por consulta: esperado URL/doc oficial presente entre los primeros tres resultados = 1, ausente = 0. Reportar top-3 hit rate y latencia por proveedor como **smoke exploratorio**, no nDCG/ranking general ni recomendación estable. Una sola pasada no demuestra estabilidad.

## Seguridad y alcance

Las consultas no contienen datos privados. El lote máximo es 16 requests en total (8 por servicio), sin páginas de fetch ni scraping. No se inicia modelo/GPU ni se cambia configuración productiva. Si los endpoints no son locales o no están ambos disponibles, registrar sólo el preflight y mantener “calidad de PlumbSearch local: no evaluada”.
