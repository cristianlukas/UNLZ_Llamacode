# ¿Hay jerarquía Haiku / Sonnet / Opus entre los tres modelos del tier 48 GB?

La idea a probar era: **KAT-Coder = el rápido**, **ThinkingCap = el intermedio**,
**DeepSeek V4 Flash = el inteligente**. Este documento junta lo medido, incluido lo
que salió en contra.

Todo contra `llama-server` b10228-cuda12.4 en 2× RTX 3090, temperatura 0.3,
evaluadores deterministas (varios ejecutan el código que devuelve el modelo).

---

## 1. La suite Corta no discrimina: todos 5/5

Primer intento, benchmark del app en modo agente, 2 pasadas por perfil:

| perfil | score | TPS | seg/pasada |
|---|---|---|---|
| MTP 4 · 131k | 5/5, 5/5 | 61,8 | 59 |
| MTP 4 · 196k | 5/5, 5/5 | 60,3 | 63 |
| ThinkingCap 131k | 4/5, 5/5 | 39,4 | 97 |
| ThinkingCap 196k | 5/5, 5/5 | 36,7 | 96 |
| DeepSeek sin DSpark | 5/5, 5/5 | 7,6 | 374 |
| DeepSeek con DSpark | 5/5, 5/5 | 6,8 | 466 |

Las cinco tareas de la suite (`is_prime`, una cuenta, un one-liner, un silogismo y
un JSON) las despacha cualquier modelo de 27B. **Mide velocidad, no capacidad.**

Dato que ya vale: **DeepSeek tarda 6× más para el mismo 5/5**, y con DSpark rinde
*peor* que sin él (466 s vs 374 s).

---

## 2. Segundo intento: tareas más duras. Empate en los tres

Se armaron 12 tareas nuevas (código con tests ejecutables, aritmética multi-paso,
lógica, invariantes):

| | KAT-Coder | ThinkingCap+MTP | DeepSeek |
|---|---|---|---|
| total | 9/12 | 9/12 · 8/12 | — |
| contar letras `r` | ❌ | ❌ | ❌ |
| formato estricto (3×4 palabras) | ❌ | ❌ | ❌ |
| día de la semana | ❌ | ❌ | ❌ |
| porcentaje inverso | ✅ | ✅ | ✅ |
| suma de horarios | ✅ | ✅ | ✅ |
| json autoconteo | ✅ | ✅ | ✅ |
| nivel de código/lógica (6 tareas) | 6/6 | 6/6 · 5/6 | — |

**Empatan tarea por tarea.** ThinkingCap+MTP no le gana a KAT en nada, y encima va
a la mitad de velocidad (60 vs 110 t/s).

### Por qué esas tres tareas eran malas para medir

Contar letras y "3 líneas de 4 palabras" fallan por **tokenización**: el modelo no
ve caracteres, ve tokens. Un modelo de 284B falla igual que uno de 3B activos. Es
una limitación estructural compartida, no una diferencia de capacidad — no sirven
para armar escalones.

---

## 3. Tercer intento: cambiar de eje

Los ejes donde el tamaño del modelo sí debería pesar:

- **D. conocimiento factual de nicho** — un MoE de ~3B activos no tiene dónde
  guardarlo.
- **E. contexto largo** (needle in a haystack a 8k y 24k tokens).
- **F. muchas entidades cruzadas** — 5-6 restricciones que interactúan.
- **G. instrucciones anidadas** — 7 reglas simultáneas sobre un JSON.

Resultados en `docs/` cuando cierre la corrida; el script está en el scratchpad de
la sesión (`probe3.py`) y es reproducible contra cualquier server.

---

## 4. Lo que ya se puede afirmar

1. **KAT-Coder no es "el rápido y limitado".** Empata en capacidad con ThinkingCap
   y va casi al doble de velocidad. Para trabajo diario es el default razonable.
2. **ThinkingCap+MTP no compra capacidad sobre KAT**, compra visión (mmproj). Si no
   necesitás imágenes, no hay razón medida para preferirlo.
3. **MTP sí vale, y mucho**: +68% de decode (36,7 → 61,8 t/s) sin costo de
   calidad, y baja el tiempo de tarea de 96 s a 59 s. Es la mejor palanca del tier.
4. **DeepSeek todavía no justificó su costo.** 7 t/s contra 110 de KAT — 15× más
   lento — sin ventaja demostrada en ninguna tarea hasta el eje D.

### Hipótesis abierta sobre DeepSeek

Se está corriendo en **UD-IQ3_S**, o sea cuantizado sobre un modelo que ya viene
en 4-bit de fábrica. Si su ventaja se perdió ahí, hay dos salidas y las dos son
accionables: bajar a **IQ2_M** (más chico, más expertos en VRAM, ~2× de decode) ya
que la calidad no se estaría aprovechando igual, o sacarlo del roster y quedarse
con KAT + ThinkingCap.

---

## 5. Método: lo que costó caro

- **Medir velocidad no alcanza: hay que leer la respuesta.** La config más rápida
  de DeepSeek (194,9 t/s) devolvía texto corrupto con métricas perfectas.
- **Los evaluadores no pueden puntuar formato.** `python_prime` y `code_refactor`
  daban False en el 100% de las pasadas de todos los modelos porque comparaban
  literales (`n <= 1`, `**2`) contra código correcto escrito distinto.
- **En modo agente hay que evaluar los archivos, no el chat.** El agente escribe
  `is_prime.py` y su mensaje final viene vacío.
- **Un score parcial no es una corrida fallada.** 3/5 es un resultado; marcarlo
  `failed` esconde el score y dispara reparaciones inútiles.
- **Una tarea con 1.436 archivos generados no está midiendo el modelo.** Ver el
  bucle de renombres en `AgentProgressGovernor` (§ commit 3975790).
