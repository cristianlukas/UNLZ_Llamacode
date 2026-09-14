# Revisión: Qwen3.8-27B frente a Qwen3.8-Flash-Next IQ3 — 2026-09-14

## Qué afirma el post

El autor compara un Qwen3.8-27B Q8 con un Qwen3.8-Flash-Next IQ3_XXS y obtiene
92% frente a 94% en nueve pruebas propias. La observación importante es que un
modelo MoE mucho mayor puede compensar una cuantización más agresiva. Es una
hipótesis razonable, pero la publicación no usa BCB, HE20, tool-use ni el mismo
harness de LlamaCode, y sus resultados dependen de otro equipo, otro backend y
otra muestra de tareas.

## Evidencia previa de LlamaCode

La comparación local disponible se hizo con dos RTX 3090, P2P PCIe y el mismo
prompt/harness entre Qwen3.8-27B y Flash-Next:

| Dimensión | Qwen3.8-27B | Flash-Next | Lectura |
| --- | ---: | ---: | --- |
| Pares de calidad válidos | 1 victoria | 0 victorias | No hay ganador estadístico con esta muestra |
| Empates | 8 | 8 | Rendimiento funcional muy cercano en esos casos |
| Configuración comparada | Q4 local, y también variante MTP estable | UD-Q4_K_XL con expertos en host | No es la comparación exacta IQ3 vs Q8 del post |
| Decode observado | ~73,75 tok/s con MTP en la variante Qwen | ~41,31 tok/s con cache MoE en la prueba histórica | Qwen fue más rápido en la configuración medida |
| Prefill | ~556,56 tok/s con MTP | ~54,05 tok/s | La caché de expertos penalizó fuertemente el prefill de Flash |
| Validación agéntica | SOL: BCB 8/8 y tool-use válido | HE0/BCB no válidos en ASTRA | SOL sigue siendo la referencia operativa |

Las pruebas posteriores de ASTRA con KV Q8 tampoco cambiaron la conclusión:
la variante de la comunidad produjo `////` y la configuración ASTRA actual
produjo texto repetitivo no utilizable. El mayor número bruto de tok/s no fue
suficiente para considerarla agente válida.

## Qué sí sirve para LlamaCode

1. **No asumir que Q8 pequeño siempre es mejor que IQ3 grande.** Para una
   futura comparación justa conviene medir Flash-Next IQ3_XXS, Qwen3.8-27B Q8,
   SOL y ASTRA con el mismo prompt set, seed, temperatura, límite de salida y
   validación de estructura.
2. **Separar calidad de ejecución.** La medición debe exigir salida válida,
   ausencia de repetición/corrupción, HE0 antes de HE20/BCB y tool-call correcto.
3. **Medir contexto y latencia por separado.** Flash-Next puede ofrecer una
   ventana mayor, pero sus expertos en host cambian radicalmente el prefill y
   el coste de cada vuelta agéntica.
4. **No extrapolar el 94% del post a SOL.** Es una media de nueve pruebas
   personales, no evidencia de reemplazo para BCB 8/8.

## Decisión

No se descargó otro IQ3_XXS: el artefacto no está instalado, la partición
principal tiene poco espacio libre y las pruebas existentes ya muestran que el
problema actual de ASTRA es funcional, no sólo de cuantización. No se cambió el
dropdown ni el default.

El resultado operativo sigue siendo:

- **SOL:** default para coding y agentes, con BCB 8/8.
- **QWEN38-Q8:** candidato experimental de fidelidad/contexto, con smoke
  funcional pero BCB pendiente.
- **ASTRA:** experimental para contexto Flash-Next; no apto para reemplazar SOL
  hasta corregir el prefill y repetir HE0 → HE20 → BCB.

Para que el post pudiera cambiar la tabla habría que instalar exactamente
Flash-Next IQ3_XXS en un volumen con espacio suficiente y repetir una campaña
apareada completa. Con la evidencia actual, no hay base para promoverlo.

