# Auditoría: expert-lookahead de Slotstream — 2026-09-18

## Resultado ejecutivo

El reporte propone ejecutar el router de una capa futura para anticipar qué
expertos habrá que leer desde SSD mientras la GPU procesa la capa actual. En
Slotstream la técnica alcanza aproximadamente 1,11× de decode frente a su
configuración anterior, con salidas idénticas en sus pruebas del Mac.

La mejora es conceptualmente relevante para ASTRA/Flash-Next, pero no es un
parámetro disponible en nuestro runtime. Slotstream es un motor nativo Swift
con MLX/Metal diseñado para Apple Silicon; su documentación declara que Linux,
Windows y NVIDIA todavía no están soportados. No se descargó el modelo ni se
intentó instalar Slotstream.

## Qué hace exactamente

El lookahead no predice tokens ni reemplaza MTP. Reutiliza el router del modelo
para pronosticar expertos de hasta dos capas futuras, reserva slots temporales,
lee esos expertos en segundo plano y aprovecha la lectura si el router real
elige los mismos expertos. Si se equivoca, descarta la lectura y ejecuta la
carga normal; por eso la salida no cambia, pero puede consumir ancho de banda
SSD adicional.

La documentación del proyecto reporta una mejora final de 1,111× sobre su
configuración anterior, con alrededor de 20% menos registros leídos durante
decode y menos bytes especulativos desperdiciados. La medición se hizo en un
Mac M5 Pro de 48 GB, con objetivo de memoria de 22 GB y dos tokens draft; el
propio proyecto aclara que no calificó otros Macs, tamaños de caché ni prompt
processing.

## Cruce con nuestras pruebas

| Ruta local | Resultado | Lectura |
| --- | ---: | --- |
| Flash-Next Q4 sin caché MoE | 16,45 tok/s a 16K | Control |
| Flash-Next Q4 con caché MoE 188 | 36,04 tok/s a 16K | +2,2× bruto, pero smoke inválido |
| Caché 150 + receta comunitaria | ~45,5 tok/s | Salida `/` o `////`; no utilizable |
| ASTRA Q4 + caché 188 | ~36,9 tok/s | Repetición del prompt; no agentivo |
| `lazy-mode on-direct` | ~7,54 tok/s | Salida válida, pero 49% más lento |
| IQ1_S + lazy on, 262K | 57,98 PP / 25,62 TG | Smoke Python válido; BCB/visión pendientes |
| SOL | 74 narrativo / 102 código | BCB 8/8 y tool-use OK |

La oportunidad que aborda Slotstream ya existe en nuestra arquitectura como
problema: expertos fuera de VRAM y lecturas host/SSD. Sin embargo, nuestras
pruebas muestran que el primer requisito no es ganar 10%, sino evitar la
salida corrupta. El lookahead no repara la corrupción observada en ASTRA ni
aporta visión, BCB o tool-use.

## ¿Se puede activar con una bandera?

No. La implementación externa necesita:

1. ejecutar routers futuros con el estado interno correcto;
2. un planificador de lecturas asíncronas y buffers temporales;
3. coordinación con la caché LRU de expertos;
4. límites de memoria y recuperación cuando el pronóstico falla;
5. una ruta CUDA para los tensores MoE de Qwen4Exp/Flash-Next.

El checkout local de llama.cpp tiene caché MoE, lazy reads, `cache-ram` y
`n-cpu-moe`, pero no contiene una implementación equivalente de
`expert-lookahead`. `phase-prefill` tampoco es lo mismo: libera/reorganiza la
caché durante el prefill y la rama experimental local no pasó el smoke
funcional.

## Decisión

- No se modifica SOL ni el dropdown.
- No se agrega un perfil `ASTRA-lookahead`: no hay backend CUDA local que lo
  ejecute y el artefacto Flash-Next grande ya no está descargado.
- No se repite una descarga de ~105 GB: la prueba externa es de otra plataforma
  y nuestras campañas ya midieron el cuello de botella local.
- La idea queda anotada como trabajo futuro para una rama CUDA/Flash-Next: medir
  `lookahead=off/on`, caché 150/188, contextos 8K/64K/131K, PP/TG, lecturas
  desperdiciadas, salida exacta, HE0, BCB y tool-use.

La conclusión operativa no cambia: la caché MoE es experimental; SOL sigue
siendo el perfil principal porque combina velocidad, calidad y estabilidad
agentiva validadas.

## Fuentes

- [Repositorio Slotstream](https://github.com/carloslfu/slotstream)
- [Diseño y resultados de expert-lookahead](https://github.com/carloslfu/slotstream/blob/main/docs/EXPERT-LOOKAHEAD.md)
- [Auditoría local de caché de expertos](qwen38-flash-next-expert-cache-pr27861-audit-20260914.md)
- [Auditoría local de lazy-mode](qwen38-flash-next-lazy-mode-20260913.md)
