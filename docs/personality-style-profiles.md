# Perfiles de personalidad y estilo

LlamaCode permite asociar preferencias reutilizables de expresión a cualquier
perfil de agente. Se guardan localmente en `persona_styles.json` dentro de la
carpeta de perfiles configurada por `LLAMACODE_PROFILES_DIR`.

## Tipos

- `personality`: tono conversacional, iniciativa, nivel de detalle y forma de
  acompañar al usuario.
- `writing-style`: ritmo, longitud de frases, vocabulario, metáforas, diálogos y
  ejemplos de referencia.

Estos perfiles sólo afectan la forma de responder. No conceden permisos, no
activan tools y no pueden reemplazar instrucciones de seguridad u operación.

## Uso

Desde Ajustes → Perfiles de agente se puede seleccionar una personalidad y un
estilo. El perfil activo conserva únicamente los IDs de esos artefactos. El
backend inyecta la ficha y, opcionalmente, hasta dos ejemplos dentro de un
límite de contexto configurable.

La ficha debe describir patrones observables y no repetir datos privados. Para
crear una ficha inicial se puede usar `buildStyleAnalysisPrompt()` con una
muestra y pedir al modelo una salida estructurada; también existe una medición
heurística local para una primera aproximación.

## Importación y exportación

Los perfiles se representan como JSON versionado. Al importar, LlamaCode genera
un nuevo ID y nunca sobrescribe el perfil existente. Las muestras quedan en la
máquina local y se recortan al límite configurado antes de entrar al prompt.

## Precedencia

La personalidad y el estilo son preferencias de expresión. La precedencia es:

1. sistema y seguridad;
2. permisos, aprobaciones y herramientas;
3. instrucciones del agente;
4. personalidad y estilo;
5. pedido concreto del usuario.

Si el usuario pide otro tono o formato para una respuesta puntual, esa petición
debe prevalecer sobre el estilo persistente siempre que no contradiga una regla
superior.
