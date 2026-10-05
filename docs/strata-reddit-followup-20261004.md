# Seguimiento local de ideas de Strata de Reddit

Fecha: 2026-10-04. Fuente: texto pegado de r/LocalLLaMA en
`/home/cristian/.codex/attachments/d09e98dc-a90b-445b-b31b-62c4b4542cf6/Texto pegado.txt`.

## Qué afirma el post y qué evidencia aporta

El autor dice que Qwen3.8 Flash-Next servido con Strata terminó una tarea de
auto-clicker de juego en menos de tres horas y con dos intervenciones, frente a
5–8 horas y más ida y vuelta con Hyperqwen. También admite uso elevado de RAM y
una degradación de respuesta del sistema en tareas/conversaciones largas. No
publica cuantización, versión de Strata, prompt exacto, harness, logs, tarea
ejecutable ni mediciones repetidas. Es una señal para formular pruebas, no una
comparación reproducible ni evidencia de que Strata supere SOL.

Los comentarios agregan una hipótesis distinta: algunos harnesses lanzan
subagentes aunque se les pida que no lo hagan; con pocos slots, concurrencia
puede reducir mucho el throughput. Debe probarse como interacción entre servidor
y harness, no atribuirse al modelo sin medir colas y solicitudes concurrentes.

## Evidencia local aplicable

- **Qwen3.8 UD-Q4_K_XL / Strata 0.1.39:** el candidato ya pasó HE0 1/1,
  HE20 20/20, BCB8 8/8 y ADV 10/10 con presupuesto configurado de 70 GiB;
  registró 56.15 GiB de expertos pinned en RAM. Su comparación local con SOL
  acabó 38/38 frente a 37/38 en primera pasada y 38/38 frente a 37/38 final,
  pero tomó 5344.735 s frente a 1534.200 s (3.484×). Una sola corrida no
  justifica cambiar el default. Ver
  [`strata-udq4-38ram-lch1-20261004.md`](strata-udq4-38ram-lch1-20261004.md)
  y la tabla local del usuario.
- **Más RAM en el mismo modo Q4:** los logs de la corrida de 70 GiB ya muestran
  que el complemento completo de expertos fuera de la caché GPU (56.15 GiB)
  quedó residente. Subir ese presupuesto a 80/90 GiB no añade expertos a esa
  configuración; no es un experimento informativo.
- **Q4 en dos GPUs y sin límite residente:** la guía del fork Strata v0.1.39
  describe otro modo: layer split `auto`, sin `--resident-budget-gib`, con los
  77 GB de expertos en RAM. Lo habilita cuando la RAM total alcanza alrededor de
  135 GB y documenta 64–78 tok/s en una máquina con 165 GiB, manteniendo al
  menos 68 GiB disponibles. Esta máquina reportó 123 GiB totales, 112 GiB
  disponibles y 2.9 GiB de swap usados antes de cargar. No satisface el mínimo
  total declarado. Por eso **no se lanzó** el modo dual sin límite ni se
  promovió una config que pueda dejar la sesión sin el margen que recomienda el
  fork. Una ampliación de RAM que alcance ese umbral habilitaría una prueba
  nueva; más `resident-budget-gib` por sí solo no.
- **Orca IQ3_XXS:** ya se ejecutó en Strata 0.1.39 con dos GPUs; los logs
  registran más del 90% de aciertos de caché. El cambio de prefill probado no
  resolvió el timeout de HE20. Copiarle el presupuesto/caché del Q4 no tiene
  hipótesis respaldada. Primero hace falta explicar la latencia del harness o
  corregir la causa de infraestructura reportada antes de otra suite larga. Ver
  [`orcarouter-qwen38-iq3_xxs-lch1-20261004.md`](orcarouter-qwen38-iq3_xxs-lch1-20261004.md).
- **Shard parcial de Orca:** se preserva. Hay dos shards completos verificados
  en la ruta de 7CFE…; el `.part` no participa en los resultados y no aporta una
  razón para reanudar o borrar la descarga en esta evaluación.

## Próximas pruebas con valor informativo

1. Repetir Q4 70 GiB una vez, con el mismo fingerprint/harness, antes de
   considerar promoción. Mantener el registro de memoria por etapa para comprobar
   estabilidad y sensibilidad a la variación entre corridas.
2. Preparar una tarea de coding realista pero determinista con workspace limpio,
   prompt sin contexto innecesario, tests de aceptación y una sola pasada de
   referencia. Comparar SOL y Q4 en el mismo harness; guardar intervenciones,
   tiempo hasta los tests verdes, archivos y reparaciones. Esto se acerca al
   relato del auto-clicker sin depender de un juego/UI impredecible.
3. En una campaña separada, comparar una solicitud serial frente a dos tareas
   simultáneas con los mismos modelos/configs. Registrar slots, tiempo en cola,
   throughput por tarea, RAM, VRAM e interacción del escritorio. Incluir control
   de subagentes del harness para saber si la degradación viene de Strata, de la
   política de delegación o de ambos.
4. Cuando la máquina cumpla el umbral de RAM del fork, comparar Q4 70 GiB en una
   GPU con Q4 dual-GPU layer split sin límite residente. No adelantar la suite de
   calidad: primero smoke de arranque, monitoreo de memoria/estabilidad y prueba
   de velocidad fija; sólo si conserva el margen se ejecuta HE0 → HE20 → BCB8.

Estas son preguntas nuevas; no repetir como si fueran nuevos resultados el HE20,
BCB8, ADV ni el ensayo de prefill ya cerrados. No se cambió ningún perfil
productivo, harness ni backend en este seguimiento.
