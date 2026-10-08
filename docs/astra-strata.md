# ASTRA / Strata en LlamaCode

ASTRA es el perfil de LlamaCode para servir Qwen3.8 Flash Next con el motor
Strata. El endpoint local OpenAI-compatible se integra con Chat, Agente y el
resto de la app. LlamaCode mantiene el proceso bajo el mismo supervisor que los
servidores llama.cpp: inicio, `/health`, logs, watchdog y parada.

## Preparar la instalación

Instalá Strata y descargá/configurá el tamaño de modelo que quieras usando el
procedimiento del propio proyecto. LlamaCode busca una instalación completa en
la caché del usuario, Documentos y volúmenes montados. Para IQ3_S prioriza el
JSON calibrado más reciente que tenga todos sus archivos, antes del config base.
Al encontrarlo, guarda las rutas en **Ajustes → ASTRA** para que el perfil quede
disponible sin volver a configurarlo. Si hay varias instalaciones o querés usar
otra, podés indicar:

- **Carpeta de Strata**: la raíz que contiene `.venv` y `serve/server.py`.
- **Configuración del modelo**: opcional. Si queda vacía se usa
  `strata-iq3_s.json` dentro de la carpeta de Strata.
- **Puerto local**: `8350` por defecto; debe estar libre.

El Python del entorno virtual se resuelve como `.venv/bin/python` en Linux y
`.venv/Scripts/python.exe` en Windows. La app valida `serve/server.py`, el
ejecutable Strata, tokenizer, pack, shards, perfil de expertos y MTP del JSON;
si el config pide visión también valida sus assets. Una instalación parcial no
se anuncia como disponible en el selector remoto. LlamaCode no duplica ni
descarga esos archivos.

También se pueden configurar `ASTRA_STRATA_ROOT` y `ASTRA_STRATA_CONFIG` antes
de iniciar LlamaCode; los valores de Ajustes tienen prioridad.

## Iniciar y detener

Elegí **ASTRA · Strata IQ3_S · Qwen3.8 Flash Next** en Lanzar. El perfil queda
en el selector aunque todavía falte instalar/configurar Strata; en ese caso la
app lo marca como pendiente y muestra el error concreto al intentar iniciarlo.
**Iniciar servidor** ejecuta Strata en `127.0.0.1`, conserva stdout y stderr en
el log, espera a `/health` y después puede iniciar el Agente del perfil.
**Detener servidor** solicita la salida ordenada de Strata; si el proceso no
termina en 60 segundos, el supervisor fuerza su detención.

### Servir ASTRA a otro LlamaCode por LAN

En Lanzar, con ASTRA seleccionado y el servidor detenido, usá **Iniciar servidor
LAN**. La app habilita el Gateway autenticado en la LAN y luego inicia ASTRA en
modo servidor, sin iniciar un agente local. El gateway es el único endpoint
expuesto a la red; Strata sigue escuchando en loopback. En **Ajustes → Gateway**
vas a ver la URL IPv4 y la API key generada. Permití el puerto del gateway sólo
en la red privada de confianza y compartí la key sólo con ese cliente.

En la otra instancia, elegí **Lanzar → Usar un servidor LAN**, buscá este host y
seleccioná **ASTRA · Strata IQ3_S · Qwen3.8 Flash Next**. El cliente crea un
perfil remoto OpenAI-compatible y puede usarlo en Chat o Agente. También se
puede crear allí un backend Cloud manual con la URL LAN, el ID estable de modelo
`sys-astra-strata-iq3s` y la misma API key.

El gateway publica en `/v1/models` sólo los perfiles que el host puede ejecutar
con su configuración y archivos actuales. La respuesta de descubrimiento LAN
usa el mismo catálogo, así que el cliente ve ASTRA cuando la autodetección lo
marca listo. Con el auto-load activo,
cada request puede pedir el modelo por su ID; si difiere del activo, el host
hace swap, espera a que el servidor solicitado esté listo y reenvía el request.
Así el otro LlamaCode también puede pedir otro modelo disponible en el catálogo
de este host. El cambio de modelo inicia sólo el servidor de inferencia; no
arranca un agente local. Si ASTRA está apagado, el primer request que lo elija
puede tardar hasta que termine la carga. Sólo se sirve un modelo a la vez en
este modo; pedir otro perfil descarga/sustituye el activo.

La app usa el mismo puerto configurado para `/health` y para Chat/Agente. Si el
puerto está ocupado, detené el proceso que lo usa o elegí otro en Ajustes antes
de iniciar ASTRA.

Si falla el arranque, revisá el log de servidor. Los errores de configuración
identifican las rutas esperadas para Python, `server.py` y el JSON del modelo.

Para un backend OpenAI-compatible externo de Strata, el `cloudBaseUrl` del
perfil debe apuntar a la raíz del servidor (por ejemplo,
`http://127.0.0.1:8350`), sin agregar `/v1`: LlamaCode agrega `/v1` a las
requests de generación y consulta `/health` en la raíz. Si el backend no ofrece
`/health`, un 404 HTTP confirma que el endpoint respondió; los errores reales de
transporte siguen marcándose como fallo.

## Visión y Computer Use

LlamaCode habilita adjuntos de imagen y observación visual cuando la
configuración de Strata incluye `--vision` y sus archivos `vision.exe` y
`vision.mmproj` existen. Si falta el flag o alguno de esos assets, ASTRA se
trata como perfil de texto y la app no ofrece esas imágenes al agente.
La detección se hace desde el config de Strata: este servidor no recibe un
`--mmproj` en la línea de comandos de LlamaCode.

Los benchmarks de ASTRA mantienen los parámetros del config. La escalera
adaptativa de VRAM de LlamaCode cambia flags propios de llama.cpp (`--fit` y
`--fit-target`), que Strata no acepta; si un modelo excede la VRAM, hay que
ajustar el config de Strata antes de repetir.

### Corridas aisladas del benchmark

Al ejecutar LlamaCode headless/test-mode, ese proceso usa sus propias
preferencias. Pasale `ASTRA_STRATA_ROOT` y `ASTRA_STRATA_CONFIG` al proceso de
prueba; no uses como sustituto un backend cloud de prueba que no tenga esos
valores, porque no representa el lanzamiento local administrado de ASTRA. La
corrida debe registrar el perfil ASTRA real, el config y el fingerprint del
harness; los fallos `server-start` se excluyen de la puntuación del modelo.

El guard de texto previo a herramientas mide caracteres crudos emitidos por
generación, incluyendo razonamiento y respuesta. No uses el snapshot de
presentación `streamingText`: inserta `<think>` delante del texto visible y no
es monotónico. Esta diferencia evita contar dos veces la misma salida y abortar
ASTRA por un límite de tamaño falso. La corrección y su repetición están
registradas en `artifacts/astra-output-guard-fix-20261006/report.md`.
